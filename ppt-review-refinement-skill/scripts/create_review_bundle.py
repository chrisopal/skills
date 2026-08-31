#!/usr/bin/env python3
"""Build a self-contained review bundle for an existing PPTX."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analyze_pptx import analyze_deck, markdown_report
from common import ensure_dir, load_json, sha256_file, write_json
from make_montage import create_montage
from render_pptx import render_pptx

SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = SKILL_ROOT / "templates"


def copy_and_patch_json(template_name: str, destination: Path, source_filename: str) -> None:
    data = load_json(TEMPLATES / template_name)
    if "source_file" in data:
        data["source_file"] = source_filename
    write_json(destination, data)


def create_review_bundle(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    render: bool = True,
    copy_source: bool = False,
    width_px: int = 1600,
    height_px: int = 900,
) -> dict[str, Any]:
    input_path = Path(input_path).resolve()
    output_dir = ensure_dir(output_dir).resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    analysis = analyze_deck(input_path)
    write_json(output_dir / "analysis.json", analysis)
    (output_dir / "structural_audit.md").write_text(markdown_report(analysis), encoding="utf-8")

    copy_and_patch_json("deck_context.template.json", output_dir / "deck_context.json", input_path.name)
    shutil.copy2(TEMPLATES / "change_manifest.template.json", output_dir / "change_manifest.json")
    shutil.copy2(TEMPLATES / "style_tokens.template.json", output_dir / "style_tokens.json")
    shutil.copy2(TEMPLATES / "review_report.template.md", output_dir / "review_report.md")
    shutil.copy2(TEMPLATES / "approval_form.template.md", output_dir / "approval_form.md")
    shutil.copy2(TEMPLATES / "pilot_review.template.md", output_dir / "pilot_review.md")

    if copy_source:
        source_dir = ensure_dir(output_dir / "source")
        shutil.copy2(input_path, source_dir / input_path.name)

    render_status = "skipped"
    render_error = ""
    rendered_count = 0
    slides_dir = ensure_dir(output_dir / "slides")
    if render:
        try:
            render_result = render_pptx(
                input_path,
                slides_dir,
                width_px=width_px,
                height_px=height_px,
                keep_pdf=False,
            )
            rendered_count = int(render_result["slide_count"])
            create_montage(slides_dir, output_dir / "montage.png")
            render_status = "complete"
        except Exception as exc:  # noqa: BLE001 - retain structural review bundle.
            render_status = "failed"
            render_error = str(exc)
            (output_dir / "RENDER_FAILED.txt").write_text(
                "页面渲染失败。结构审计仍可使用，但视觉评审尚未完成。\n\n" + render_error + "\n",
                encoding="utf-8",
            )

    manifest = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_path),
        "source_sha256": sha256_file(input_path),
        "output_dir": str(output_dir),
        "structural_audit": "complete",
        "render_status": render_status,
        "render_error": render_error,
        "rendered_slide_count": rendered_count,
        "expected_slide_count": analysis["deck"]["slide_count"],
        "visual_review_ready": render_status == "complete" and rendered_count == analysis["deck"]["slide_count"],
        "files": sorted(str(p.relative_to(output_dir)) for p in output_dir.rglob("*") if p.is_file()),
    }
    write_json(output_dir / "bundle_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Create a PPT review bundle with audit, renders, and templates.")
    parser.add_argument("input", help="Input PPTX/PPTM")
    parser.add_argument("--out", required=True, help="Output review bundle directory")
    parser.add_argument("--no-render", action="store_true", help="Skip slide rendering")
    parser.add_argument("--copy-source", action="store_true", help="Copy the source deck into the bundle")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--height", type=int, default=900)
    args = parser.parse_args()
    try:
        manifest = create_review_bundle(
            args.input,
            args.out,
            render=not args.no_render,
            copy_source=args.copy_source,
            width_px=args.width,
            height_px=args.height,
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        if manifest["render_status"] == "failed":
            print("WARNING: Structural audit succeeded, but rendering failed.", file=sys.stderr)
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
