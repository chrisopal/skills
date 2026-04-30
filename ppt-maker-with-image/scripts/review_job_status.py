#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pipeline.common import load_json, resolve_output_dir
from pipeline.manifest import STAGE_ARTIFACTS, load_manifest, manifest_path
from validate_job import validate_job_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review the current PPT job status and recommend the next action."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument("--output-dir", default="", help="Optional override for artifacts directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    return parser


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_rendered_images(images_dir: Path) -> int:
    if not images_dir.exists():
        return 0
    return len(sorted(images_dir.glob("slide_*.png")))


def build_stage_artifacts(job: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
    return {
        "master_style": output_dir / STAGE_ARTIFACTS["master_style"],
        "outline": output_dir / STAGE_ARTIFACTS["outline"],
        "page_intent": output_dir / STAGE_ARTIFACTS["page_intent"],
        "slide_prompts": output_dir / STAGE_ARTIFACTS["slide_prompts"],
        "render": output_dir / STAGE_ARTIFACTS["render"],
        "assemble": output_dir / pptx_name,
    }


def summarize_stage_artifacts(
    stage_artifacts: dict[str, Path],
    manifest: dict[str, Any],
    image_count: int,
) -> dict[str, dict[str, Any]]:
    manifest_stages = manifest.get("stages") or {}
    summary: dict[str, dict[str, Any]] = {}
    for stage_name, path in stage_artifacts.items():
        entry = dict(manifest_stages.get(stage_name) or {})
        summary[stage_name] = {
            "artifact": entry.get("artifact", path.name),
            "exists": path.exists(),
            "path": str(path),
        }
        if stage_name == "render":
            summary[stage_name]["image_count"] = image_count
    return summary


def determine_stage(job: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(output_dir)
    manifest_file = manifest_path(output_dir)
    stage_artifacts = build_stage_artifacts(job, output_dir)
    master_style_path = stage_artifacts["master_style"]
    outline_path = stage_artifacts["outline"]
    page_intent_path = stage_artifacts["page_intent"]
    slide_prompts_path = stage_artifacts["slide_prompts"]
    images_dir = stage_artifacts["render"]
    pptx_path = stage_artifacts["assemble"]

    required_missing = validate_job_data(job)
    master_style = read_optional_json(master_style_path)
    outline = read_optional_json(outline_path)
    page_intent = read_optional_json(page_intent_path)
    slide_prompts = read_optional_json(slide_prompts_path)
    image_count = count_rendered_images(images_dir)
    expected_pages = int(job.get("page_count") or 0)

    issues: list[str] = []
    next_steps: list[str] = []

    has_master_style = master_style is not None
    has_outline = outline is not None
    has_page_intent = page_intent is not None
    has_slide_prompts = slide_prompts is not None
    has_rendered_images = image_count >= expected_pages if expected_pages else image_count > 0
    has_pptx = pptx_path.exists()

    stage: str
    completed = False

    if required_missing:
        stage = "input_incomplete"
        issues.extend([f"缺少必要字段: {field}" for field in required_missing])
        next_steps.append("补全 job.json 中的主题、受众、用途、风格和页数等必要字段。")
        next_steps.append("运行: python scripts/validate_job.py path/to/job.json")
    else:
        completed = (
            has_master_style
            and has_outline
            and has_page_intent
            and has_slide_prompts
            and has_rendered_images
            and has_pptx
        )
        if completed:
            stage = "completed"
            if not job.get("outline_approved") or not job.get("prompts_approved"):
                issues.append("产物已齐全，当前仍显示人工审批字段为 false，但按 artifact 完整度可视为可继续。")
            next_steps.append("当前 job 已完成。")
            next_steps.append("如果要局部调整，运行: python scripts/regenerate_single_slide.py path/to/job.json --page-no N")
        elif not has_master_style:
            stage = "ready_for_master_style"
            next_steps.append("运行主流程脚本生成 master_style 和后续中间产物。")
            next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json")
        elif not has_outline:
            stage = "ready_for_outline"
            next_steps.append("已有 master_style，但还没有 outline.json。")
            next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json")
        elif not has_page_intent:
            stage = "ready_for_page_intent"
            if not job.get("outline_approved"):
                issues.append("大纲已生成，但 job.json 中 outline_approved 仍为 false。")
            next_steps.append("生成逐页页面意图。")
            next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json --auto-approve-outline")
        elif not has_slide_prompts:
            stage = "ready_for_slide_prompts"
            if not job.get("page_intent_approved"):
                issues.append("页面意图已生成，但 job.json 中 page_intent_approved 仍为 false。")
            next_steps.append("逐页意图已生成，继续生成逐页提示词。")
            next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json --auto-approve-outline")
        elif not has_rendered_images:
            stage = "ready_for_image_generation"
            if expected_pages and image_count > 0:
                issues.append(f"已渲染图片 {image_count}/{expected_pages} 页，尚未完成。")
            next_steps.append("运行主流程继续生成图片并组装 pptx。")
            next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json --auto-approve-outline --auto-approve-prompts")
        elif not has_pptx:
            stage = "ready_for_pptx_assembly"
            next_steps.append("图片已齐全，但尚未组装成 pptx。")
            next_steps.append(
                "运行: python scripts/assemble_pptx.py --images artifacts/images/slide_01.png ... --output artifacts/deck.pptx"
            )
        else:
            stage = "ready_for_pptx_assembly"
            issues.append("发现异常阶段组合，建议重跑脚本检查。")

    if has_outline:
        slides = outline.get("slides", [])
        if expected_pages and slides and len(slides) != expected_pages:
            issues.append(f"outline.json 页数为 {len(slides)}，与 job.page_count={expected_pages} 不一致。")
    if has_slide_prompts:
        slides = slide_prompts.get("slides", [])
        if expected_pages and slides and len(slides) != expected_pages:
            issues.append(f"slide_prompts.json 页数为 {len(slides)}，与 job.page_count={expected_pages} 不一致。")
    if has_page_intent:
        slides = page_intent.get("slides", [])
        if expected_pages and slides and len(slides) != expected_pages:
            issues.append(f"page_intent.json 页数为 {len(slides)}，与 job.page_count={expected_pages} 不一致。")
    if not manifest_file.exists():
        issues.append("manifest.json 尚未生成，流水线元数据不完整。")

    return {
        "stage": stage,
        "completed": completed,
        "issues": issues,
        "next_steps": next_steps,
        "artifacts": {
            "manifest": manifest_file.exists(),
            "master_style": has_master_style,
            "outline": has_outline,
            "page_intent": has_page_intent,
            "slide_prompts": has_slide_prompts,
            "images": image_count,
            "pptx": has_pptx,
        },
        "stage_artifacts": summarize_stage_artifacts(stage_artifacts, manifest, image_count),
        "manifest_current_stage": manifest.get("current_stage"),
    }


def print_human_readable(status: dict[str, Any], job_path: Path, output_dir: Path) -> None:
    print(f"Job: {job_path}")
    print(f"Artifacts: {output_dir}")
    print(f"Stage: {status['stage']}")
    print("")
    print("Artifacts summary:")
    print(f"- manifest.json: {status['artifacts']['manifest']}")
    print(f"- master_style.json: {status['artifacts']['master_style']}")
    print(f"- outline.json: {status['artifacts']['outline']}")
    print(f"- page_intent.json: {status['artifacts']['page_intent']}")
    print(f"- slide_prompts.json: {status['artifacts']['slide_prompts']}")
    print(f"- images rendered: {status['artifacts']['images']}")
    print(f"- pptx exists: {status['artifacts']['pptx']}")
    if status.get("manifest_current_stage"):
        print(f"- manifest current_stage: {status['manifest_current_stage']}")
    print("")
    print("Stage artifacts:")
    for stage_name, artifact in status["stage_artifacts"].items():
        suffix = ""
        if stage_name == "render":
            suffix = f" ({artifact['image_count']} images)"
        print(f"- {stage_name}: {artifact['artifact']} -> {artifact['exists']}{suffix}")
    if status["issues"]:
        print("")
        print("Issues:")
        for item in status["issues"]:
            print(f"- {item}")
    print("")
    print("Next steps:")
    for step in status["next_steps"]:
        print(f"- {step}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)
    status = determine_stage(job, output_dir)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print_human_readable(status, job_path, output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
