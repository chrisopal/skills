#!/usr/bin/env python3
"""Create render_plan.json, render report, and a project bundle."""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

from book2video_common import read_json, relpath, write_json


def build_render_plan(project_dir: Path, style_bible: dict, storyboard: dict) -> dict:
    return {
        "renderer": "remotion",
        "compositionName": "BookVideoComposition",
        "coverCompositionName": "CoverPosterComposition",
        "fps": style_bible["fps"],
        "width": style_bible["width"],
        "height": style_bible["height"],
        "coverWidth": style_bible["coverWidth"],
        "coverHeight": style_bible["coverHeight"],
        "durationSec": storyboard["targetDurationSec"],
        "durationLimitSec": storyboard["durationLimitSec"],
        "sceneOrder": [scene["sceneId"] for scene in storyboard["scenes"]],
        "globalStyleRef": "style_bible.json",
        "storyboardRef": "storyboard.json",
        "assetManifestRef": "asset_manifest.json",
        "narrationRef": "narration_script.md",
        "defaultTransition": {"type": "fade", "durationMs": 320},
        "subtitle": {"enabled": True, "mode": "key_sentence", "maxLines": 2, "highlightColor": "#FF6A00"},
        "bgm": {"enabled": True, "ducking": True, "volume": 0.18},
        "export": {"format": "mp4", "quality": "standard", "platform": style_bible["platform"]},
        "providerStatus": "mock-render-plan",
    }


def zip_project(project_dir: Path, zip_path: Path) -> None:
    include_suffixes = {".json", ".md", ".svg", ".srt", ".txt"}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(project_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            if path.suffix in include_suffixes:
                archive.write(path, relpath(path, project_dir))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, help="Book2Video project directory")
    parser.add_argument("--renderer", default="remotion", choices=["remotion", "hyperframe"])
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    style_bible = read_json(project_dir / "style_bible.json")
    storyboard = read_json(project_dir / "storyboard.json")
    asset_manifest = read_json(project_dir / "asset_manifest.json")

    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    render_plan = build_render_plan(project_dir, style_bible, storyboard)
    render_plan["renderer"] = args.renderer
    if args.renderer == "hyperframe":
        render_plan["providerStatus"] = "adapter-designed-not-implemented"
    write_json(project_dir / "render_plan.json", render_plan)

    mock_video = output_dir / "final_video.mock.txt"
    mock_video.write_text(
        "Mock render placeholder. Wire a real RenderProvider to produce output/final_video.mp4.\n",
        encoding="utf-8",
    )

    render_report = project_dir / "render_report.md"
    render_report.write_text(
        "\n".join(
            [
                "# Render Report",
                "",
                f"Renderer: {args.renderer}",
                f"Duration: {storyboard['targetDurationSec']} sec",
                f"Scenes: {len(storyboard['scenes'])}",
                "",
                "Status: mock render handoff created.",
                "",
                "Real media still required:",
                "- output/final_video.mp4",
                "- cover.png if a PNG poster is required",
                "- tts_audio/*.mp3",
                "- bgm/main.mp3",
                "",
                f"Asset placeholders: {sum(1 for item in asset_manifest['sceneImages'] if item.get('status') == 'placeholder')} scene visuals",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle_path = project_dir / "project_bundle.zip"
    zip_project(project_dir, bundle_path)

    print(f"render_project: {project_dir}")
    print(f"mock_video: {mock_video}")
    print(f"bundle: {bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
