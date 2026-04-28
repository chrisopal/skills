#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from llm.config import load_model_config
from pipeline.common import (
    ensure_huixin_assets,
    load_json,
    resolve_output_dir,
    skill_root,
    write_json,
)
from pipeline.manifest import STAGE_ARTIFACTS, load_manifest, write_manifest
from pipeline.stage_assemble import run_stage as run_assemble_stage
from pipeline.stage_master_style import run_stage as run_master_style_stage
from pipeline.stage_outline import run_stage as run_outline_stage
from pipeline.stage_page_intent import run_stage as run_page_intent_stage
from pipeline.stage_render import RENDER_METADATA_FILENAME, run_stage as run_render_stage
from pipeline.stage_slide_prompts import run_stage as run_slide_prompts_stage
from pipeline._stage_utils import build_provider_capabilities
from validate_job import validate_job_data
from style.header import build_style_header


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a semi-automatic image-first PPT job from job.json to pptx."
    )
    parser.add_argument("job", help="Path to the job.json file")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory override",
    )
    parser.add_argument(
        "--auto-approve-outline",
        action="store_true",
        help="Continue immediately after generating outline",
    )
    parser.add_argument(
        "--auto-approve-prompts",
        action="store_true",
        help="Continue immediately after generating slide prompts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip live model calls and generate placeholder outputs",
    )
    return parser


def persist_stage(output_dir: Path, name: str, data: Any) -> Path:
    path = output_dir / name
    write_json(path, data)
    return path


def update_manifest(
    manifest: dict[str, object],
    *,
    stage_name: str,
    artifact: str,
    status: str = "completed",
) -> None:
    stages = manifest.setdefault("stages", {})
    if not isinstance(stages, dict):
        stages = {}
        manifest["stages"] = stages
    payload = {"status": status, "artifact": artifact}
    stages[stage_name] = payload


def write_status_manifest(output_dir: Path, manifest: dict[str, object], job: dict[str, Any]) -> None:
    pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
    manifest["artifacts"] = {
        "master_style": (output_dir / STAGE_ARTIFACTS["master_style"]).exists(),
        "outline": (output_dir / STAGE_ARTIFACTS["outline"]).exists(),
        "page_intent": (output_dir / STAGE_ARTIFACTS["page_intent"]).exists(),
        "slide_prompts": (output_dir / STAGE_ARTIFACTS["slide_prompts"]).exists(),
        "images": len(sorted((output_dir / STAGE_ARTIFACTS["render"]).glob("slide_*.png"))),
        "pptx": (output_dir / pptx_name).exists(),
    }
    write_manifest(output_dir, manifest)


def maybe_attach_render_metadata(output_dir: Path, manifest: dict[str, object]) -> None:
    metadata_path = output_dir / RENDER_METADATA_FILENAME
    if metadata_path.exists():
        manifest["render_metadata"] = load_json(metadata_path)


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    model_config = load_model_config(Path(args.config).expanduser().resolve())

    missing = validate_job_data(job)
    if missing:
        print("[ERROR] job.json 缺少必要字段：")
        for item in missing:
            print(f"- {item}")
        return 1

    ensure_huixin_assets(job)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(output_dir)
    manifest.update(
        {
            "artifact_names": dict(STAGE_ARTIFACTS),
            "job_path": str(job_path),
            "output_dir": str(output_dir),
            "dry_run": args.dry_run,
            "provider_capabilities": build_provider_capabilities(model_config),
            "text_provider": model_config.text.provider,
            "text_model": model_config.text.model,
            "image_provider": model_config.image.provider,
            "image_model": model_config.image.model,
            "current_stage": "master_style",
        }
    )
    write_status_manifest(output_dir, manifest, job)

    master_style = run_master_style_stage(job, model_config, dry_run=args.dry_run)
    persist_stage(output_dir, STAGE_ARTIFACTS["master_style"], master_style)
    update_manifest(manifest, stage_name="master_style", artifact=STAGE_ARTIFACTS["master_style"])
    manifest["current_stage"] = "outline"
    write_status_manifest(output_dir, manifest, job)

    outline_payload = run_outline_stage(job, model_config, dry_run=args.dry_run)
    persist_stage(output_dir, STAGE_ARTIFACTS["outline"], outline_payload)
    update_manifest(manifest, stage_name="outline", artifact=STAGE_ARTIFACTS["outline"])
    if not (args.auto_approve_outline or job.get("outline_approved")):
        manifest["current_stage"] = "outline_review"
        write_status_manifest(output_dir, manifest, job)
        print(f"[STOP] 已生成大纲：{output_dir / STAGE_ARTIFACTS['outline']}")
        print("请确认并修改后，将 job.json 中的 outline_approved 设为 true，或使用 --auto-approve-outline 继续。")
        return 0

    manifest["current_stage"] = "page_intent"
    write_status_manifest(output_dir, manifest, job)
    page_intent_payload = run_page_intent_stage(
        job,
        model_config,
        master_style,
        outline_payload,
        dry_run=args.dry_run,
    )
    persist_stage(output_dir, STAGE_ARTIFACTS["page_intent"], page_intent_payload)
    update_manifest(manifest, stage_name="page_intent", artifact=STAGE_ARTIFACTS["page_intent"])
    style_header = build_style_header(master_style, page_intent_payload)

    manifest["current_stage"] = "slide_prompts"
    write_status_manifest(output_dir, manifest, job)
    slide_prompts = run_slide_prompts_stage(
        job,
        model_config,
        master_style,
        outline_payload,
        style_header=style_header,
        page_intent=page_intent_payload,
        dry_run=args.dry_run,
    )
    persist_stage(output_dir, STAGE_ARTIFACTS["slide_prompts"], slide_prompts)
    update_manifest(manifest, stage_name="slide_prompts", artifact=STAGE_ARTIFACTS["slide_prompts"])
    if not (args.auto_approve_prompts or job.get("prompts_approved")):
        manifest["current_stage"] = "slide_prompts_review"
        write_status_manifest(output_dir, manifest, job)
        print(f"[STOP] 已生成逐页提示词：{output_dir / STAGE_ARTIFACTS['slide_prompts']}")
        print("请确认并修改后，将 job.json 中的 prompts_approved 设为 true，或使用 --auto-approve-prompts 继续。")
        return 0

    manifest["current_stage"] = "render"
    write_status_manifest(output_dir, manifest, job)
    image_paths = run_render_stage(job, model_config, slide_prompts, output_dir, dry_run=args.dry_run)
    update_manifest(manifest, stage_name="render", artifact=STAGE_ARTIFACTS["render"])
    manifest["rendered_images"] = len(image_paths)
    maybe_attach_render_metadata(output_dir, manifest)
    manifest["current_stage"] = "assemble"
    write_status_manifest(output_dir, manifest, job)

    pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
    pptx_path = run_assemble_stage(image_paths, output_dir, pptx_name=pptx_name)
    update_manifest(manifest, stage_name="assemble", artifact=pptx_name)
    manifest["current_stage"] = "completed"
    write_status_manifest(output_dir, manifest, job)
    print(f"[OK] PPTX 已生成：{pptx_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
