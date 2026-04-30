from __future__ import annotations

import re
import sys
from pathlib import Path

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
import render_single_slide_ppt


class _FakeProvider:
    def __init__(self) -> None:
        self.requests = []

    def render(self, request):
        self.requests.append(request)
        return b"single-slide-image"

    def close(self) -> None:
        pass


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


def test_render_single_slide_ppt_sanitizes_prompt_before_provider_render(
    tmp_path: Path, monkeypatch
) -> None:
    provider = _FakeProvider()
    assembled: list[tuple[list[Path], Path]] = []
    monkeypatch.setattr(render_single_slide_ppt, "load_model_config", lambda _path: _model_config())
    monkeypatch.setattr(render_single_slide_ppt, "build_image_provider", lambda *_args, **_kwargs: provider)
    monkeypatch.setattr(
        render_single_slide_ppt,
        "assemble_pptx",
        lambda image_paths, output_path: assembled.append((image_paths, output_path)),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "render_single_slide_ppt.py",
            "--prompt",
            (
                "Design a consulting slide with margins 56-72px, spacing 20-28px, "
                "rounded cards R=14px, stroke 1pt, subtle shadow, caption 12-14px, "
                "page title 36-44px, Microsoft YaHei, green highlights and clear hierarchy."
            ),
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert render_single_slide_ppt.main() == 0
    assert len(provider.requests) == 1
    request_prompt = provider.requests[0].prompt
    assert "consulting slide" in request_prompt
    assert "Microsoft YaHei" in request_prompt
    assert "green highlights" in request_prompt
    assert "clear hierarchy" in request_prompt
    _assert_prompt_sanitized(request_prompt)
    assert len(assembled) == 1
    assert assembled[0][1] == tmp_path / "single_slide.pptx"
