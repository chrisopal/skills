from __future__ import annotations

import sys
from pathlib import Path

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline.common import load_json, write_json
from pipeline.stage_render import RENDER_METADATA_FILENAME
import run_ppt_job


def _model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model="text-model"),
        image=ModelRoleConfig(provider="openrouter", model="image-model"),
        providers={"openrouter": ProviderConfig(name="openrouter")},
    )


def test_run_ppt_job_includes_render_metadata_in_final_manifest(tmp_path: Path, monkeypatch) -> None:
    job_path = tmp_path / "job.json"
    output_dir = tmp_path / "out"
    write_json(
        job_path,
        {
            "topic": "Q2经营分析",
            "target_audience": "管理层",
            "purpose": "汇报",
            "style": "咨询风",
            "page_count": 1,
            "outline_approved": True,
            "prompts_approved": True,
            "output": {"directory": "out", "pptx_filename": "deck.pptx"},
        },
    )

    monkeypatch.setattr(run_ppt_job, "load_model_config", lambda _path: _model_config())
    monkeypatch.setattr(run_ppt_job, "validate_job_data", lambda _job: [])
    monkeypatch.setattr(run_ppt_job, "ensure_huixin_assets", lambda _job: None)
    monkeypatch.setattr(run_ppt_job, "run_master_style_stage", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(run_ppt_job, "run_outline_stage", lambda *_args, **_kwargs: {"slides": []})
    monkeypatch.setattr(run_ppt_job, "run_page_intent_stage", lambda *_args, **_kwargs: {"slides": []})
    monkeypatch.setattr(run_ppt_job, "build_style_header", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(
        run_ppt_job,
        "run_slide_prompts_stage",
        lambda *_args, **_kwargs: {"slides": [{"page_no": 1, "title": "封面", "image_prompt": "cover"}]},
    )

    render_metadata = {
        "use_reference_image": True,
        "provider_supports_reference_images": False,
        "reference_source": "first_slide",
        "fallback_reason": "provider_does_not_support_reference_images",
    }

    def _fake_render(*_args, **_kwargs):
        image_dir = output_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)
        image_path = image_dir / "slide_01.png"
        image_path.write_bytes(b"image")
        write_json(output_dir / RENDER_METADATA_FILENAME, render_metadata)
        return [image_path]

    monkeypatch.setattr(run_ppt_job, "run_render_stage", _fake_render)

    def _fake_assemble(_image_paths, assembled_output_dir, *, pptx_name: str):
        pptx_path = assembled_output_dir / pptx_name
        pptx_path.write_bytes(b"pptx")
        return pptx_path

    monkeypatch.setattr(run_ppt_job, "run_assemble_stage", _fake_assemble)
    monkeypatch.setattr(
        sys,
        "argv",
        ["run_ppt_job.py", str(job_path), "--config", str(tmp_path / "config.yaml")],
    )

    assert run_ppt_job.main() == 0

    manifest = load_json(output_dir / "manifest.json")
    assert manifest["render_metadata"] == render_metadata
