from __future__ import annotations

import httpx
import pytest

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig, read_provider_key
from llm.errors import ProviderError, UnsupportedFeatureError
from llm.image import build_image_provider
from llm.image.base import ImageRenderRequest, ReferenceImage
from llm.image.gemini import GeminiImageProvider
from llm.image.openai import OpenAIImageProvider
from llm.image.openrouter import OpenRouterImageProvider
from llm.image import openai as openai_module
from llm.image import openrouter as openrouter_module


def _model_config(provider_name: str, providers: dict[str, ProviderConfig] | None = None) -> ModelConfig:
    role = ModelRoleConfig(provider=provider_name, model="test-model")
    return ModelConfig(
        default_provider=provider_name,
        text=role,
        image=role,
        providers=providers or {},
    )


def _json_response(method: str, url: str, payload: dict) -> httpx.Response:
    return httpx.Response(200, request=httpx.Request(method, url), json=payload)


class _FakeClient:
    def __init__(self, response: httpx.Response) -> None:
        self._response = response

    def __enter__(self) -> _FakeClient:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def post(self, *_args, **_kwargs) -> httpx.Response:
        return self._response


def test_build_image_provider_supports_legacy_image_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "legacy-openai-key")

    provider = build_image_provider(_model_config("openai"))

    assert isinstance(provider, OpenAIImageProvider)


def test_build_image_provider_without_key_still_raises_for_supported_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(UnsupportedFeatureError, match="OPENAI_API_KEY"):
        build_image_provider(_model_config("openai"))


def test_build_image_provider_rejects_unknown_provider() -> None:
    with pytest.raises(UnsupportedFeatureError, match="not supported: unknown"):
        build_image_provider(_model_config("unknown"))


def test_read_provider_key_explicit_empty_env_does_not_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "from-process-env")

    assert read_provider_key(ProviderConfig(name="openai"), env={}) is None


def test_read_provider_key_prefers_explicit_api_key_env() -> None:
    provider = ProviderConfig(name="openai", api_key_env="CUSTOM_KEY")

    assert (
        read_provider_key(
            provider,
            env={
                "CUSTOM_KEY": "from-custom-env",
                "OPENAI_API_KEY": "from-default-env",
            },
        )
        == "from-custom-env"
    )


def test_openai_url_download_errors_are_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _json_response(
        "POST",
        "https://api.openai.com/v1/images/generations",
        {"data": [{"url": "https://example.com/image.png"}]},
    )
    monkeypatch.setattr(openai_module.httpx, "Client", lambda timeout=60.0: _FakeClient(response))

    def _raise_connect_error(url: str, timeout: float = 60.0) -> httpx.Response:
        raise httpx.ConnectError("download failed", request=httpx.Request("GET", url))

    monkeypatch.setattr(openai_module.httpx, "get", _raise_connect_error)

    provider = OpenAIImageProvider(ProviderConfig(name="openai"), api_key="test-key")
    request = ImageRenderRequest(prompt="prompt", model="gpt-image-1")

    with pytest.raises(ProviderError, match="OpenAI image download failed") as exc_info:
        provider.render(request)

    assert isinstance(exc_info.value.__cause__, httpx.ConnectError)


def test_openrouter_url_download_status_errors_are_wrapped(monkeypatch: pytest.MonkeyPatch) -> None:
    response = _json_response(
        "POST",
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "choices": [
                {"message": {"images": [{"image_url": {"url": "https://example.com/image.png"}}]}}
            ]
        },
    )
    monkeypatch.setattr(openrouter_module.httpx, "Client", lambda timeout=60.0: _FakeClient(response))

    def _not_found(url: str, timeout: float = 60.0) -> httpx.Response:
        return httpx.Response(404, request=httpx.Request("GET", url))

    monkeypatch.setattr(openrouter_module.httpx, "get", _not_found)

    provider = OpenRouterImageProvider(ProviderConfig(name="openrouter"), api_key="test-key")
    request = ImageRenderRequest(prompt="prompt", model="openrouter-model")

    with pytest.raises(ProviderError, match="OpenRouter image download failed") as exc_info:
        provider.render(request)

    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


def test_openrouter_retries_malformed_json_render_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_url = "https://openrouter.ai/api/v1/chat/completions"
    responses = [
        httpx.Response(200, request=httpx.Request("POST", request_url), content=b'{"choices":[{"message":'),
        _json_response(
            "POST",
            request_url,
            {
                "choices": [
                    {
                        "message": {
                            "images": [{"image_url": {"url": "data:image/png;base64,aW1hZ2U="}}]
                        }
                    }
                ]
            },
        ),
    ]
    attempts = 0
    sleep_calls: list[int] = []

    class _RetryingClient:
        def __enter__(self) -> _RetryingClient:
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            return False

        def post(self, *_args, **_kwargs) -> httpx.Response:
            nonlocal attempts
            response = responses[attempts]
            attempts += 1
            return response

    monkeypatch.setattr(openrouter_module.httpx, "Client", lambda timeout=60.0: _RetryingClient())
    monkeypatch.setattr(openrouter_module.time, "sleep", sleep_calls.append)

    provider = OpenRouterImageProvider(ProviderConfig(name="openrouter"), api_key="test-key")
    request = ImageRenderRequest(prompt="prompt", model="openrouter-model")

    assert provider.render(request) == b"image"
    assert attempts == 2
    assert sleep_calls == [2]


def test_openrouter_sends_reference_images_as_multimodal_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: dict[str, object] = {}
    response = _json_response(
        "POST",
        "https://openrouter.ai/api/v1/chat/completions",
        {"choices": [{"message": {"images": [{"image_url": {"url": "data:image/png;base64,aW1hZ2U="}}]}}]},
    )

    class _RecordingClient(_FakeClient):
        def post(self, *_args, **kwargs) -> httpx.Response:
            recorded.update(kwargs)
            return response

    monkeypatch.setattr(openrouter_module.httpx, "Client", lambda timeout=60.0: _RecordingClient(response))

    provider = OpenRouterImageProvider(ProviderConfig(name="openrouter"), api_key="test-key")
    request = ImageRenderRequest(
        prompt="render slide 2",
        model="openrouter-model",
        reference_images=[
            ReferenceImage(data=b"reference-bytes", mime_type="image/webp"),
            ReferenceImage(data=b"second-ref", mime_type="image/png"),
        ],
    )

    provider.render(request)

    payload = recorded["json"]
    content = payload["messages"][0]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"] == "data:image/webp;base64,cmVmZXJlbmNlLWJ5dGVz"
    assert content[2]["type"] == "image_url"
    assert content[2]["image_url"]["url"] == "data:image/png;base64,c2Vjb25kLXJlZg=="


def test_provider_capability_info_reports_feature_flags() -> None:
    assert OpenRouterImageProvider(ProviderConfig(name="openrouter"), api_key="test-key").capability_info == {
        "supports_reference_images": True,
        "supports_seed": False,
    }
    assert OpenAIImageProvider(ProviderConfig(name="openai"), api_key="test-key").capability_info == {
        "supports_reference_images": False,
        "supports_seed": False,
    }
    assert GeminiImageProvider(ProviderConfig(name="gemini"), api_key="test-key").capability_info == {
        "supports_reference_images": False,
        "supports_seed": False,
    }


@pytest.mark.parametrize(
    ("provider", "render_request", "match"),
    [
        (
            OpenRouterImageProvider(ProviderConfig(name="openrouter"), api_key="test-key"),
            ImageRenderRequest(prompt="prompt", model="openrouter-model", seed=123),
            "does not support seed",
        ),
        (
            OpenAIImageProvider(ProviderConfig(name="openai"), api_key="test-key"),
            ImageRenderRequest(
                prompt="prompt",
                model="gpt-image-1",
                reference_images=[ReferenceImage(data=b"reference")],
            ),
            "does not support reference images",
        ),
        (
            GeminiImageProvider(ProviderConfig(name="gemini"), api_key="test-key"),
            ImageRenderRequest(prompt="prompt", model="gemini-image", seed=123),
            "does not support seed",
        ),
    ],
)
def test_providers_reject_unsupported_features(
    provider: object,
    render_request: ImageRenderRequest,
    match: str,
) -> None:
    with pytest.raises(UnsupportedFeatureError, match=match):
        provider.render(render_request)
