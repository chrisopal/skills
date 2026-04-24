#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = [
    "topic",
    "target_audience",
    "purpose",
    "style",
    "page_count",
    "key_points",
]

SLIDE_W = 13.333
SLIDE_H = 7.5


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a PPT job JSON file.")
    parser.add_argument("job", help="Path to the job JSON file")
    parser.add_argument("--artifacts", default="", help="Optional artifacts directory containing outline/slide_prompts/slide_specs")
    return parser


def is_missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, list) and not value:
        return True
    return False


def find_missing_required_fields(data: dict) -> list[str]:
    return [field for field in REQUIRED_FIELDS if is_missing(data.get(field))]


def has_confirmed_template(data: dict) -> bool:
    if not is_missing(data.get("template_id")) or not is_missing(data.get("template_name")):
        return True
    style = str(data.get("style", "")).strip()
    if not style:
        return False
    known_aliases = load_known_template_names()
    return style in known_aliases


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_known_template_names() -> set[str]:
    names = {
        "慧新",
        "慧新-产品及解决方案介绍",
        "慧新产品及解决方案介绍",
        "慧新-市场宣传",
        "慧新市场宣传",
        "慧新-内部会议",
        "慧新内部会议",
    }
    manifest_path = skill_root() / "assets" / "template_manifest.json"
    if not manifest_path.exists():
        return names
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return names
    for item in manifest.get("templates", []):
        if not isinstance(item, dict):
            continue
        template_id = str(item.get("template_id") or "").strip()
        if template_id:
            names.add(template_id)
        for alias in item.get("aliases", []):
            alias_text = str(alias).strip()
            if alias_text:
                names.add(alias_text)
        preset_asset = str(item.get("preset_asset") or "").strip()
        if preset_asset:
            preset_path = skill_root() / "assets" / preset_asset
            if preset_path.exists():
                try:
                    preset = json.loads(preset_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                template_name = str(preset.get("template_name") or "").strip()
                if template_name:
                    names.add(template_name)
    return names


def validate_job_data(
    data: dict,
    *,
    require_confirmation: bool = False,
    require_template_confirmation: bool = False,
) -> list[str]:
    missing = find_missing_required_fields(data)

    page_count = data.get("page_count")
    if page_count is not None and (not isinstance(page_count, int) or page_count <= 0):
        missing.append("page_count(valid positive integer)")

    if require_confirmation and not data.get("requirement_confirmed"):
        missing.append("requirement_confirmed")

    if require_template_confirmation and not has_confirmed_template(data):
        missing.append("template_id/template_name(confirmed template selection)")

    return missing


def read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def expected_page_count(job: dict[str, Any]) -> int:
    try:
        return int(job.get("page_count") or 0)
    except (TypeError, ValueError):
        return 0


def placement_issues(artifact_name: str, page_no: Any, placement: Any) -> list[str]:
    if not isinstance(placement, dict):
        return [f"{artifact_name} 第{page_no}页 image_placeholders placement must be an object."]
    issues: list[str] = []
    values: dict[str, float] = {}
    for key in ("x", "y", "w", "h"):
        try:
            values[key] = float(placement[key])
        except (KeyError, TypeError, ValueError):
            issues.append(f"{artifact_name} 第{page_no}页 image_placeholders placement.{key} must be numeric.")
    if issues:
        return issues
    if values["w"] <= 0 or values["h"] <= 0:
        issues.append(f"{artifact_name} 第{page_no}页 image_placeholders placement width/height must be positive.")
    if values["x"] < 0 or values["y"] < 0 or values["x"] + values["w"] > SLIDE_W or values["y"] + values["h"] > SLIDE_H:
        issues.append(f"{artifact_name} 第{page_no}页 image_placeholders placement is outside the 16:9 canvas.")
    return issues


def validate_image_placeholders(artifact_name: str, slide: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    page_no = slide.get("page_no", "?")
    placeholders = slide.get("image_placeholders", [])
    if not placeholders and isinstance(slide.get("visible_content"), dict):
        placeholders = slide["visible_content"].get("image_placeholders", [])
    if placeholders is None:
        return issues
    if not isinstance(placeholders, list):
        return [f"{artifact_name} 第{page_no}页 image_placeholders must be a list."]
    for index, placeholder in enumerate(placeholders, start=1):
        if not isinstance(placeholder, dict):
            issues.append(f"{artifact_name} 第{page_no}页 image_placeholders[{index}] must be an object.")
            continue
        if not str(placeholder.get("prompt") or placeholder.get("purpose") or "").strip():
            issues.append(f"{artifact_name} 第{page_no}页 image_placeholders[{index}] missing prompt.")
        if "placement" in placeholder:
            issues.extend(placement_issues(artifact_name, page_no, placeholder["placement"]))
    return issues


def validate_slide_collection(
    artifact_name: str,
    data: dict[str, Any],
    *,
    expected_pages: int,
    require_render_fields: bool = False,
) -> list[str]:
    issues: list[str] = []
    slides = data.get("slides")
    if not isinstance(slides, list):
        return [f"{artifact_name} missing slides list."]
    if expected_pages and len(slides) != expected_pages:
        issues.append(f"{artifact_name} 页数为 {len(slides)}，与 job.page_count={expected_pages} 不一致。")
    seen_pages: set[int] = set()
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            issues.append(f"{artifact_name} slides[{index}] must be an object.")
            continue
        try:
            page_no = int(slide.get("page_no") or index)
        except (TypeError, ValueError):
            issues.append(f"{artifact_name} slides[{index}] page_no must be an integer.")
            page_no = index
        if page_no in seen_pages:
            issues.append(f"{artifact_name} page_no={page_no} is duplicated.")
        seen_pages.add(page_no)
        visible_content = slide.get("visible_content") if isinstance(slide.get("visible_content"), dict) else {}
        title = str(slide.get("title") or visible_content.get("title") or "").strip()
        if not title:
            issues.append(f"{artifact_name} 第{page_no}页 missing title.")
        issues.extend(validate_image_placeholders(artifact_name, slide))
        if require_render_fields:
            if not isinstance(slide.get("visible_content"), dict) or not slide.get("visible_content", {}).get("title"):
                issues.append(f"{artifact_name} 第{page_no}页 missing visible_content.title.")
            layout_regions = slide.get("layout_regions")
            if not isinstance(layout_regions, dict) or not isinstance(layout_regions.get("content"), dict) or not isinstance(layout_regions.get("images"), list):
                issues.append(f"{artifact_name} 第{page_no}页 missing layout_regions.content/images.")
    return issues


def validate_artifacts(job: dict[str, Any], output_dir: Path) -> list[str]:
    expected_pages = expected_page_count(job)
    issues: list[str] = []
    artifact_specs = [
        ("outline.json", False),
        ("slide_prompts.json", False),
        ("slide_specs.json", True),
    ]
    for artifact_name, require_render_fields in artifact_specs:
        data = read_optional_json(output_dir / artifact_name)
        if data is None:
            continue
        issues.extend(
            validate_slide_collection(
                artifact_name,
                data,
                expected_pages=expected_pages,
                require_render_fields=require_render_fields,
            )
        )
    return issues


def resolve_artifacts_dir(job_path: Path, job: dict[str, Any], override: str) -> Path:
    if override:
        return Path(override).expanduser().resolve()
    output_dir = job.get("output", {}).get("directory") if isinstance(job.get("output"), dict) else ""
    if output_dir:
        return (job_path.parent / output_dir).resolve()
    return (job_path.parent / "artifacts").resolve()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    data = json.loads(job_path.read_text(encoding="utf-8"))

    missing = validate_job_data(
        data,
        require_confirmation=True,
        require_template_confirmation=True,
    )
    if missing:
        print("[MISSING] Required fields or confirmations:")
        for field in missing:
            print(f"- {field}")
        return 1

    artifacts_dir = resolve_artifacts_dir(job_path, data, args.artifacts)
    artifact_issues = validate_artifacts(data, artifacts_dir)
    if artifact_issues:
        print("[INVALID] Artifact schema issues:")
        for issue in artifact_issues:
            print(f"- {issue}")
        return 1

    print("[OK] Job input is complete enough to continue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
