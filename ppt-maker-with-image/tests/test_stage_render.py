from __future__ import annotations

from pathlib import Path
import re

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_render
from pipeline.common import load_json


class _FakeProvider:
    supports_reference_images = True
    supports_seed = True

    def __init__(self) -> None:
        self.requests = []
        self.render_count = 0

    def render(self, request):
        self.requests.append(request)
        self.render_count += 1
        return f"image-bytes-{self.render_count}".encode()

    def close(self) -> None:
        pass


class _NoReferenceProvider(_FakeProvider):
    supports_reference_images = False


class _NoSeedProvider(_FakeProvider):
    supports_seed = False


def _assert_prompt_sanitized(text: str) -> None:
    assert not re.search(r"\b(?:px|pt)\b", text, flags=re.IGNORECASE)
    assert not re.search(r"\b(?:stroke|shadow|margin|margins|spacing|caption)\b", text, flags=re.IGNORECASE)
    assert "R=" not in text
    assert not re.search(
        r"\b(?:40\s*-\s*56|56\s*-\s*72|20\s*-\s*28|24\s*-\s*30|12\s*-\s*14|16\s*-\s*18|18\s*-\s*22|36\s*-\s*44)\b",
        text,
    )


def _model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model="text-model"),
        image=ModelRoleConfig(provider="openrouter", model="image-model"),
        providers={"openrouter": ProviderConfig(name="openrouter")},
    )


def test_stage_render_routes_first_slide_as_reference_for_following_slides(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    slide_prompts = {
        "slides": [
            {"page_no": 1, "title": "封面", "image_prompt": "slide 1"},
            {"page_no": 2, "title": "分析", "image_prompt": "slide 2"},
            {"page_no": 3, "title": "行动", "image_prompt": "slide 3"},
        ]
    }

    paths = stage_render.run_stage(
        {"consistency": {"use_reference_image": True, "reference_source": "first_slide", "seed": 123}},
        _model_config(),
        slide_prompts,
        tmp_path,
        dry_run=False,
    )

    assert len(paths) == 3
    first_slide_bytes = b"image-bytes-1"
    assert provider.requests[0].reference_images is None
    assert provider.requests[1].reference_images is not None
    assert provider.requests[1].reference_images[0].data == first_slide_bytes
    assert provider.requests[1].reference_images[0].mime_type == "image/png"
    assert provider.requests[2].reference_images is not None
    assert provider.requests[2].reference_images[0].data == first_slide_bytes
    assert provider.requests[1].seed == 123
    assert provider.requests[2].seed == 123
    metadata = load_json(tmp_path / stage_render.RENDER_METADATA_FILENAME)
    assert metadata == {
        "use_reference_image": True,
        "provider_supports_reference_images": True,
        "reference_source": "first_slide",
        "fallback_reason": None,
    }


def test_stage_render_omits_seed_when_provider_lacks_seed_support(tmp_path: Path, monkeypatch) -> None:
    provider = _NoSeedProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    paths = stage_render.run_stage(
        {"consistency": {"seed": 123}},
        _model_config(),
        {
            "slides": [
                {"page_no": 1, "title": "一", "image_prompt": "one"},
                {"page_no": 2, "title": "二", "image_prompt": "two"},
            ]
        },
        tmp_path,
        dry_run=False,
    )

    assert len(paths) == 2
    assert [request.seed for request in provider.requests] == [None, None]


def test_stage_render_preserves_seed_when_provider_supports_seed(tmp_path: Path, monkeypatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    stage_render.run_stage(
        {"consistency": {"seed": 456}},
        _model_config(),
        {"slides": [{"page_no": 1, "title": "一", "image_prompt": "one"}]},
        tmp_path,
        dry_run=False,
    )

    assert [request.seed for request in provider.requests] == [456]


def test_stage_render_sanitizes_existing_slide_prompts_at_render_boundary(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    raw_prompt = (
        "Design a white-background business slide with margins 56-72px, spacing 20-28px, "
        "rounded cards R=14px, stroke 1pt, subtle shadow, caption 12-14px, "
        "page title 36-44px, clear hierarchy and green highlights."
    )

    stage_render.run_stage(
        {},
        _model_config(),
        {"slides": [{"page_no": 1, "title": "一", "image_prompt": raw_prompt}]},
        tmp_path,
        dry_run=False,
    )

    assert len(provider.requests) == 1
    request_prompt = provider.requests[0].prompt
    assert "white-background business slide" in request_prompt
    assert "green highlights" in request_prompt
    assert "clear hierarchy" in request_prompt
    _assert_prompt_sanitized(request_prompt)


def test_stage_render_falls_back_cleanly_when_provider_lacks_reference_support(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _NoReferenceProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    paths = stage_render.run_stage(
        {"consistency": {"use_reference_image": True, "reference_source": "first_slide"}},
        _model_config(),
        {
            "slides": [
                {"page_no": 1, "title": "一", "image_prompt": "one"},
                {"page_no": 2, "title": "二", "image_prompt": "two"},
            ]
        },
        tmp_path,
        dry_run=False,
    )

    assert len(paths) == 2
    assert provider.requests[0].reference_images is None
    assert provider.requests[1].reference_images is None
    metadata = load_json(tmp_path / stage_render.RENDER_METADATA_FILENAME)
    assert metadata == {
        "use_reference_image": True,
        "provider_supports_reference_images": False,
        "reference_source": "first_slide",
        "fallback_reason": "provider_does_not_support_reference_images",
    }


def test_stage_render_keeps_reference_disabled_by_default(tmp_path: Path, monkeypatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    stage_render.run_stage(
        {},
        _model_config(),
        {
            "slides": [
                {"page_no": 1, "title": "一", "image_prompt": "one"},
                {"page_no": 2, "title": "二", "image_prompt": "two"},
            ]
        },
        tmp_path,
        dry_run=False,
    )

    assert provider.requests[0].reference_images is None
    assert provider.requests[1].reference_images is None


def test_stage_render_requires_explicit_first_slide_reference_source(tmp_path: Path, monkeypatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    stage_render.run_stage(
        {"consistency": {"use_reference_image": True}},
        _model_config(),
        {
            "slides": [
                {"page_no": 1, "title": "一", "image_prompt": "one"},
                {"page_no": 2, "title": "二", "image_prompt": "two"},
            ]
        },
        tmp_path,
        dry_run=False,
    )

    assert provider.requests[0].reference_images is None
    assert provider.requests[1].reference_images is None
