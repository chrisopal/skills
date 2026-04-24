#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from run_ppt_job import load_json, resolve_output_dir
from validate_job import find_missing_required_fields, has_confirmed_template


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Review the current direct-PPT job status and recommend the next action."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument("--output-dir", default="", help="Optional override for artifacts directory")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON output")
    return parser


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def determine_stage(job: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    master_style_path = output_dir / "master_style.json"
    outline_path = output_dir / "outline.json"
    slide_prompts_path = output_dir / "slide_prompts.json"
    slide_specs_path = output_dir / "slide_specs.json"
    image_manifest_path = output_dir / "image_manifest.json"
    slides_dir = output_dir / "slides"
    compile_js_path = slides_dir / "compile.js"
    pptx_path = output_dir / job.get("output", {}).get("pptx_filename", "deck.pptx")

    required_missing = find_missing_required_fields(job)
    outline = read_optional_json(outline_path)
    slide_prompts = read_optional_json(slide_prompts_path)
    slide_specs = read_optional_json(slide_specs_path)
    expected_pages = int(job.get("page_count") or 0)
    expected_js_files = [slides_dir / f"slide-{idx:02d}.js" for idx in range(1, expected_pages + 1)]
    missing_js_files = [path.name for path in expected_js_files if not path.exists()]
    placeholder_count = 0
    asset_count = 0
    if slide_specs is not None:
        for slide in slide_specs.get("slides", []):
            placeholder_count += len(slide.get("image_placeholders", []))
            asset_count += len(slide.get("image_assets", []))

    issues: list[str] = []
    next_steps: list[str] = []

    if required_missing:
        stage = "input_incomplete"
        issues.extend([f"缺少必要字段: {field}" for field in required_missing])
        next_steps.append("补全 topic / target_audience / purpose / style / page_count 这些必填字段。")
        next_steps.append("运行: python scripts/validate_job.py path/to/job.json")
    elif not job.get("requirement_confirmed"):
        stage = "waiting_for_requirement_confirmation"
        next_steps.append("查看并确认 requirement_summary，然后将 job.json 中 requirement_confirmed 设为 true。")
    elif not has_confirmed_template(job):
        stage = "waiting_for_template_confirmation"
        if job.get("recommended_template_id") and job.get("recommended_template_name"):
            issues.append(
                f"已推荐模板：{job['recommended_template_name']} ({job['recommended_template_id']})，但尚未确认。"
            )
        next_steps.append("将推荐模板写入 job.json 的 template_id / template_name 后重新运行。")
    elif not master_style_path.exists():
        stage = "ready_for_master_style"
        next_steps.append("运行主流程脚本生成 master style 和后续中间产物。")
    elif outline is None:
        stage = "ready_for_outline"
        next_steps.append("已有 master style，但还没有 outline.json。")
    elif not job.get("outline_approved"):
        stage = "waiting_for_outline_review"
        next_steps.append("检查 artifacts/outline.json，必要时手动修改后 approve。")
    elif slide_prompts is None:
        stage = "ready_for_slide_prompts"
        next_steps.append("大纲已确认，但还没有 slide_prompts.json。")
    elif not job.get("prompts_approved"):
        stage = "waiting_for_prompt_review"
        issues.append("结构化页面意图与 compiled prompts 已生成，但 prompts_approved 仍为 false。")
        next_steps.append("检查 artifacts/slide_prompts.json，必要时手动修改结构化字段。")
    elif slide_specs is None:
        stage = "ready_for_direct_render"
        next_steps.append("重新运行主流程生成 slide_specs、页面级 JS，并直接绘制 pptx。")
    elif missing_js_files:
        stage = "ready_for_page_js_generation"
        issues.append(f"缺少页面 JS: {', '.join(missing_js_files)}")
        next_steps.append("重新运行主流程，为缺失页面生成 slides/slide-XX.js。")
    elif not compile_js_path.exists():
        stage = "ready_for_compile_script"
        issues.append("缺少 slides/compile.js。")
        next_steps.append("重新运行主流程生成 compile.js 并组装 pptx。")
    elif not pptx_path.exists():
        stage = "ready_for_pptx_assembly"
        next_steps.append("页面级 JS 已存在，但尚未绘制为 pptx。")
        next_steps.append("运行: python scripts/assemble_pptx.py --slide-specs artifacts/slide_specs.json --master-style artifacts/master_style.json --output artifacts/deck.pptx")
    else:
        stage = "completed"
        next_steps.append("当前 job 已完成。")
        next_steps.append("如果要局部调整，运行: python scripts/regenerate_single_slide.py path/to/job.json --page-no N")

    if outline is not None and expected_pages and len(outline.get("slides", [])) != expected_pages:
        issues.append(f"outline.json 页数为 {len(outline.get('slides', []))}，与 job.page_count={expected_pages} 不一致。")
    if slide_prompts is not None and expected_pages and len(slide_prompts.get("slides", [])) != expected_pages:
        issues.append(f"slide_prompts.json 页数为 {len(slide_prompts.get('slides', []))}，与 job.page_count={expected_pages} 不一致。")
    if slide_specs is not None and expected_pages and len(slide_specs.get("slides", [])) != expected_pages:
        issues.append(f"slide_specs.json 页数为 {len(slide_specs.get('slides', []))}，与 job.page_count={expected_pages} 不一致。")
    if placeholder_count and asset_count < placeholder_count:
        issues.append(f"存在 {placeholder_count} 个图片占位，但只有 {asset_count} 个已生成图片资产。")
        next_steps.append("如需图片，运行: python scripts/generate_image_assets.py --slide-specs artifacts/slide_specs.json --master-style artifacts/master_style.json")

    return {
        "stage": stage,
        "issues": issues,
        "next_steps": next_steps,
        "artifacts": {
            "master_style": master_style_path.exists(),
            "outline": outline_path.exists(),
            "slide_prompts": slide_prompts_path.exists(),
            "slide_specs": slide_specs_path.exists(),
            "image_manifest": image_manifest_path.exists(),
            "image_placeholders": placeholder_count,
            "image_assets": asset_count,
            "slide_js": bool(expected_js_files) and not missing_js_files,
            "compile_js": compile_js_path.exists(),
            "pptx": pptx_path.exists(),
        },
    }


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
        print(f"Job: {job_path}")
        print(f"Artifacts: {output_dir}")
        print(f"Stage: {status['stage']}\n")
        print("Artifacts summary:")
        for key, value in status["artifacts"].items():
            print(f"- {key}: {value}")
        if status["issues"]:
            print("\nIssues:")
            for item in status["issues"]:
                print(f"- {item}")
        print("\nNext steps:")
        for step in status["next_steps"]:
            print(f"- {step}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
