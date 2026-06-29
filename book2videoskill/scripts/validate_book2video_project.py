#!/usr/bin/env python3
"""Validate a Book2VideoSkill project directory."""

from __future__ import annotations

import argparse
from pathlib import Path

from book2video_common import is_pyramid_principle, read_json


REQUIRED_FILES = [
    "video_brief.md",
    "book_core.json",
    "style_bible.json",
    "cover_poster_plan.json",
    "storyboard.json",
    "narration_script.md",
    "xiaohongshu_publish.md",
]

ASSET_STAGE_FILES = ["asset_manifest.json", "assets_ready_report.md"]
RENDER_STAGE_FILES = ["render_plan.json", "render_report.md", "project_bundle.zip"]
PYRAMID_TERMS = ["结论先行", "以上统下", "归类分组", "逻辑递进", "AI汇报结构生成器"]


def require_file(project_dir: Path, rel_path: str, errors: list[str]) -> Path:
    path = project_dir / rel_path
    if not path.exists():
        errors.append(f"missing required file: {rel_path}")
    return path


def validate_path_refs(project_dir: Path, manifest: dict, errors: list[str]) -> None:
    refs: list[str] = []
    for key in ["coverImage", "mascotImage", "musicAsset"]:
        if key in manifest and manifest[key].get("path"):
            refs.append(manifest[key]["path"])
    for key in ["sceneImages", "ttsAssets", "subtitleAssets"]:
        for item in manifest.get(key, []):
            if item.get("path"):
                refs.append(item["path"])
    for rel_path in refs:
        if not (project_dir / rel_path).exists():
            errors.append(f"asset manifest path does not exist: {rel_path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", help="Book2Video project directory")
    parser.add_argument("--require-assets", action="store_true", help="Require asset stage files")
    parser.add_argument("--require-render", action="store_true", help="Require real final render media")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    errors: list[str] = []
    warnings: list[str] = []

    if not project_dir.exists() or not project_dir.is_dir():
        errors.append(f"project directory not found: {project_dir}")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    for rel_path in REQUIRED_FILES:
        require_file(project_dir, rel_path, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    book_core = read_json(project_dir / "book_core.json")
    style_bible = read_json(project_dir / "style_bible.json")
    cover_plan = read_json(project_dir / "cover_poster_plan.json")
    storyboard = read_json(project_dir / "storyboard.json")

    scenes = storyboard.get("scenes", [])
    if not 6 <= len(scenes) <= 8:
        errors.append(f"storyboard scene count must be 6-8, got {len(scenes)}")
    total_duration = sum(int(scene.get("durationSec", 0)) for scene in scenes)
    limit = int(storyboard.get("durationLimitSec", style_bible.get("durationLimitSec", 300)))
    if total_duration > limit:
        errors.append(f"storyboard duration {total_duration} exceeds limit {limit}")
    if storyboard.get("targetDurationSec") != total_duration:
        errors.append("storyboard targetDurationSec does not equal sum(scene.durationSec)")

    required_scene_fields = [
        "sceneId",
        "title",
        "durationSec",
        "goal",
        "visualDescription",
        "imageSourceStrategy",
        "onscreenText",
        "subtitle",
        "narration",
        "motion",
        "transitionIn",
        "transitionOut",
        "musicCue",
        "tts",
    ]
    for scene in scenes:
        for field in required_scene_fields:
            if field not in scene:
                errors.append(f"scene {scene.get('sceneId', '<missing>')} missing field: {field}")

    palette = style_bible.get("visualStyle", {}).get("palette", {})
    if palette.get("primary") != "#F97316" or palette.get("secondary") != "#0B5D3B":
        errors.append("style palette must use orange primary #F97316 and green secondary #0B5D3B")
    if cover_plan.get("aspectRatio") != "4:5":
        errors.append("coverPosterPlan aspectRatio must default to 4:5")

    all_text = "\n".join(
        [
            (project_dir / "video_brief.md").read_text(encoding="utf-8"),
            (project_dir / "narration_script.md").read_text(encoding="utf-8"),
            (project_dir / "xiaohongshu_publish.md").read_text(encoding="utf-8"),
            str(book_core),
            str(cover_plan),
        ]
    )
    if is_pyramid_principle(book_core.get("bookTitle", "")):
        for term in PYRAMID_TERMS:
            if term not in all_text:
                errors.append(f"pyramid principle output missing term: {term}")
        if book_core.get("visualModel", {}).get("type") != "pyramid":
            errors.append("pyramid principle visualModel.type must be pyramid")

    has_asset_stage = (project_dir / "asset_manifest.json").exists()
    if args.require_assets or has_asset_stage:
        for rel_path in ASSET_STAGE_FILES:
            require_file(project_dir, rel_path, errors)
        if (project_dir / "asset_manifest.json").exists():
            manifest = read_json(project_dir / "asset_manifest.json")
            validate_path_refs(project_dir, manifest, errors)
            if len(manifest.get("sceneImages", [])) != len(scenes):
                errors.append("asset_manifest sceneImages count must match storyboard scenes")
            if len(manifest.get("ttsAssets", [])) != len(scenes):
                errors.append("asset_manifest ttsAssets count must match storyboard scenes")
            if any(item.get("status") == "placeholder" for item in manifest.get("sceneImages", [])):
                warnings.append("scene visuals are placeholder handoffs; real image provider not yet run")

    has_render_stage = (project_dir / "render_plan.json").exists()
    if has_render_stage:
        for rel_path in RENDER_STAGE_FILES:
            require_file(project_dir, rel_path, errors)
        render_plan = read_json(project_dir / "render_plan.json")
        if render_plan.get("durationSec") != total_duration:
            errors.append("render_plan durationSec must equal storyboard duration")
        if not (project_dir / "output" / "final_video.mock.txt").exists():
            warnings.append("mock render handoff missing; real render may still be pending")

    if args.require_render:
        real_outputs = [
            "output/final_video.mp4",
            "cover.png",
            "tts_audio/S01.mp3",
            "bgm/main.mp3",
        ]
        for rel_path in real_outputs:
            require_file(project_dir, rel_path, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1

    print(f"OK: {project_dir} scenes={len(scenes)} duration={total_duration}s")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
