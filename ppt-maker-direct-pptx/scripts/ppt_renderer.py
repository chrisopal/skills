#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Theme:
    background: str
    surface: str
    primary: str
    accent: str
    neutral: str
    text: str
    text_muted: str
    divider: str
    title_font: str
    body_font: str


def strip_hash(value: str | None, fallback: str) -> str:
    raw = (value or fallback).replace("#", "").strip()
    if len(raw) == 3:
        raw = "".join(ch * 2 for ch in raw)
    return raw.upper()


def to_theme(master_style: dict[str, Any]) -> Theme:
    colors = master_style.get("color_strategy", {})
    typography = master_style.get("typography", {})
    return Theme(
        background=strip_hash(colors.get("background"), "FFFFFF"),
        surface=strip_hash(colors.get("section_background"), "F5F7FA"),
        primary=strip_hash(colors.get("secondary_teal") or colors.get("primary_blue"), "0F95B6"),
        accent=strip_hash(colors.get("primary_green") or colors.get("accent_green"), "A8D86B"),
        neutral=strip_hash(colors.get("neutral_gray"), "D9D9D9"),
        text=strip_hash(colors.get("text_primary"), "1E1E1E"),
        text_muted=strip_hash(colors.get("text_secondary"), "6B7280"),
        divider=strip_hash(colors.get("divider"), "E5E7EB"),
        title_font=str(typography.get("title_font", "Microsoft YaHei")),
        body_font=str(typography.get("body_font", "Microsoft YaHei")),
    )


def split_summary(text: str, limit: int = 36) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= limit:
        return [text]
    words = text.replace("；", "，").split("，")
    lines: list[str] = []
    current = ""
    for word in words:
        word = word.strip()
        if not word:
            continue
        candidate = f"{current}｜{word}" if current else word
        if len(candidate) > limit and current:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines[:3]


def normalize_blocks(key_blocks: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, block in enumerate(key_blocks, start=1):
        if isinstance(block, dict):
            normalized.append(
                {
                    "title": str(block.get("title") or f"模块 {idx}").strip(),
                    "items": [str(item).strip() for item in block.get("items", []) if str(item).strip()],
                    "summary": str(block.get("summary", "")).strip(),
                }
            )
        else:
            text = str(block).strip()
            normalized.append({"title": text or f"模块 {idx}", "items": [], "summary": ""})
    return normalized


def infer_layout_family(slide: dict[str, Any], template_name: str) -> str:
    text = " ".join(
        str(slide.get(key, "") or "")
        for key in ("title", "subtitle", "page_goal", "layout_type", "visual_focus", "detail_notes")
    ).lower()
    block_count = len(normalize_blocks(slide.get("key_blocks", [])))

    if any(word in text for word in ["架构", "蓝图", "底座", "层", "平台", "architecture", "blueprint"]):
        return "architecture_layers"
    if any(word in text for word in ["路线", "里程碑", "阶段", "实施", "roadmap", "milestone", "计划"]):
        return "roadmap"
    if block_count >= 4:
        return "four_card_grid"
    if block_count == 3:
        return "three_card_grid"
    if block_count == 2:
        return "two_column"
    if any(word in text for word in ["总结", "收益", "价值", "结论", "建议", "summary", "value"]):
        return "summary"
    if "会议" in template_name or "内部" in template_name:
        return "two_column"
    return "focus_with_sidebar"


def build_slide_specs(job: dict[str, Any], master_style: dict[str, Any], slide_prompts: dict[str, Any]) -> dict[str, Any]:
    slides = []
    template_name = job.get("template_name") or job.get("style") or ""
    for slide in slide_prompts.get("slides", []):
        blocks = normalize_blocks(slide.get("key_blocks", []))
        slides.append(
            {
                "page_no": slide.get("page_no"),
                "title": slide.get("title", ""),
                "subtitle": slide.get("subtitle", ""),
                "page_goal": slide.get("page_goal", ""),
                "visual_focus": slide.get("visual_focus", ""),
                "detail_notes": slide.get("detail_notes", ""),
                "layout_family": infer_layout_family(slide, template_name),
                "blocks": blocks,
                "compiled_prompt": slide.get("compiled_prompt", ""),
            }
        )
    return {"slides": slides}


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def js_array(items: list[str]) -> str:
    return json.dumps(items, ensure_ascii=False)


def safe_filename(name: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")
    return normalized or "presentation"


def ensure_node_workspace(slides_dir: Path) -> None:
    slides_dir.mkdir(parents=True, exist_ok=True)
    package_json = slides_dir / "package.json"
    if not package_json.exists():
        package_json.write_text(
            json.dumps(
                {
                    "name": "ppt-maker-direct-pptx",
                    "private": True,
                    "type": "commonjs",
                    "dependencies": {
                        "pptxgenjs": "^3.12.0",
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    node_modules = slides_dir / "node_modules" / "pptxgenjs"
    if not node_modules.exists():
        subprocess.run(
            ["npm", "install", "--no-audit", "--no-fund"],
            cwd=slides_dir,
            check=True,
            capture_output=True,
            text=True,
        )


def render_block_items(block: dict[str, Any]) -> list[str]:
    items = [str(item).strip() for item in block.get("items", []) if str(item).strip()]
    if items:
        return items[:4]
    return split_summary(block.get("summary", "") or block.get("title", ""), 28)


def slide_module_js(spec: dict[str, Any], theme: Theme) -> str:
    blocks = spec.get("blocks", [])
    blocks_json = json.dumps(
        [
            {
                "title": block.get("title", ""),
                "items": render_block_items(block),
                "summary": block.get("summary", ""),
            }
            for block in blocks
        ],
        ensure_ascii=False,
        indent=2,
    )
    return f"""const slideConfig = {json.dumps(spec, ensure_ascii=False, indent=2)};

function addText(slide, theme, text, opts = {{}}) {{
  return slide.addText(text, {{
    fontFace: opts.fontFace || theme.bodyFont,
    fontSize: opts.fontSize || 12,
    color: opts.color || theme.text,
    bold: !!opts.bold,
    x: opts.x, y: opts.y, w: opts.w, h: opts.h,
    align: opts.align || "left",
    valign: opts.valign || "top",
    margin: 0,
    breakLine: false,
  }});
}}

function addBulletText(slide, theme, items, opts = {{}}) {{
  const runs = [];
  items.forEach((item, idx) => {{
    runs.push({{
      text: item,
      options: {{
        bullet: {{ indent: 12 }},
        breakLine: idx < items.length - 1,
      }},
    }});
  }});
  slide.addText(runs, {{
    fontFace: theme.bodyFont,
    fontSize: opts.fontSize || 11.5,
    color: theme.text,
    x: opts.x, y: opts.y, w: opts.w, h: opts.h,
    margin: 0.02,
    breakLine: true,
  }});
}}

function addCard(pres, slide, theme, x, y, w, h, title, items, accent, summary = "") {{
  slide.addShape(pres.ShapeType.roundRect, {{
    x, y, w, h,
    rectRadius: 0.08,
    fill: {{ color: theme.surface }},
    line: {{ color: theme.divider, pt: 1 }},
  }});
  slide.addShape(pres.ShapeType.roundRect, {{
    x, y, w, h: 0.08,
    rectRadius: 0.03,
    fill: {{ color: accent }},
    line: {{ color: accent, transparency: 100 }},
  }});
  addText(slide, theme, title, {{
    x: x + 0.12, y: y + 0.14, w: w - 0.24, h: 0.24,
    fontSize: 14, color: accent, bold: true
  }});
  const lines = items && items.length ? items : (summary ? [summary] : []);
  addBulletText(slide, theme, lines.slice(0, 4), {{
    x: x + 0.12, y: y + 0.46, w: w - 0.24, h: h - 0.6, fontSize: 11.5
  }});
}}

function createSlide(pres, theme) {{
  const slide = pres.addSlide();
  slide.background = {{ color: theme.bg }};

  slide.addShape(pres.ShapeType.parallelogram, {{ x: 0.45, y: 0.28, w: 0.62, h: 0.24, fill: {{ color: theme.primary }}, line: {{ color: theme.primary, transparency: 100 }} }});
  slide.addShape(pres.ShapeType.parallelogram, {{ x: 0.98, y: 0.28, w: 0.40, h: 0.24, fill: {{ color: theme.accent }}, line: {{ color: theme.accent, transparency: 100 }} }});
  slide.addText(slideConfig.title, {{
    x: 0.72, y: 0.34, w: 8.5, h: 0.36,
    fontFace: theme.titleFont,
    fontSize: 24,
    color: theme.text,
    bold: true,
    margin: 0,
  }});
  if (slideConfig.subtitle) {{
    slide.addText(slideConfig.subtitle, {{
      x: 0.74, y: 0.76, w: 8.8, h: 0.22,
      fontFace: theme.bodyFont,
      fontSize: 12,
      color: theme.textMuted,
      margin: 0,
    }});
  }}

  slide.addShape(pres.ShapeType.roundRect, {{
    x: 10.65, y: 0.40, w: 1.9, h: 0.34,
    rectRadius: 0.08,
    fill: {{ color: theme.surface }},
    line: {{ color: theme.primary, pt: 1.1 }},
  }});
  slide.addText(slideConfig.layout_family, {{
    x: 10.78, y: 0.47, w: 1.6, h: 0.18,
    fontFace: theme.bodyFont,
    fontSize: 10,
    color: theme.primary,
    bold: true,
    align: "center",
    margin: 0,
  }});

  const blocks = {blocks_json};
  const family = slideConfig.layout_family || "focus_with_sidebar";

  if (family === "architecture_layers") {{
    slide.addShape(pres.ShapeType.roundRect, {{ x: 0.56, y: 1.32, w: 12.18, h: 5.76, rectRadius: 0.08, fill: {{ color: "FBFCFD" }}, line: {{ color: theme.divider, pt: 1 }} }});
    const labelX = 0.76;
    const rowX = 2.05;
    const rowW = 10.25;
    const rowH = 0.78;
    const baseY = 1.55;
    blocks.slice(0, 5).forEach((block, idx) => {{
      const y = baseY + idx * 0.92;
      slide.addShape(pres.ShapeType.roundRect, {{ x: labelX, y, w: 1.18, h: 0.56, rectRadius: 0.06, fill: {{ color: theme.primary }}, line: {{ color: theme.primary, transparency: 100 }} }});
      slide.addText(block.title, {{ x: labelX + 0.12, y: y + 0.12, w: 0.94, h: 0.16, fontFace: theme.bodyFont, fontSize: 11, color: "FFFFFF", bold: true, margin: 0 }});
      slide.addShape(pres.ShapeType.roundRect, {{ x: rowX, y: y - 0.05, w: rowW, h: rowH, rectRadius: 0.08, fill: {{ color: theme.surface }}, line: {{ color: theme.divider, pt: 0.8 }} }});
      let cursorX = rowX + 0.16;
      const widths = [1.8, 1.55, 1.55, 1.75, 1.95];
      const items = block.items && block.items.length ? block.items : [block.summary || block.title];
      items.slice(0, 5).forEach((item, j) => {{
        const width = widths[j] || 1.6;
        const accent = j === items.length - 1 ? theme.accent : theme.primary;
        addCard(pres, slide, theme, cursorX, y + 0.06, width, 0.56, item, [], accent, "");
        cursorX += width + 0.12;
      }});
      if (idx < blocks.length - 1) {{
        slide.addShape(pres.ShapeType.line, {{ x: 6.2, y: y + 0.73, w: 0, h: 0.15, line: {{ color: theme.primary, pt: 1.2 }} }});
      }}
    }});
  }} else if (family === "roadmap") {{
    const gap = 0.22;
    const cardW = 2.75;
    const cardH = 2.3;
    blocks.slice(0, 4).forEach((block, idx) => {{
      const x = 0.92 + idx * (cardW + gap);
      const accent = idx === blocks.length - 1 ? theme.accent : theme.primary;
      addCard(pres, slide, theme, x, 2.6, cardW, cardH, block.title, block.items, accent, block.summary);
    }});
  }} else if (family === "two_column") {{
    const left = blocks[0] || {{ title: "模块一", items: [], summary: "" }};
    const right = blocks[1] || {{ title: "模块二", items: [], summary: "" }};
    addCard(pres, slide, theme, 0.72, 1.62, 5.72, 4.75, left.title, left.items, theme.primary, left.summary);
    addCard(pres, slide, theme, 6.86, 1.62, 5.72, 4.75, right.title, right.items, theme.accent, right.summary);
  }} else if (family === "four_card_grid" || family === "three_card_grid") {{
    const columns = family === "three_card_grid" ? 3 : 2;
    const gap = 0.18;
    const x0 = 0.72;
    const y0 = 1.72;
    const totalW = 11.84;
    const cardW = (totalW - gap * (columns - 1)) / columns;
    const rows = blocks.length > columns ? 2 : 1;
    const cardH = rows === 2 ? 2.05 : 3.9;
    blocks.forEach((block, idx) => {{
      const row = Math.floor(idx / columns);
      const col = idx % columns;
      const accent = idx % 2 ? theme.accent : theme.primary;
      addCard(pres, slide, theme, x0 + col * (cardW + gap), y0 + row * (cardH + 0.24), cardW, cardH, block.title, block.items, accent, block.summary);
    }});
  }} else if (family === "summary") {{
    slide.addShape(pres.ShapeType.roundRect, {{ x: 0.72, y: 1.62, w: 11.84, h: 0.74, rectRadius: 0.08, fill: {{ color: theme.primary }}, line: {{ color: theme.primary, transparency: 100 }} }});
    slide.addText(slideConfig.page_goal || slideConfig.visual_focus || "总结本页核心结论与收益。", {{
      x: 0.96, y: 1.82, w: 11.2, h: 0.22, fontFace: theme.titleFont, fontSize: 16, color: "FFFFFF", bold: true, align: "center", margin: 0
    }});
    const columns = 3;
    const gap = 0.18;
    const x0 = 0.72;
    const y0 = 2.62;
    const totalW = 11.84;
    const cardW = (totalW - gap * (columns - 1)) / columns;
    blocks.slice(0, 3).forEach((block, idx) => addCard(pres, slide, theme, x0 + idx * (cardW + gap), y0, cardW, 2.8, block.title, block.items, idx % 2 ? theme.accent : theme.primary, block.summary));
  }} else {{
    const main = blocks[0] || {{ title: slideConfig.title, items: [], summary: "" }};
    addCard(pres, slide, theme, 0.72, 1.62, 8.22, 4.9, main.title, main.items, theme.primary, main.summary || slideConfig.page_goal || "");
    slide.addShape(pres.ShapeType.roundRect, {{ x: 9.18, y: 1.62, w: 3.38, h: 4.9, rectRadius: 0.08, fill: {{ color: theme.surface }}, line: {{ color: theme.divider, pt: 1 }} }});
    slide.addText(slideConfig.visual_focus || "视觉焦点", {{ x: 9.36, y: 1.78, w: 3.0, h: 0.22, fontFace: theme.bodyFont, fontSize: 13, color: theme.accent, bold: true, margin: 0 }});
    addBulletText(slide, theme, [slideConfig.detail_notes || slideConfig.page_goal || "突出关键结构与价值主张。"], {{ x: 9.36, y: 2.12, w: 2.92, h: 3.7, fontSize: 11 }});
  }}

  slide.addText(String(slideConfig.page_no || ""), {{
    x: 12.1, y: 6.9, w: 0.5, h: 0.2, fontFace: theme.bodyFont, fontSize: 10, color: theme.primary, bold: true, align: "center", margin: 0
  }});
  return slide;
}}

module.exports = {{
  createSlide,
  slideConfig,
}};
"""


def compile_script_js(slide_specs: dict[str, Any], theme: Theme, output_path: Path) -> str:
    count = len(slide_specs.get("slides", []))
    theme_json = json.dumps(
        {
            "primary": theme.primary,
            "secondary": theme.neutral,
            "accent": theme.accent,
            "light": theme.surface,
            "bg": theme.background,
            "text": theme.text,
            "textMuted": theme.text_muted,
            "divider": theme.divider,
            "titleFont": theme.title_font,
            "bodyFont": theme.body_font,
        },
        ensure_ascii=False,
        indent=2,
    )
    return f"""const PptxGenJS = require('pptxgenjs');

async function main() {{
  const pres = new PptxGenJS();
  pres.layout = 'LAYOUT_WIDE';
  pres.author = 'OpenAI Codex';
  pres.company = 'OpenAI';
  pres.subject = 'ppt-maker-direct-pptx generated deck';
  pres.title = 'ppt-maker-direct-pptx generated deck';
  pres.theme = {{
    headFontFace: 'Microsoft YaHei',
    bodyFontFace: 'Microsoft YaHei',
    lang: 'zh-CN',
  }};

  const theme = {theme_json};

  for (let i = 1; i <= {count}; i++) {{
    const num = String(i).padStart(2, '0');
    const slideModule = require(`./slide-${{num}}.js`);
    slideModule.createSlide(pres, theme);
  }}

  await pres.writeFile({{ fileName: {js_string(str(output_path))} }});
}}

main().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""


def write_slide_modules(slides_dir: Path, slide_specs: dict[str, Any], theme: Theme) -> None:
    for index, spec in enumerate(slide_specs.get("slides", []), start=1):
        filename = slides_dir / f"slide-{index:02d}.js"
        filename.write_text(slide_module_js(spec, theme), encoding="utf-8")


def render_ppt_from_specs(slide_specs: dict[str, Any], master_style: dict[str, Any], output_path: Path) -> Path:
    theme = to_theme(master_style)
    slides_dir = output_path.parent / "slides"
    ensure_node_workspace(slides_dir)
    write_slide_modules(slides_dir, slide_specs, theme)
    compile_path = slides_dir / "compile.js"
    compile_path.write_text(compile_script_js(slide_specs, theme, output_path), encoding="utf-8")
    subprocess.run(["node", str(compile_path)], cwd=slides_dir, check=True, capture_output=True, text=True)
    return output_path
