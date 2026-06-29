#!/usr/bin/env python3
"""Create asset handoff files, subtitles, and asset_manifest.json."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from book2video_common import hhmmss, read_json, relpath, write_json


def write_svg(path: Path, title: str, subtitle: str, width: int, height: int) -> None:
    escaped_title = html.escape(title)
    escaped_subtitle = html.escape(subtitle)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="#FFFDF7"/>
  <rect x="64" y="64" width="{width - 128}" height="{height - 128}" rx="28" fill="#FFFFFF" stroke="#F4A261" stroke-width="4"/>
  <text x="96" y="150" font-family="Arial, sans-serif" font-size="54" font-weight="700" fill="#F97316">{escaped_title}</text>
  <text x="96" y="230" font-family="Arial, sans-serif" font-size="30" fill="#0B5D3B">{escaped_subtitle}</text>
  <line x1="96" y1="282" x2="{width - 96}" y2="282" stroke="#F4A261" stroke-width="4"/>
  <text x="96" y="{height - 110}" font-family="Arial, sans-serif" font-size="28" fill="#333333">Text is rendered by component, not image model.</text>
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def write_srt(path: Path, text: str, duration: int) -> None:
    path.write_text(f"1\n{hhmmss(0)} --> {hhmmss(duration)}\n{text}\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, help="Book2Video project directory")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    style_bible = read_json(project_dir / "style_bible.json")
    storyboard = read_json(project_dir / "storyboard.json")
    cover_plan = read_json(project_dir / "cover_poster_plan.json")

    scene_dir = project_dir / "scene_images"
    tts_dir = project_dir / "tts_audio"
    subtitle_dir = project_dir / "subtitles"
    bgm_dir = project_dir / "bgm"
    for directory in [scene_dir, tts_dir, subtitle_dir, bgm_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    cover_path = project_dir / "cover.svg"
    mascot_path = project_dir / "mascot.svg"
    write_svg(cover_path, cover_plan["headline"], cover_plan["subtitle"], style_bible["coverWidth"], style_bible["coverHeight"])
    write_svg(mascot_path, "原创书籍角色", "专业、克制、不过度卡通", 512, 512)

    scene_images = []
    tts_assets = []
    subtitle_assets = []
    elapsed = 0
    for scene in storyboard["scenes"]:
        scene_id = scene["sceneId"]
        scene_image = scene_dir / f"{scene_id}.svg"
        tts_file = tts_dir / f"{scene_id}.tts.txt"
        subtitle_file = subtitle_dir / f"{scene_id}.srt"
        write_svg(scene_image, scene["title"], scene["visualDescription"][:48], style_bible["width"], style_bible["height"])
        tts_file.write_text(scene["narration"] + "\n", encoding="utf-8")
        write_srt(subtitle_file, scene["subtitle"], scene["durationSec"])
        scene_images.append(
            {
                "sceneId": scene_id,
                "path": relpath(scene_image, project_dir),
                "status": "placeholder",
                "provider": "component_svg_fallback",
                "requiresProvider": True,
                "prompt": scene["imageSourceStrategy"].get("imagePrompt", ""),
            }
        )
        tts_assets.append(
            {
                "sceneId": scene_id,
                "path": relpath(tts_file, project_dir),
                "status": "placeholder",
                "provider": "tts_handoff_text",
                "requiresProvider": True,
                "durationSec": scene["durationSec"],
            }
        )
        subtitle_assets.append(
            {
                "sceneId": scene_id,
                "path": relpath(subtitle_file, project_dir),
                "status": "generated",
                "format": "srt",
                "startSec": elapsed,
                "durationSec": scene["durationSec"],
            }
        )
        elapsed += scene["durationSec"]

    bgm_path = bgm_dir / "main.music.txt"
    bgm_path.write_text(
        f"Generate calm structured BGM, loopable, duration >= {storyboard['targetDurationSec']} sec, volume 0.18, duck under narration.\n",
        encoding="utf-8",
    )

    manifest = {
        "projectName": storyboard["projectName"],
        "durationSec": storyboard["targetDurationSec"],
        "aspectRatio": style_bible["aspectRatio"],
        "coverImage": {
            "path": relpath(cover_path, project_dir),
            "status": "placeholder",
            "provider": "component_svg_fallback",
            "requiresProvider": True,
        },
        "mascotImage": {
            "path": relpath(mascot_path, project_dir),
            "status": "placeholder",
            "provider": "component_svg_fallback",
            "requiresProvider": True,
        },
        "sceneImages": scene_images,
        "ttsAssets": tts_assets,
        "subtitleAssets": subtitle_assets,
        "musicAsset": {
            "path": relpath(bgm_path, project_dir),
            "status": "placeholder",
            "provider": "music_handoff_text",
            "requiresProvider": True,
            "durationSec": storyboard["targetDurationSec"],
        },
    }
    write_json(project_dir / "asset_manifest.json", manifest)
    (project_dir / "assets_ready_report.md").write_text(
        "\n".join(
            [
                "# Assets Ready Report",
                "",
                "Status: scaffold placeholders created.",
                "",
                "- Cover and scene visuals are SVG component fallbacks.",
                "- TTS files are text handoffs for a real TTS provider.",
                "- BGM is a music brief handoff.",
                "- Subtitles are generated SRT files.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"asset_project: {project_dir}")
    print(f"scene_images: {len(scene_images)}")
    print("status: placeholder_handoff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
