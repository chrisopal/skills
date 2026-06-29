#!/usr/bin/env python3
"""Create asset handoff files, subtitles, and asset_manifest.json."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from book2video_common import hhmmss, read_json, relpath, write_json

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - validated at runtime.
    Image = None
    ImageDraw = None
    ImageFont = None


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


def load_font(size: int, *, bold: bool = False):
    if ImageFont is None:
        return None
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size=size, index=1 if bold else 0)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(draw, text: str, font, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw, xy: tuple[int, int], text: str, font, fill: str, max_width: int, line_gap: int = 10) -> int:
    x, y = xy
    for line in wrap_text(draw, text, font, max_width):
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_gap
    return y


def write_png_card(path: Path, title: str, subtitle: str, body: list[str], width: int, height: int) -> None:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required to render PNG poster/video frames.")
    image = Image.new("RGB", (width, height), "#FFFDF7")
    draw = ImageDraw.Draw(image)
    title_font = load_font(58 if height > 1400 else 42, bold=True)
    subtitle_font = load_font(34 if height > 1400 else 26)
    body_font = load_font(30 if height > 1400 else 22)
    small_font = load_font(24 if height > 1400 else 18)

    margin = int(width * 0.07)
    card_x = margin
    card_y = margin
    card_w = width - 2 * margin
    card_h = height - 2 * margin
    draw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=28, fill="#FFFFFF", outline="#F4A261", width=4)
    draw.rounded_rectangle((card_x + 24, card_y + 24, card_x + 230, card_y + 78), radius=24, fill="#0B5D3B")
    draw.text((card_x + 46, card_y + 34), "一本书，一个AI Skill", font=small_font, fill="#FFFFFF")
    y = card_y + 120
    y = draw_wrapped(draw, (card_x + 40, y), title, title_font, "#F97316", card_w - 80, line_gap=14)
    y += 14
    y = draw_wrapped(draw, (card_x + 40, y), subtitle, subtitle_font, "#0B5D3B", card_w - 80, line_gap=12)
    y += 24
    draw.line((card_x + 40, y, card_x + card_w - 40, y), fill="#F4A261", width=4)
    y += 38
    for index, item in enumerate(body[:6], start=1):
        row_y = y
        draw.rounded_rectangle((card_x + 40, row_y, card_x + 98, row_y + 58), radius=16, fill="#F97316" if index == 1 else "#0B5D3B")
        draw.text((card_x + 58, row_y + 13), f"{index:02d}", font=small_font, fill="#FFFFFF")
        y = draw_wrapped(draw, (card_x + 120, row_y + 6), item, body_font, "#333333", card_w - 180, line_gap=8)
        y = max(y + 20, row_y + 80)
        if y > card_y + card_h - 140:
            break
    draw.text((card_x + 40, card_y + card_h - 84), "Text rendered by deterministic component layer; image models provide optional visual elements.", font=small_font, fill="#666666")
    image.save(path)


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
    poster_path = project_dir / "poster.png"
    write_svg(cover_path, cover_plan["headline"], cover_plan["subtitle"], style_bible["coverWidth"], style_bible["coverHeight"])
    write_svg(mascot_path, "原创书籍角色", "专业、克制、不过度卡通", 512, 512)
    write_png_card(
        poster_path,
        cover_plan["headline"],
        cover_plan["subtitle"],
        [
            str(module.get("title", "")) + "：" + (" / ".join(module.get("body", [])) if isinstance(module.get("body"), list) else str(module.get("body", "")))
            for module in cover_plan.get("modules", [])
        ],
        style_bible["coverWidth"],
        style_bible["coverHeight"],
    )

    scene_images = []
    tts_assets = []
    subtitle_assets = []
    elapsed = 0
    for scene in storyboard["scenes"]:
        scene_id = scene["sceneId"]
        scene_image = scene_dir / f"{scene_id}.svg"
        scene_png = scene_dir / f"{scene_id}.png"
        tts_file = tts_dir / f"{scene_id}.tts.txt"
        subtitle_file = subtitle_dir / f"{scene_id}.srt"
        write_svg(scene_image, scene["title"], scene["visualDescription"][:48], style_bible["width"], style_bible["height"])
        write_png_card(scene_png, scene["title"], scene["narration"], [scene["goal"], scene["visualDescription"]], style_bible["width"], style_bible["height"])
        tts_file.write_text(scene["narration"] + "\n", encoding="utf-8")
        write_srt(subtitle_file, scene["subtitle"], scene["durationSec"])
        scene_images.append(
            {
                "sceneId": scene_id,
                "path": relpath(scene_png, project_dir),
                "svgPath": relpath(scene_image, project_dir),
                "status": "generated",
                "provider": "component_png_renderer",
                "requiresProvider": False,
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
            "path": relpath(poster_path, project_dir),
            "svgPath": relpath(cover_path, project_dir),
            "status": "generated",
            "provider": "component_png_renderer",
            "requiresProvider": False,
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
                "Poster: `poster.png` generated.",
                "Scene frames: `scene_images/*.png` generated for Remotion/video assembly.",
                "",
                "- Cover and scene visuals use deterministic component rendering by default.",
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
