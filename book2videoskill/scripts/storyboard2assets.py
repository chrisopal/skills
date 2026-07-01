#!/usr/bin/env python3
"""Create asset handoff files, subtitles, and asset_manifest.json."""

from __future__ import annotations

import argparse
import html
from pathlib import Path

from book2video_common import ensure_storyboard_v12_fields, hhmmss, read_json, relpath, write_json

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
</svg>
"""
    path.write_text(svg, encoding="utf-8")


def load_font(size: int, *, bold: bool = False):
    if ImageFont is None:
        return None
    candidates = [
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2 if bold else 0),
        ("/System/Library/Fonts/STHeiti Light.ttc", 1),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
        ("/Library/Fonts/Arial Unicode.ttf", 0),
    ]
    for candidate, index in candidates:
        try:
            return ImageFont.truetype(candidate, size=size, index=index)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(draw, text: str, font, max_width: int, max_lines: int | None = None) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines() or [text]:
        current = ""
        for char in paragraph:
            candidate = current + char
            if draw.textlength(candidate, font=font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                    if max_lines and len(lines) >= max_lines:
                        lines[-1] = lines[-1].rstrip("，。；、 ") + "..."
                        return lines
                current = char
        if current:
            lines.append(current)
            if max_lines and len(lines) >= max_lines:
                return lines
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("，。；、 ") + "..."
    return lines


def draw_wrapped(draw, xy: tuple[int, int], text: str, font, fill: str, max_width: int, line_gap: int = 10, max_lines: int | None = None) -> int:
    x, y = xy
    for line in wrap_text(draw, text, font, max_width, max_lines=max_lines):
        draw.text((x, y), line, font=font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_gap
    return y


def paste_cover(image, source_path: Path, box: tuple[int, int, int, int]) -> None:
    if Image is None or not source_path.exists():
        return
    source = Image.open(source_path).convert("RGB")
    target_w = box[2] - box[0]
    target_h = box[3] - box[1]
    ratio = max(target_w / source.width, target_h / source.height)
    resized = source.resize((int(source.width * ratio), int(source.height * ratio)))
    left = max(0, (resized.width - target_w) // 2)
    top = max(0, (resized.height - target_h) // 2)
    cropped = resized.crop((left, top, left + target_w, top + target_h))
    image.paste(cropped, box)


def draw_pill(draw, xy: tuple[int, int], text: str, font, fill: str = "#0B5D3B", text_fill: str = "#FFFFFF", x_pad: int = 24, y_pad: int = 10) -> tuple[int, int, int, int]:
    x, y = xy
    text_width = int(draw.textlength(text, font=font))
    bbox = draw.textbbox((x, y), text, font=font)
    h = bbox[3] - bbox[1] + y_pad * 2
    w = text_width + x_pad * 2
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=fill)
    draw.text((x + x_pad, y + y_pad - 2), text, font=font, fill=text_fill)
    return (x, y, x + w, y + h)


def draw_arrow(draw, start: tuple[int, int], end: tuple[int, int], fill: str, width: int = 5) -> None:
    draw.line((start[0], start[1], end[0], end[1]), fill=fill, width=width)
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    if abs(dx) > abs(dy):
        direction = 1 if dx >= 0 else -1
        points = [(end[0], end[1]), (end[0] - 18 * direction, end[1] - 12), (end[0] - 18 * direction, end[1] + 12)]
    else:
        direction = 1 if dy >= 0 else -1
        points = [(end[0], end[1]), (end[0] - 12, end[1] - 18 * direction), (end[0] + 12, end[1] - 18 * direction)]
    draw.polygon(points, fill=fill)


def draw_fallback_visual(
    draw,
    box: tuple[int, int, int, int],
    title: str,
    body: list[str],
    visual_type: str | None = None,
    visual_role: str | None = None,
) -> None:
    x1, y1, x2, y2 = box
    w = x2 - x1
    h = y2 - y1
    cx = x1 + w // 2
    cy = y1 + h // 2
    visual_key = " ".join([visual_type or "", visual_role or "", title, " ".join(body)]).lower()
    label_font = load_font(26, bold=True)
    small_font = load_font(22)

    draw.rounded_rectangle(box, radius=22, fill="#FFF7EC", outline="#F4A261", width=3)
    for offset, color in [(0, "#FDEAD6"), (46, "#E7F2EA"), (92, "#FFFDF7")]:
        draw.rounded_rectangle(
            (x1 + 34 + offset, y1 + 34 + offset, x2 - 34 - offset, y2 - 34 - offset),
            radius=24,
            outline=color,
            width=4,
        )

    def node(x: int, y: int, text: str, fill: str = "#FFFFFF", outline: str = "#0B5D3B") -> tuple[int, int, int, int]:
        bw, bh = 176, 78
        rect = (x - bw // 2, y - bh // 2, x + bw // 2, y + bh // 2)
        draw.rounded_rectangle(rect, radius=18, fill=fill, outline=outline, width=3)
        draw_wrapped(draw, (rect[0] + 20, rect[1] + 20), text, small_font, outline, bw - 40, line_gap=4, max_lines=1)
        return rect

    if any(term in visual_key for term in ["flywheel", "flow", "feedback", "环", "循环", "principles_system"]):
        positions = [
            (cx, y1 + int(h * 0.20), "目标"),
            (x1 + int(w * 0.76), y1 + int(h * 0.39), "现实"),
            (x1 + int(w * 0.66), y1 + int(h * 0.68), "根因"),
            (x1 + int(w * 0.34), y1 + int(h * 0.68), "原则"),
            (x1 + int(w * 0.24), y1 + int(h * 0.39), "执行"),
        ]
        points = [(px, py) for px, py, _ in positions]
        for start, end in zip(points, points[1:] + points[:1]):
            draw_arrow(draw, start, end, "#F97316", 5)
        for index, (px, py, text) in enumerate(positions):
            node(px, py, text, fill="#FFFFFF" if index % 2 else "#E7F2EA")
        draw.ellipse((cx - 92, cy - 92, cx + 92, cy + 92), fill="#0B5D3B", outline="#F97316", width=4)
        draw_wrapped(draw, (cx - 62, cy - 28), "原则\n复盘", label_font, "#FFFFFF", 124, line_gap=6, max_lines=2)
    elif any(term in visual_key for term in ["pyramid", "结构", "模型"]):
        levels = [
            (cx - 110, y1 + 135, cx + 110, y1 + 245, "#F97316", "结论"),
            (cx - 255, y1 + 300, cx + 255, y1 + 430, "#0B5D3B", "理由"),
            (cx - 390, y1 + 500, cx + 390, y1 + 660, "#FDEAD6", "事实 / 案例"),
        ]
        for rect in levels:
            draw.rounded_rectangle(rect[:4], radius=22, fill=rect[4], outline="#2F2A24", width=3)
            text_fill = "#FFFFFF" if rect[4] != "#FDEAD6" else "#0B5D3B"
            draw_wrapped(draw, (rect[0] + 34, rect[1] + 36), rect[5], label_font, text_fill, rect[2] - rect[0] - 68, max_lines=1)
        for x in [cx - 250, cx, cx + 250]:
            draw.line((x, y1 + 500, cx, y1 + 245), fill="#F4A261", width=4)
    elif any(term in visual_key for term in ["matrix", "decision", "决策", "择优", "可信度"]):
        grid = (x1 + 128, y1 + 165, x2 - 128, y2 - 180)
        draw.rounded_rectangle(grid, radius=22, fill="#FFFFFF", outline="#0B5D3B", width=4)
        rows, cols = 4, 4
        cell_w = (grid[2] - grid[0]) // cols
        cell_h = (grid[3] - grid[1]) // rows
        for col in range(1, cols):
            draw.line((grid[0] + col * cell_w, grid[1], grid[0] + col * cell_w, grid[3]), fill="#E7F2EA", width=4)
        for row in range(1, rows):
            draw.line((grid[0], grid[1] + row * cell_h, grid[2], grid[1] + row * cell_h), fill="#E7F2EA", width=4)
        for col, score in enumerate([0.35, 0.68, 0.54, 0.86]):
            bar_h = int(cell_h * 2.4 * score)
            bx = grid[0] + col * cell_w + 42
            by = grid[3] - bar_h - 34
            draw.rounded_rectangle((bx, by, bx + 62, grid[3] - 34), radius=14, fill="#F97316" if col == 3 else "#0B5D3B")
        draw_wrapped(draw, (grid[0] + 34, grid[1] + 28), "可信度加权", label_font, "#0B5D3B", grid[2] - grid[0] - 68, max_lines=1)
    elif any(term in visual_key for term in ["workflow", "ai", "skill", "工作流"]):
        y = cy - 45
        xs = [x1 + 180, cx, x2 - 180]
        labels = ["输入", "AI整理", "原则卡"]
        for i, (px, text) in enumerate(zip(xs, labels)):
            node(px, y, text, fill="#FFFFFF" if i != 1 else "#E7F2EA", outline="#F97316" if i == 1 else "#0B5D3B")
        draw_arrow(draw, (xs[0] + 92, y), (xs[1] - 96, y), "#F97316", 5)
        draw_arrow(draw, (xs[1] + 96, y), (xs[2] - 92, y), "#F97316", 5)
        for row, text in enumerate(["事实清单", "根因判断", "行动清单"]):
            node(cx, y + 135 + row * 96, text, fill="#FFFDF7", outline="#0B5D3B")
    elif any(term in visual_key for term in ["book", "author", "书籍", "内涵"]):
        book = (cx - 165, cy - 260, cx + 165, cy + 260)
        draw.rounded_rectangle(book, radius=26, fill="#202020", outline="#F97316", width=5)
        draw.rectangle((book[0] + 28, book[1] + 30, book[0] + 50, book[3] - 30), fill="#F97316")
        draw_wrapped(draw, (book[0] + 78, book[1] + 95), "BOOK\nTO\nSKILL", label_font, "#FFFDF7", 210, line_gap=12, max_lines=3)
        draw.rounded_rectangle((x1 + 120, cy - 120, cx - 230, cy + 155), radius=18, fill="#FFFFFF", outline="#0B5D3B", width=3)
        draw.line((x1 + 156, cy - 52, cx - 270, cy - 52), fill="#F4A261", width=6)
        draw.line((x1 + 156, cy + 22, cx - 270, cy + 22), fill="#E7F2EA", width=6)
        draw.rounded_rectangle((cx + 230, cy - 120, x2 - 120, cy + 155), radius=18, fill="#FFFFFF", outline="#0B5D3B", width=3)
        draw.line((cx + 270, cy - 52, x2 - 156, cy - 52), fill="#F4A261", width=6)
        draw.line((cx + 270, cy + 22, x2 - 156, cy + 22), fill="#E7F2EA", width=6)
    else:
        desk = (x1 + 105, y1 + 225, x2 - 105, y2 - 165)
        draw.rounded_rectangle(desk, radius=28, fill="#FFFFFF", outline="#0B5D3B", width=4)
        for i, color in enumerate(["#F97316", "#0B5D3B", "#F4A261"]):
            px = desk[0] + 70 + i * 190
            py = desk[1] + 90 + (i % 2) * 70
            draw.rounded_rectangle((px, py, px + 145, py + 98), radius=18, fill=color)
        draw.line((desk[0] + 70, desk[3] - 135, desk[2] - 70, desk[3] - 135), fill="#E7F2EA", width=9)
        draw.line((desk[0] + 70, desk[3] - 80, desk[2] - 190, desk[3] - 80), fill="#FDEAD6", width=9)
        draw_wrapped(draw, (desk[0] + 70, desk[1] + 270), "问题 -> 结构 -> 行动", label_font, "#0B5D3B", desk[2] - desk[0] - 140, max_lines=1)


def write_png_card(
    path: Path,
    title: str,
    subtitle: str,
    body: list[str],
    width: int,
    height: int,
    image_source: Path | None = None,
    visual_type: str | None = None,
    visual_role: str | None = None,
) -> None:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required to render PNG poster/video frames.")
    image = Image.new("RGB", (width, height), "#FFFDF7")
    draw = ImageDraw.Draw(image)
    is_scene = height > 1500
    margin = 54 if is_scene else 64
    card_x = margin
    card_y = margin
    card_w = width - 2 * margin
    card_h = height - 2 * margin
    small_font = load_font(24 if is_scene else 22)
    title_font = load_font(60 if is_scene else 58, bold=True)
    subtitle_font = load_font(34 if is_scene else 30)
    body_font = load_font(28 if is_scene else 24)

    draw.rounded_rectangle((card_x, card_y, card_x + card_w, card_y + card_h), radius=26, fill="#FFFFFF", outline="#F4A261", width=3)
    draw_pill(draw, (card_x + 30, card_y + 28), "一本书，一个 AI Skill", small_font)

    if is_scene:
        caption_h = 340
        hero_box = (card_x + 30, card_y + 104, card_x + card_w - 30, card_y + card_h - caption_h)
        content_y = hero_box[3] + 34
    else:
        hero_box = (card_x + 30, card_y + 106, card_x + card_w - 30, card_y + 106 + int(card_h * 0.36))
        content_y = hero_box[3] + 42

    if image_source and image_source.exists():
        paste_cover(image, image_source, hero_box)
        draw.rounded_rectangle(hero_box, radius=22, outline="#F4A261", width=3)
    else:
        draw_fallback_visual(draw, hero_box, title, body, visual_type=visual_type, visual_role=visual_role)

    x = card_x + 44
    max_width = card_w - 88
    y = content_y
    y = draw_wrapped(draw, (x, y), title, title_font, "#F97316", max_width, line_gap=12, max_lines=2)
    y += 12
    y = draw_wrapped(draw, (x, y), subtitle, subtitle_font, "#0B5D3B", max_width, line_gap=10, max_lines=2 if is_scene else 1)
    if not is_scene:
        y += 26
        draw.line((x, y, card_x + card_w - 44, y), fill="#F4A261", width=3)
        y += 28

    if is_scene:
        # Keep scene frames clean: image, title, visible subtitle, no footer filler.
        pass
    else:
        compact_items = [item.split("：", 1)[0] for item in body[:4]]
        gap = 18
        box_w = (max_width - gap) // 2
        box_h = 86
        for index, item in enumerate(compact_items, start=1):
            col = (index - 1) % 2
            row = (index - 1) // 2
            box_x = x + col * (box_w + gap)
            box_y = y + row * (box_h + 16)
            draw.rounded_rectangle((box_x, box_y, box_x + box_w, box_y + box_h), radius=18, fill="#FFF7EC", outline="#F4A261", width=2)
            badge_color = "#F97316" if index == 1 else "#0B5D3B"
            draw.rounded_rectangle((box_x + 18, box_y + 18, box_x + 58, box_y + 58), radius=12, fill=badge_color)
            draw.text((box_x + 31, box_y + 25), f"{index}", font=small_font, fill="#FFFFFF")
            draw_wrapped(draw, (box_x + 74, box_y + 24), item, body_font, "#333333", box_w - 94, line_gap=8, max_lines=1)
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
    if ensure_storyboard_v12_fields(storyboard):
        write_json(project_dir / "storyboard.json", storyboard)
    cover_plan = read_json(project_dir / "cover_poster_plan.json")

    scene_dir = project_dir / "scene_images"
    imagegen_source_dir = project_dir / "imagegen_sources"
    tts_dir = project_dir / "tts_audio"
    subtitle_dir = project_dir / "subtitles"
    bgm_dir = project_dir / "bgm"
    for directory in [scene_dir, imagegen_source_dir, tts_dir, subtitle_dir, bgm_dir]:
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
        imagegen_source_dir / "poster.png",
    )

    scene_images = []
    tts_assets = []
    subtitle_assets = []
    imagegen_source_count = 1 if (imagegen_source_dir / "poster.png").exists() else 0
    imagegen_prompts = [
        {
            "assetId": "poster",
            "kind": "xiaohongshu_poster",
            "prompt": cover_plan.get("mascot", {}).get("imagePrompt", "")
            or f"{cover_plan['headline']}，小红书知识宣传海报，橙色主色，深绿色辅助，暖白背景，商业信息图风格，中文文字由组件渲染",
            "aspectRatio": style_bible.get("coverAspectRatio", "4:5"),
            "textRenderingPolicy": "Render final Chinese text in components; imagegen should provide visual illustration or texture only.",
            "targetPath": "imagegen_sources/poster.png",
            "compositedPath": "poster.png",
        }
    ]
    elapsed = 0
    for scene in storyboard["scenes"]:
        scene_id = scene["sceneId"]
        scene_image = scene_dir / f"{scene_id}.svg"
        scene_png = scene_dir / f"{scene_id}.png"
        tts_file = tts_dir / f"{scene_id}.tts.txt"
        subtitle_file = subtitle_dir / f"{scene_id}.srt"
        write_svg(scene_image, scene["title"], scene["visualDescription"][:48], style_bible["width"], style_bible["height"])
        write_png_card(
            scene_png,
            scene["title"],
            scene["narration"],
            [scene["goal"], scene["visualDescription"]],
            style_bible["width"],
            style_bible["height"],
            imagegen_source_dir / f"{scene_id}.png",
            visual_type=scene.get("visualType"),
            visual_role=scene.get("visualRole"),
        )
        tts_file.write_text(scene["narration"] + "\n", encoding="utf-8")
        write_srt(subtitle_file, scene["subtitle"], scene["durationSec"])
        imagegen_scene_source = imagegen_source_dir / f"{scene_id}.png"
        imagegen_scene_exists = imagegen_scene_source.exists()
        if imagegen_scene_exists:
            imagegen_source_count += 1
        scene_images.append(
            {
                "sceneId": scene_id,
                "path": relpath(scene_png, project_dir),
                "svgPath": relpath(scene_image, project_dir),
                "status": "generated",
                "provider": "imagegen_with_component_overlay" if imagegen_scene_exists else "component_png_renderer_fallback",
                "requiresProvider": False,
                "preferredProvider": "imagegen",
                "imagegenSourcePath": f"imagegen_sources/{scene_id}.png",
                "imagegenSourceExists": imagegen_scene_exists,
                "prompt": scene["imageSourceStrategy"].get("imagePrompt", ""),
            }
        )
        imagegen_prompts.append(
            {
                "assetId": scene_id,
                "kind": "scene_visual",
                "prompt": scene["imageSourceStrategy"].get("imagePrompt", ""),
                "aspectRatio": style_bible.get("aspectRatio", "9:16"),
                "textRenderingPolicy": "Render final Chinese text in components; imagegen should provide visual illustration or texture only.",
                "targetPath": f"imagegen_sources/{scene_id}.png",
                "compositedPath": relpath(scene_png, project_dir),
                "fallbackPath": relpath(scene_image, project_dir),
            }
        )
        tts_assets.append(
            {
                "sceneId": scene_id,
                "path": relpath(tts_dir / f"{scene_id}.mp3", project_dir),
                "handoffPath": relpath(tts_file, project_dir),
                "status": "pending",
                "provider": "openrouter",
                "requiresProvider": False,
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
        "imageProvider": {
            "default": "imagegen",
            "fallback": "component_png_renderer",
            "promptManifest": "imagegen_prompts.json",
        },
        "coverImage": {
            "path": relpath(poster_path, project_dir),
            "svgPath": relpath(cover_path, project_dir),
            "status": "generated",
            "provider": "imagegen_with_component_overlay" if (imagegen_source_dir / "poster.png").exists() else "component_png_renderer_fallback",
            "requiresProvider": False,
            "preferredProvider": "imagegen",
            "imagegenSourcePath": "imagegen_sources/poster.png",
            "imagegenSourceExists": (imagegen_source_dir / "poster.png").exists(),
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
    write_json(project_dir / "imagegen_prompts.json", imagegen_prompts)
    write_json(project_dir / "asset_manifest.json", manifest)
    (project_dir / "assets_ready_report.md").write_text(
        "\n".join(
            [
                "# Assets Ready Report",
                "",
                "Status: imagegen prompts prepared; imagegen sources composited when present.",
                "Default image provider: `imagegen`.",
                "Imagegen prompt manifest: `imagegen_prompts.json`.",
                "Imagegen source directory: `imagegen_sources/`.",
                f"Imagegen sources found: {imagegen_source_count}.",
                "Composited poster: `poster.png` generated.",
                "Composited scene frames: `scene_images/*.png` generated for Remotion/video assembly.",
                "",
                "- Use the built-in imagegen plugin for final poster/scene visuals, then copy selected images into `imagegen_sources/` and rerun this script.",
                "- Deterministic component frames remain available as fallback so the video pipeline still closes.",
                "- TTS defaults to OpenRouter via `openrouter_tts.py`; text handoffs remain for debugging.",
                "- BGM is a music brief handoff.",
                "- Subtitles are generated SRT files.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"asset_project: {project_dir}")
    print(f"scene_images: {len(scene_images)}")
    print("status: imagegen_composited" if imagegen_source_count else "component_fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
