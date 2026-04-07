#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_ppt_job import load_json, resolve_output_dir
from validate_job import validate_job_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review the current PPT job status and recommend the next action."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional override for artifacts directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON output",
    )
    return parser


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def count_rendered_images(images_dir: Path) -> int:
    if not images_dir.exists():
        return 0
    return len(sorted(images_dir.glob("slide_*.png")))


def determine_stage(job: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    master_style_path = output_dir / "master_style.json"
    outline_path = output_dir / "outline.json"
    slide_prompts_path = output_dir / "slide_prompts.json"
    images_dir = output_dir / "images"
    pptx_path = output_dir / job.get("output", {}).get("pptx_filename", "deck.pptx")

    required_missing = validate_job_data(job)
    master_style = read_optional_json(master_style_path)
    outline = read_optional_json(outline_path)
    slide_prompts = read_optional_json(slide_prompts_path)
    image_count = count_rendered_images(images_dir)
    expected_pages = int(job.get("page_count") or 0)

    issues: list[str] = []
    next_steps: list[str] = []

    if required_missing:
        stage = "input_incomplete"
        issues.extend([f"缺少必要字段: {field}" for field in required_missing])
        next_steps.append("补全 job.json 中的主题、受众、用途、风格和页数等必要字段。")
        next_steps.append("运行: python scripts/validate_job.py path/to/job.json")
        return {
            "stage": stage,
            "issues": issues,
            "next_steps": next_steps,
            "artifacts": {
                "master_style": master_style_path.exists(),
                "outline": outline_path.exists(),
                "slide_prompts": slide_prompts_path.exists(),
                "images": image_count,
                "pptx": pptx_path.exists(),
            },
        }

    if master_style is None:
        stage = "ready_for_master_style"
        next_steps.append("运行主流程脚本生成 master style 和后续中间产物。")
        next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json")
    elif outline is None:
        stage = "ready_for_outline"
        next_steps.append("已有 master style，但还没有 outline.json。")
        next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json --auto-approve-outline")
    elif not job.get("outline_approved"):
        stage = "waiting_for_outline_review"
        issues.append("大纲已生成，但 job.json 中 outline_approved 仍为 false。")
        next_steps.append("检查 artifacts/outline.json，必要时手动修改。")
        next_steps.append("修改后运行: python scripts/sync_job_artifacts.py path/to/job.json --approve-outline")
    elif slide_prompts is None:
        stage = "ready_for_slide_prompts"
        next_steps.append("大纲已确认，但还没有 slide_prompts.json。")
        next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json --auto-approve-outline")
    elif not job.get("prompts_approved"):
        stage = "waiting_for_prompt_review"
        issues.append("逐页提示词已生成，但 job.json 中 prompts_approved 仍为 false。")
        next_steps.append("检查 artifacts/slide_prompts.json，必要时手动修改。")
        next_steps.append("修改后运行: python scripts/sync_job_artifacts.py path/to/job.json --approve-prompts")
    elif image_count < expected_pages:
        stage = "ready_for_image_generation"
        if image_count > 0:
            issues.append(f"已渲染图片 {image_count}/{expected_pages} 页，尚未完成。")
        next_steps.append("运行主流程继续生成图片并组装 pptx。")
        next_steps.append("运行: python scripts/run_ppt_job.py path/to/job.json --auto-approve-outline --auto-approve-prompts")
    elif not pptx_path.exists():
        stage = "ready_for_pptx_assembly"
        next_steps.append("图片已齐全，但尚未组装成 pptx。")
        next_steps.append(
            "运行: python scripts/assemble_pptx.py --images artifacts/images/slide_01.png ... --output artifacts/deck.pptx"
        )
    else:
        stage = "completed"
        next_steps.append("当前 job 已完成。")
        next_steps.append("如果要局部调整，运行: python scripts/regenerate_single_slide.py path/to/job.json --page-no N")

    if outline is not None:
        slides = outline.get("slides", [])
        if expected_pages and slides and len(slides) != expected_pages:
            issues.append(f"outline.json 页数为 {len(slides)}，与 job.page_count={expected_pages} 不一致。")
    if slide_prompts is not None:
        slides = slide_prompts.get("slides", [])
        if expected_pages and slides and len(slides) != expected_pages:
            issues.append(f"slide_prompts.json 页数为 {len(slides)}，与 job.page_count={expected_pages} 不一致。")

    return {
        "stage": stage,
        "issues": issues,
        "next_steps": next_steps,
        "artifacts": {
            "master_style": master_style_path.exists(),
            "outline": outline_path.exists(),
            "slide_prompts": slide_prompts_path.exists(),
            "images": image_count,
            "pptx": pptx_path.exists(),
        },
    }


def print_human_readable(status: dict[str, Any], job_path: Path, output_dir: Path) -> None:
    print(f"Job: {job_path}")
    print(f"Artifacts: {output_dir}")
    print(f"Stage: {status['stage']}")
    print("")
    print("Artifacts summary:")
    print(f"- master_style.json: {status['artifacts']['master_style']}")
    print(f"- outline.json: {status['artifacts']['outline']}")
    print(f"- slide_prompts.json: {status['artifacts']['slide_prompts']}")
    print(f"- images rendered: {status['artifacts']['images']}")
    print(f"- pptx exists: {status['artifacts']['pptx']}")
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
