from __future__ import annotations

from pathlib import Path

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_render


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
