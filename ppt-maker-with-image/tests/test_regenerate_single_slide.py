from __future__ import annotations

import json
import sys
from pathlib import Path

import llm.image as llm_image
import pytest
from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from llm.image.base import ReferenceImage
from pipeline import stage_render
import regenerate_single_slide


def _model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model="test-text-model"),
        image=ModelRoleConfig(provider="openrouter", model="test-image-model"),
        providers={
            "openrouter": ProviderConfig(
                name="openrouter",
                api_key_env="OPENROUTER_API_KEY",
                base_url="https://openrouter.ai/api/v1",
            )
        },
    )


def _provider_fallback_model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model=""),
        image=ModelRoleConfig(provider="openrouter", model="test-image-model"),
        providers={
            "openrouter": ProviderConfig(
                name="openrouter",
                api_key_env="OPENROUTER_API_KEY",
                base_url="https://openrouter.ai/api/v1",
                text_model="provider-text-model",
            )
        },
    )


def test_regenerate_single_prompt_uses_style_header_page_intent_and_provider_model_fallback(monkeypatch) -> None:
    recorded: dict[str, object] = {}
    style_header = "【不可见设计约束】只作为版式控制。"
    page_intent = {
        "global_intent": "突出经营结论",
        "slides": [{"page_no": 1, "intent": "先讲背景", "slide_role": "intro", "key_blocks": ["背景"]}],
    }

    def _fake_complete_json(**kwargs):
        recorded.update(kwargs)
        return {
            "page_no": 1,
            "title": "封面",
            "slide_role": "intro",
            "key_blocks": ["背景"],
            "image_prompt": "页面正文",
        }

    monkeypatch.setattr(regenerate_single_slide, "complete_json", _fake_complete_json)

    payload = regenerate_single_slide.regenerate_single_prompt(
        {
            "topic": "Q2经营分析",
            "target_audience": "管理层",
            "purpose": "汇报",
            "style": "咨询风",
            "page_count": 1,
        },
        {"typography": {"page_title": "36-44px, bold"}},
        {"slides": [{"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]}]},
        {"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]},
        {"page_no": 1, "title": "封面", "slide_role": "intro", "key_blocks": ["背景"], "image_prompt": "旧提示词"},
        "只优化标题表达。",
        style_header=style_header,
        page_intent=page_intent,
        dry_run=False,
        config=_provider_fallback_model_config(),
    )

    assert payload["image_prompt"].startswith(style_header)
    assert recorded["model"] == "provider-text-model"
    message = recorded["messages"][0]["content"]
    assert "Page intent:" in message
    assert '"global_intent": "突出经营结论"' in message
    assert "Style header:" in message
    assert style_header in message
    assert "36-44px" not in message
    assert "Master style:\n{}" in message


class _FakeImageProvider:
    def __init__(self, *, supports_reference_images: bool) -> None:
        self.supports_reference_images = supports_reference_images
        self.requests = []

    def render(self, request):
        self.requests.append(request)
        return b"rendered-slide"

    def close(self) -> None:
        pass


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_single_slide_job(
    tmp_path: Path,
    *,
    consistency: dict[str, object] | None,
) -> tuple[Path, Path]:
    output_dir = tmp_path / "artifacts"
    _write_json(
        tmp_path / "job.json",
        {
            "topic": "Q2经营分析",
            "target_audience": "管理层",
            "purpose": "汇报",
            "style": "咨询风",
            "page_count": 2,
            "output": {"directory": "artifacts", "pptx_filename": "deck.pptx"},
            "consistency": consistency or {},
        },
    )
    _write_json(output_dir / "master_style.json", {"typography": {"page_title": "36-44px, bold"}})
    _write_json(
        output_dir / "outline.json",
        {
            "slides": [
                {"page_no": 1, "title": "封面", "purpose": "引言", "key_blocks": ["背景"]},
                {"page_no": 2, "title": "分析", "purpose": "分析", "key_blocks": ["指标"]},
            ]
        },
    )
    _write_json(
        output_dir / "slide_prompts.json",
        {
            "slides": [
                {"page_no": 1, "title": "封面", "slide_role": "intro", "key_blocks": ["背景"], "image_prompt": "slide 1"},
                {"page_no": 2, "title": "分析", "slide_role": "analysis", "key_blocks": ["指标"], "image_prompt": "slide 2"},
            ]
        },
    )
    return tmp_path / "job.json", output_dir


def _run_render_only(
    monkeypatch,
    tmp_path: Path,
    *,
    page_no: int,
    consistency: dict[str, object] | None,
    provider_supports_reference_images: bool,
    first_slide_bytes: bytes | None = None,
) -> _FakeImageProvider:
    job_path, output_dir = _write_single_slide_job(tmp_path, consistency=consistency)
    if first_slide_bytes is not None:
        image_path = output_dir / "images" / "slide_01.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(first_slide_bytes)

    provider = _FakeImageProvider(supports_reference_images=provider_supports_reference_images)
    monkeypatch.setattr(regenerate_single_slide, "load_model_config", lambda _path: _model_config())
    monkeypatch.setattr(llm_image, "build_image_provider", lambda *_args, **_kwargs: provider)
    monkeypatch.setattr(stage_render, "build_image_render_prompt", lambda image_prompt, _resolution: image_prompt)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "regenerate_single_slide.py",
            str(job_path),
            "--page-no",
            str(page_no),
            "--render-only",
            "--skip-rebuild-pptx",
        ],
    )

    assert regenerate_single_slide.main() == 0
    assert len(provider.requests) == 1
    return provider


def test_regenerate_single_slide_passes_first_slide_reference_image_for_later_pages(
    tmp_path: Path, monkeypatch
) -> None:
    reference_bytes = b"first-slide-reference"
    provider = _run_render_only(
        monkeypatch,
        tmp_path,
        page_no=2,
        consistency={"use_reference_image": True, "reference_source": "first_slide"},
        provider_supports_reference_images=True,
        first_slide_bytes=reference_bytes,
    )

    request = provider.requests[0]
    assert request.reference_images is not None
    assert len(request.reference_images) == 1
    assert isinstance(request.reference_images[0], ReferenceImage)
    assert request.reference_images[0].data == reference_bytes
    assert request.reference_images[0].mime_type == "image/png"


def test_regenerate_single_slide_never_passes_reference_for_page_one(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _run_render_only(
        monkeypatch,
        tmp_path,
        page_no=1,
        consistency={"use_reference_image": True, "reference_source": "first_slide"},
        provider_supports_reference_images=True,
        first_slide_bytes=b"existing-first-slide",
    )

    assert provider.requests[0].reference_images is None


@pytest.mark.parametrize(
    ("consistency", "first_slide_bytes"),
    [
        ({"use_reference_image": True}, b"existing-first-slide"),
        ({"use_reference_image": True, "reference_source": "first_slide"}, None),
    ],
)
def test_regenerate_single_slide_skips_references_without_explicit_source_or_file(
    tmp_path: Path,
    monkeypatch,
    consistency: dict[str, object],
    first_slide_bytes: bytes | None,
) -> None:
    provider = _run_render_only(
        monkeypatch,
        tmp_path,
        page_no=2,
        consistency=consistency,
        provider_supports_reference_images=True,
        first_slide_bytes=first_slide_bytes,
    )

    assert provider.requests[0].reference_images is None


def test_regenerate_single_slide_falls_back_when_provider_lacks_reference_support(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _run_render_only(
        monkeypatch,
        tmp_path,
        page_no=2,
        consistency={"use_reference_image": True, "reference_source": "first_slide"},
        provider_supports_reference_images=False,
        first_slide_bytes=b"existing-first-slide",
    )

    assert provider.requests[0].reference_images is None
