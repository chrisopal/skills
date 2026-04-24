#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


JsGenerator = Callable[[str], str]

FORBIDDEN_SCRIPT_TOKENS = [
    "layout_family",
    "layout_type",
    "page_goal",
    "visual_focus",
    "detail_notes",
    "template_name",
    "template_id",
]

SLIDE_W = 13.333
SLIDE_H = 7.5


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
            if text:
                normalized.append({"title": text, "items": [], "summary": ""})
    return normalized


def normalize_placeholders(placeholders: list[Any], page_no: int) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(placeholders or [], start=1):
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("prompt") or item.get("purpose") or "").strip()
        if not prompt:
            continue
        normalized.append(
            {
                "id": str(item.get("id") or f"p{page_no}_img{idx}").strip(),
                "role": str(item.get("role") or "supporting_visual").strip(),
                "purpose": str(item.get("purpose") or prompt).strip(),
                "prompt": prompt,
                "placement": item.get("placement") if isinstance(item.get("placement"), dict) else {},
                "required": bool(item.get("required", False)),
            }
        )
    return normalized


def normalize_image_assets(image_assets: list[Any]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in image_assets or []:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path") or item.get("asset_path") or "").strip()
        placeholder_id = str(item.get("placeholder_id") or item.get("id") or "").strip()
        if not path and not placeholder_id:
            continue
        placement = item.get("placement") if isinstance(item.get("placement"), dict) else {}
        normalized.append(
            {
                "placeholder_id": placeholder_id,
                "path": path,
                "caption": str(item.get("caption") or item.get("purpose") or "").strip(),
                "placement": placement,
            }
        )
    return normalized


def clamp_float(value: Any, fallback: float, min_value: float, max_value: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = fallback
    return max(min_value, min(max_value, number))


def sanitize_region(region: dict[str, Any]) -> dict[str, float]:
    return {
        "x": clamp_float(region.get("x"), 0.72, 0.2, SLIDE_W - 1.0),
        "y": clamp_float(region.get("y"), 1.55, 0.8, SLIDE_H - 1.0),
        "w": clamp_float(region.get("w"), 11.86, 1.0, SLIDE_W - 1.0),
        "h": clamp_float(region.get("h"), 5.25, 1.0, SLIDE_H - 1.0),
    }


def derive_layout_regions(image_placeholders: list[dict[str, Any]]) -> dict[str, Any]:
    base = {"x": 0.72, "y": 1.55, "w": 11.86, "h": 5.25}
    images: list[dict[str, float]] = []
    if not image_placeholders:
        return {"content": base, "images": images, "mode": "full"}

    primary = image_placeholders[0]
    placement = primary.get("placement") if isinstance(primary.get("placement"), dict) else {}
    raw_x = placement.get("x")
    default_side = "right"
    x = clamp_float(raw_x, 8.45, 0.72, 10.2)
    y = clamp_float(placement.get("y"), 1.7, 1.45, 4.6)
    w = clamp_float(placement.get("w"), 3.35, 2.0, 4.2)
    h = clamp_float(placement.get("h"), 2.35, 1.4, 3.2)
    if x < 6.0:
        default_side = "left"
    if default_side == "right":
        x = max(x, 8.15)
        w = min(w, 12.35 - x)
        content = {"x": 0.72, "y": 1.55, "w": max(5.8, x - 1.05), "h": 5.25}
    else:
        x = min(x, 1.05)
        content_x = x + w + 0.65
        content = {"x": content_x, "y": 1.55, "w": max(5.8, 12.58 - content_x), "h": 5.25}
    images.append({"x": x, "y": y, "w": w, "h": h})

    for idx, placeholder in enumerate(image_placeholders[1:3], start=2):
        placement = placeholder.get("placement") if isinstance(placeholder.get("placement"), dict) else {}
        images.append(
            {
                "x": clamp_float(placement.get("x"), 8.15, 0.72, 10.6),
                "y": clamp_float(placement.get("y"), 4.4 + (idx - 2) * 0.9, 1.55, 6.0),
                "w": clamp_float(placement.get("w"), 3.2, 1.8, 4.0),
                "h": clamp_float(placement.get("h"), 1.05, 0.7, 1.6),
            }
        )
    return {"content": sanitize_region(content), "images": images, "mode": f"with_image_{default_side}"}


def template_recipe(template_id: str, template_name: str) -> str:
    key = template_id or template_name
    if "product-solution" in key or "产品" in template_name or "解决方案" in template_name:
        return (
            "产品及解决方案介绍：优先使用能力架构、平台底座、场景模块、客户价值证明。"
            "页面要像售前方案页，结构清晰，模块之间有明确的能力到价值映射。"
        )
    if "market-promo" in key or "市场" in template_name or "宣传" in template_name:
        return (
            "市场宣传：优先使用强标题、价值主张、卖点卡片、关键数字和轻量视觉焦点。"
            "页面更有吸引力，但仍保持企业级克制，不要广告感过重。"
        )
    if "internal-meeting" in key or "内部" in template_name or "会议" in template_name:
        return (
            "内部会议：优先使用进展状态、风险问题、行动项、责任人/时间节奏。"
            "页面像管理例会材料，强调可执行动作和状态判断。"
        )
    return (
        "通用慧新咨询风：优先使用咨询结构、分层架构、对比矩阵、路线图和结论先行模块。"
        "页面要正式、克制、信息密度高但清晰。"
    )


def build_slide_specs(job: dict[str, Any], master_style: dict[str, Any], slide_prompts: dict[str, Any]) -> dict[str, Any]:
    template_id = str(job.get("template_id") or "").strip()
    template_name = str(job.get("template_name") or job.get("style") or "").strip()
    recipe = template_recipe(template_id, template_name)
    slides = []
    for index, slide in enumerate(slide_prompts.get("slides", []), start=1):
        page_no = int(slide.get("page_no") or index)
        blocks = normalize_blocks(slide.get("key_blocks", []))
        image_placeholders = normalize_placeholders(slide.get("image_placeholders", []), page_no)
        image_assets = normalize_image_assets(slide.get("image_assets", []))
        layout_regions = derive_layout_regions(image_placeholders)
        slides.append(
            {
                "page_no": page_no,
                "title": str(slide.get("title", "")).strip(),
                "subtitle": str(slide.get("subtitle", "")).strip(),
                "layout_type": str(slide.get("layout_type", "content")).strip() or "content",
                "blocks": blocks,
                "visible_content": {
                    "title": str(slide.get("title", "")).strip(),
                    "subtitle": str(slide.get("subtitle", "")).strip(),
                    "blocks": blocks,
                    "image_placeholders": image_placeholders,
                    "image_assets": image_assets,
                },
                "image_placeholders": image_placeholders,
                "image_assets": image_assets,
                "layout_regions": layout_regions,
                "invisible_guidance": {
                    "page_goal": str(slide.get("page_goal", "")).strip(),
                    "visual_focus": str(slide.get("visual_focus", "")).strip(),
                    "detail_notes": str(slide.get("detail_notes", "")).strip(),
                    "compiled_prompt": str(slide.get("compiled_prompt", "")).strip(),
                },
                "template_variant": {
                    "id": template_id,
                    "name": template_name,
                    "rendering_recipe": recipe,
                },
                "script_path": f"slides/slide-{page_no:02d}.js",
            }
        )
    return {"slides": slides}


def js_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


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


def theme_to_js(theme: Theme) -> str:
    return json.dumps(
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


def module_filename(page_no: int) -> str:
    return f"slide-{page_no:02d}.js"


def compact_master_style(master_style: dict[str, Any]) -> dict[str, Any]:
    return {
        "visual_positioning": master_style.get("visual_positioning", ""),
        "deck_voice": master_style.get("deck_voice", ""),
        "color_strategy": master_style.get("color_strategy", {}),
        "typography": master_style.get("typography", {}),
        "title_hierarchy_rules": master_style.get("title_hierarchy_rules", []),
        "layout_system": master_style.get("layout_system", {}),
        "module_layout_patterns": master_style.get("module_layout_patterns", []),
        "chart_rules": master_style.get("chart_rules", []),
        "icon_rules": master_style.get("icon_rules", []),
        "forbidden_elements": master_style.get("forbidden_elements", []),
        "prompt_block": master_style.get("prompt_block", ""),
    }


def build_page_js_prompt(spec: dict[str, Any], master_style: dict[str, Any], theme: Theme, total_slides: int) -> str:
    visible = spec.get("visible_content", {})
    guidance = spec.get("invisible_guidance", {})
    template_variant = spec.get("template_variant", {})
    layout_regions = spec.get("layout_regions", {"content": {"x": 0.72, "y": 1.55, "w": 11.86, "h": 5.25}, "images": []})
    return f"""You are generating one complete PptxGenJS slide module.

Return ONLY JavaScript code. No Markdown fences. No explanations.

Output file contract:
- CommonJS module.
- Export a synchronous function: module.exports = {{ createSlide, slideConfig }};
- createSlide(pres, theme) must add exactly one slide and return it.
- Use only the provided pres object and PptxGenJS native methods: slide.addText, slide.addShape, slide.addChart, slide.addImage, simple lines/connectors.
- Do not use remote assets, async code, fs, child_process, eval, imports, or require().
- Use shape type strings such as 'rect', 'roundRect', 'line', 'ellipse', and 'parallelogram'. Never use PptxGenJS.ShapeType, pptxgen.ShapeType, or pres.ShapeType.
- The slide is 16:9 LAYOUT_WIDE, 13.333 x 7.5 inches.
- Use theme keys only: primary, secondary, accent, light, bg, text, textMuted, divider, titleFont, bodyFont.
- If layout_regions.images is not empty, slideConfig must include contentRegion and images derived from layout_regions.

Visible content to render:
{json.dumps(visible, ensure_ascii=False, indent=2)}

Layout regions. Treat these as hard non-overlap zones:
{json.dumps(layout_regions, ensure_ascii=False, indent=2)}

Invisible design guidance. Use this to design, but do NOT render these field names or raw values:
{json.dumps(guidance, ensure_ascii=False, indent=2)}

Deck-level master style:
{json.dumps(compact_master_style(master_style), ensure_ascii=False, indent=2)}

Template rendering recipe:
{template_variant.get("rendering_recipe", "")}

Theme values:
{theme_to_js(theme)}

Slide context:
- page_no: {spec.get("page_no")}
- total_slides: {total_slides}
- layout_type hint: {spec.get("layout_type")}

Hard rules:
- Do not visibly render these internal tokens: {", ".join(FORBIDDEN_SCRIPT_TOKENS)}.
- Do not add page numbers, template names, chapter tags, 16:9 labels, watermarks, or corner microcopy.
- Build a real page-specific layout from the visible content. Avoid repeated generic three-card layouts unless the content truly asks for it.
- Do not import or require pptxgenjs inside the slide module; compile.js provides the pres object.
- Keep Chinese text readable. Use Microsoft YaHei through theme.titleFont/theme.bodyFont.
- Prefer a clear title area, 2-4 strong modules, and a purposeful visual structure.
- Keep all text inside its shapes and use font sizes that fit.
- Inside every card, reserve separate title and body zones; body text must start below the title zone.
- Do not place full bullet lists inside tiny chips or cards below 1.0 inch high.
- Use colors consistently: blue/teal for structure, green for value/emphasis, gray for secondary/support.
- If visible_content.image_assets contains local paths, embed them with slide.addImage at the matching placeholder placement.
- If image_placeholders exist without assets, draw a clean editable placeholder frame in that location.
- Main content must stay inside layout_regions.content. Do not draw cards, text, charts, or connectors outside that region except title/subtitle.
- Image assets/placeholders must stay inside layout_regions.images. They are reserved visual zones, not decorative overlays.
- Never place image assets/placeholders on top of text, cards, KPI strips, architecture rows, timelines, or module titles.
"""


def build_repair_prompt(spec: dict[str, Any], master_style: dict[str, Any], theme: Theme, previous_js: str, error: str) -> str:
    return f"""Repair this PptxGenJS slide module.

Return ONLY corrected JavaScript code. No Markdown fences. No explanations.

Validation error:
{error}

Original slide spec:
{json.dumps(spec, ensure_ascii=False, indent=2)}

Master style:
{json.dumps(compact_master_style(master_style), ensure_ascii=False, indent=2)}

Theme:
{theme_to_js(theme)}

Previous JavaScript:
```javascript
{previous_js}
```

Keep the required contract:
- module.exports = {{ createSlide, slideConfig }};
- createSlide(pres, theme) is synchronous.
- Use only PptxGenJS native objects.
- Do not include forbidden internal strings: {", ".join(FORBIDDEN_SCRIPT_TOKENS)}.
"""


def extract_js_code(raw: str) -> str:
    text = raw.strip()
    fenced = re.search(r"```(?:javascript|js)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        return fenced.group(1).strip()
    return text


def script_requires_image_regions(spec: dict[str, Any] | None) -> bool:
    if not spec:
        return False
    visible = spec.get("visible_content", {}) if isinstance(spec.get("visible_content"), dict) else {}
    placeholders = spec.get("image_placeholders") or visible.get("image_placeholders") or []
    assets = spec.get("image_assets") or visible.get("image_assets") or []
    layout_regions = spec.get("layout_regions") if isinstance(spec.get("layout_regions"), dict) else {}
    return bool(placeholders or assets or layout_regions.get("images"))


def validation_error_for_script(script_text: str, spec: dict[str, Any] | None = None) -> str | None:
    lowered = script_text.lower()
    for token in FORBIDDEN_SCRIPT_TOKENS:
        if token.lower() in lowered:
            return f"Generated script contains forbidden internal token: {token}"
    if "module.exports" not in script_text or "createSlide" not in script_text:
        return "Generated script must export createSlide via module.exports"
    if re.search(r"\brequire\s*\(", script_text) or re.search(r"^\s*import\s+", script_text, flags=re.MULTILINE):
        return "Generated slide module must not import or require dependencies; compile.js provides the pres object"
    if any(forbidden in lowered for forbidden in ["child_process", "eval("]):
        return "Generated script uses forbidden runtime APIs"
    if re.search(r"(ShapeType|shapeType)", script_text):
        return "Use PptxGenJS shape type strings like 'rect' and 'roundRect'; do not use ShapeType constants"
    if script_requires_image_regions(spec):
        if "contentRegion" not in script_text:
            return "Image-aware slides must define slideConfig.contentRegion and keep text/cards inside it"
        if not re.search(r"\bimages\s*:", script_text):
            return "Image-aware slides must define slideConfig.images from layout_regions.images"
    return None


def validate_slide_module(slides_dir: Path, filename: str, spec: dict[str, Any] | None = None) -> None:
    script_path = slides_dir / filename
    script_text = script_path.read_text(encoding="utf-8")
    local_error = validation_error_for_script(script_text, spec)
    if local_error:
        raise ValueError(local_error)
    probe = f"""
const mod = require('./{filename}');
if (!mod || typeof mod.createSlide !== 'function') {{
  throw new Error('createSlide export missing');
}}
if (mod.createSlide.constructor.name === 'AsyncFunction') {{
  throw new Error('createSlide must be synchronous');
}}
const PptxGenJS = require('pptxgenjs');
const pres = new PptxGenJS();
pres.layout = 'LAYOUT_WIDE';
const theme = {{
  primary: '0F95B6',
  secondary: 'D9D9D9',
  accent: 'A8D86B',
  light: 'F5F7FA',
  bg: 'FFFFFF',
  text: '1E1E1E',
  textMuted: '6B7280',
  divider: 'E5E7EB',
  titleFont: 'Microsoft YaHei',
  bodyFont: 'Microsoft YaHei',
}};
mod.createSlide(pres, theme);
"""
    subprocess.run(["node", "-e", probe], cwd=slides_dir, check=True, capture_output=True, text=True)


def compile_script_js(slide_specs: dict[str, Any], theme: Theme, output_path: Path) -> str:
    files = [f"./{module_filename(int(spec.get('page_no') or index))}" for index, spec in enumerate(slide_specs.get("slides", []), start=1)]
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

  const theme = {theme_to_js(theme)};
  const slideFiles = {json.dumps(files, ensure_ascii=False, indent=2)};

  for (const file of slideFiles) {{
    const slideModule = require(file);
    slideModule.createSlide(pres, theme);
  }}

  await pres.writeFile({{ fileName: {js_string(str(output_path))} }});
}}

main().catch((err) => {{
  console.error(err);
  process.exit(1);
}});
"""


def sanitize_text(text: str, limit: int = 60) -> str:
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def deterministic_slide_js(spec: dict[str, Any], theme: Theme, total_slides: int) -> str:
    visible = spec.get("visible_content", {})
    blocks = visible.get("blocks", []) or []
    page_no = int(spec.get("page_no") or 1)
    template_name = spec.get("template_variant", {}).get("name", "")
    title = sanitize_text(visible.get("title") or spec.get("title") or f"第{page_no}页", 52)
    subtitle = sanitize_text(visible.get("subtitle") or "", 72)
    clean_blocks = []
    for idx, block in enumerate(blocks[:6], start=1):
        items = [sanitize_text(item, 30) for item in block.get("items", [])[:4]]
        summary = sanitize_text(block.get("summary", ""), 42)
        clean_blocks.append({"title": sanitize_text(block.get("title") or f"模块{idx}", 20), "items": items, "summary": summary})
    if not clean_blocks:
        clean_blocks = [{"title": "核心观点", "items": ["结构化展开", "价值导向", "可执行落地"], "summary": ""}]
    image_placeholders = spec.get("image_placeholders", []) or visible.get("image_placeholders", []) or []
    image_assets = spec.get("image_assets", []) or visible.get("image_assets", []) or []
    layout_regions = spec.get("layout_regions") or derive_layout_regions(image_placeholders)
    content_region = sanitize_region(layout_regions.get("content", {}))
    image_regions = layout_regions.get("images", []) if isinstance(layout_regions.get("images"), list) else []
    images = []
    for idx, placeholder in enumerate(image_placeholders[:3], start=1):
        placement = placeholder.get("placement") if isinstance(placeholder.get("placement"), dict) else {}
        region = image_regions[idx - 1] if idx - 1 < len(image_regions) and isinstance(image_regions[idx - 1], dict) else placement
        asset = next(
            (
                item
                for item in image_assets
                if item.get("placeholder_id") == placeholder.get("id") or item.get("id") == placeholder.get("id")
            ),
            {},
        )
        images.append(
            {
                "id": sanitize_text(placeholder.get("id") or f"image{idx}", 22),
                "title": sanitize_text(placeholder.get("purpose") or placeholder.get("role") or "视觉占位", 24),
                "path": str(asset.get("path") or ""),
                "caption": sanitize_text(asset.get("caption") or placeholder.get("purpose") or "", 32),
                "x": clamp_float(region.get("x"), 8.4, 0.72, 11.0),
                "y": clamp_float(region.get("y"), 1.8, 1.45, 6.2),
                "w": clamp_float(region.get("w"), 3.35, 1.2, 4.4),
                "h": clamp_float(region.get("h"), 2.35, 0.7, 3.4),
            }
        )

    text_blob = " ".join([title, subtitle, " ".join(block["title"] for block in clean_blocks), str(spec.get("layout_type", ""))])
    if any(word in text_blob for word in ["架构", "蓝图", "平台", "分层", "底座"]):
        layout = "blueprint"
    elif any(word in text_blob for word in ["路线", "阶段", "里程碑", "计划"]):
        layout = "roadmap"
    elif "市场" in template_name or "宣传" in template_name:
        layout = "promo"
    elif "内部" in template_name or "会议" in template_name:
        layout = "meeting"
    elif len(clean_blocks) >= 4:
        layout = "grid"
    elif page_no % 2 == 0 and len(clean_blocks) <= 3:
        layout = "split"
    else:
        layout = "grid"

    return f"""const slideConfig = {{
  pageNo: {page_no},
  totalSlides: {total_slides},
  title: {js_string(title)},
  subtitle: {js_string(subtitle)},
  layout: {js_string(layout)},
  contentRegion: {json.dumps(content_region, ensure_ascii=False, indent=2)},
  blocks: {json.dumps(clean_blocks, ensure_ascii=False, indent=2)},
  images: {json.dumps(images, ensure_ascii=False, indent=2)}
}};

function addText(slide, text, opts) {{
  slide.addText(text, Object.assign({{
    fontFace: opts.fontFace || opts.theme.bodyFont,
    margin: 0.04,
    fit: 'shrink',
    breakLine: false,
    valign: 'top',
    color: opts.theme.text,
  }}, opts));
}}

function addTitle(slide, theme) {{
  slide.addShape('parallelogram', {{ x: 0.42, y: 0.31, w: 0.52, h: 0.22, fill: {{ color: theme.primary }}, line: {{ color: theme.primary, transparency: 100 }} }});
  slide.addShape('parallelogram', {{ x: 0.86, y: 0.31, w: 0.34, h: 0.22, fill: {{ color: theme.accent }}, line: {{ color: theme.accent, transparency: 100 }} }});
  addText(slide, slideConfig.title, {{ theme, x: 0.62, y: 0.58, w: 10.8, h: 0.42, fontFace: theme.titleFont, fontSize: 24, bold: true, color: theme.text }});
  if (slideConfig.subtitle) {{
    addText(slide, slideConfig.subtitle, {{ theme, x: 0.64, y: 1.11, w: 10.5, h: 0.24, fontSize: 11.5, color: theme.textMuted }});
  }}
  slide.addShape('line', {{ x: 0.62, y: 1.43, w: 11.9, h: 0, line: {{ color: theme.divider, pt: 1 }} }});
}}

function addImageAssets(slide, theme) {{
  (slideConfig.images || []).forEach((image) => {{
    slide.addShape('roundRect', {{ x: image.x, y: image.y, w: image.w, h: image.h, rectRadius: 0.08, fill: {{ color: 'FFFFFF' }}, line: {{ color: theme.divider, pt: 1 }} }});
    if (image.path) {{
      slide.addImage({{ path: image.path, x: image.x + 0.04, y: image.y + 0.04, w: Math.max(0.1, image.w - 0.08), h: Math.max(0.1, image.h - 0.08) }});
    }} else {{
      slide.addShape('rect', {{ x: image.x + 0.14, y: image.y + 0.18, w: Math.max(0.1, image.w - 0.28), h: Math.max(0.1, image.h - 0.36), fill: {{ color: theme.light }}, line: {{ color: theme.divider, dash: 'dash' }} }});
      addText(slide, image.title || '图片占位', {{ theme, x: image.x + 0.22, y: image.y + image.h / 2 - 0.1, w: Math.max(0.1, image.w - 0.44), h: 0.2, fontSize: 10.5, color: theme.textMuted, align: 'center' }});
    }}
  }});
}}

function estimateLines(text, width, fontSize) {{
  const chars = String(text || '').replace(/\\s+/g, '').length;
  const charsPerLine = Math.max(4, Math.floor(width * 72 / Math.max(8, fontSize) / 1.25));
  return Math.max(1, Math.ceil(chars / charsPerLine));
}}

function cardTextMetrics(w, h, block) {{
  const compact = h < 1.25;
  const titleSize = compact ? 10.8 : (w < 2.3 ? 11.6 : 12.8);
  const bodySize = compact ? 8.6 : (w < 2.3 ? 9.2 : 9.8);
  const titleLines = Math.min(2, estimateLines(block.title, Math.max(0.8, w - 0.36), titleSize));
  const titleH = Math.max(0.24, titleLines * (titleSize / 72 * 1.25));
  const bodyY = 0.18 + titleH + 0.12;
  const bodyH = Math.max(0.18, h - bodyY - 0.18);
  const maxItems = Math.max(1, Math.min(4, Math.floor(bodyH / Math.max(0.18, bodySize / 72 * 1.42))));
  return {{ titleSize, bodySize, titleH, bodyY, bodyH, maxItems }};
}}

function addCard(slide, theme, x, y, w, h, block, accent, mode = 'normal') {{
  slide.addShape('roundRect', {{ x, y, w, h, rectRadius: 0.08, fill: {{ color: mode === 'emphasis' ? accent : theme.light }}, line: {{ color: mode === 'emphasis' ? accent : theme.divider, pt: 1 }} }});
  const metrics = cardTextMetrics(w, h, block);
  addText(slide, block.title, {{ theme, x: x + 0.16, y: y + 0.16, w: w - 0.32, h: metrics.titleH, fontSize: metrics.titleSize, bold: true, color: mode === 'emphasis' ? 'FFFFFF' : accent, fontFace: theme.titleFont, breakLine: true }});
  const lines = block.items && block.items.length ? block.items : (block.summary ? [block.summary] : ['形成结构化能力', '支撑业务闭环']);
  const runs = [];
  const visibleLines = lines.slice(0, metrics.maxItems);
  visibleLines.forEach((item, idx) => runs.push({{ text: item, options: {{ bullet: {{ indent: 10 }}, breakLine: idx < visibleLines.length - 1 }} }}));
  slide.addText(runs, {{ x: x + 0.18, y: y + metrics.bodyY, w: w - 0.36, h: metrics.bodyH, fontFace: theme.bodyFont, fontSize: metrics.bodySize, color: mode === 'emphasis' ? 'FFFFFF' : theme.text, margin: 0.02, fit: 'shrink', breakLine: true }});
}}

function addBlueprint(slide, theme) {{
  const rows = slideConfig.blocks.slice(0, 5);
  const region = slideConfig.contentRegion;
  const baseY = region.y + 0.1;
  const labelW = Math.min(1.45, Math.max(1.05, region.w * 0.16));
  const rowX = region.x + labelW + 0.24;
  const rowW = Math.max(2.2, region.w - labelW - 0.3);
  const rowStep = Math.min(0.92, Math.max(0.7, (region.h - 0.45) / Math.max(1, rows.length)));
  rows.forEach((block, idx) => {{
    const y = baseY + idx * rowStep;
    const accent = idx === rows.length - 1 ? theme.accent : theme.primary;
    slide.addShape('roundRect', {{ x: region.x, y, w: labelW, h: 0.56, rectRadius: 0.08, fill: {{ color: accent }}, line: {{ color: accent, transparency: 100 }} }});
    addText(slide, block.title, {{ theme, x: region.x + 0.1, y: y + 0.16, w: labelW - 0.2, h: 0.18, fontSize: 10.2, bold: true, color: 'FFFFFF', align: 'center' }});
    slide.addShape('roundRect', {{ x: rowX, y: y - 0.06, w: rowW, h: 0.68, rectRadius: 0.08, fill: {{ color: theme.light }}, line: {{ color: theme.divider, pt: 0.8 }} }});
    const items = (block.items && block.items.length ? block.items : [block.summary || '能力模块']).slice(0, 4);
    items.forEach((item, j) => {{
      const itemGap = 0.16;
      const itemW = Math.max(1.0, (rowW - 0.34 - itemGap * (items.length - 1)) / Math.max(1, items.length));
      const x = rowX + 0.17 + j * (itemW + itemGap);
      slide.addShape('roundRect', {{ x, y: y + 0.12, w: itemW, h: 0.32, rectRadius: 0.06, fill: {{ color: j === 0 ? accent : 'FFFFFF' }}, line: {{ color: j === 0 ? accent : theme.divider, pt: 0.6 }} }});
      addText(slide, item, {{ theme, x: x + 0.06, y: y + 0.2, w: itemW - 0.12, h: 0.1, fontSize: 8.4, bold: j === 0, color: j === 0 ? 'FFFFFF' : theme.text, align: 'center' }});
    }});
  }});
}}

function addGrid(slide, theme) {{
  const cols = slideConfig.blocks.length >= 4 ? 2 : 3;
  const gap = 0.18;
  const region = slideConfig.contentRegion;
  const x0 = region.x;
  const y0 = region.y + 0.1;
  const totalW = region.w;
  const cardW = (totalW - gap * (cols - 1)) / cols;
  const rows = Math.ceil(slideConfig.blocks.length / cols);
  const cardH = rows > 1 ? Math.min(2.05, (region.h - 0.4) / rows) : Math.min(3.92, region.h - 0.35);
  slideConfig.blocks.forEach((block, idx) => addCard(slide, theme, x0 + (idx % cols) * (cardW + gap), y0 + Math.floor(idx / cols) * (cardH + 0.25), cardW, cardH, block, idx % 2 ? theme.accent : theme.primary, idx === 0 ? 'emphasis' : 'normal'));
}}

function addSplit(slide, theme) {{
  const left = slideConfig.blocks[0] || {{ title: '关键结构', items: [] }};
  const right = slideConfig.blocks[1] || {{ title: '价值落地', items: [] }};
  const region = slideConfig.contentRegion;
  const gap = 0.22;
  const cardW = (region.w - gap) / 2;
  const hasBottom = !!slideConfig.blocks[2];
  const topH = hasBottom ? Math.max(2.85, region.h - 1.65) : region.h - 0.32;
  addCard(slide, theme, region.x, region.y + 0.12, cardW, topH, left, theme.primary, 'emphasis');
  addCard(slide, theme, region.x + cardW + gap, region.y + 0.12, cardW, topH, right, theme.accent, 'normal');
  if (hasBottom) addCard(slide, theme, region.x, region.y + topH + 0.42, region.w, 1.05, slideConfig.blocks[2], theme.accent, 'normal');
}}

function addRoadmap(slide, theme) {{
  const blocks = slideConfig.blocks.slice(0, 4);
  const region = slideConfig.contentRegion;
  slide.addShape('line', {{ x: region.x + 0.25, y: region.y + region.h * 0.45, w: region.w - 0.5, h: 0, line: {{ color: theme.primary, pt: 2 }} }});
  blocks.forEach((block, idx) => {{
    const stepW = region.w / Math.max(1, blocks.length);
    const x = region.x + idx * stepW + 0.08;
    slide.addShape('ellipse', {{ x: x + stepW * 0.38, y: region.y + region.h * 0.45 - 0.2, w: 0.38, h: 0.38, fill: {{ color: idx === blocks.length - 1 ? theme.accent : theme.primary }}, line: {{ color: 'FFFFFF', pt: 1 }} }});
    addCard(slide, theme, x, region.y + 0.45 + (idx % 2) * 1.72, Math.max(1.7, stepW - 0.22), 1.42, block, idx === blocks.length - 1 ? theme.accent : theme.primary, 'normal');
  }});
}}

function addPromo(slide, theme) {{
  const first = slideConfig.blocks[0] || {{ title: '核心价值', items: [] }};
  const region = slideConfig.contentRegion;
  const heroW = Math.max(3.0, region.w * 0.58);
  slide.addShape('roundRect', {{ x: region.x, y: region.y + 0.12, w: heroW, h: region.h - 0.45, rectRadius: 0.1, fill: {{ color: theme.primary }}, line: {{ color: theme.primary, transparency: 100 }} }});
  addText(slide, first.title, {{ theme, x: region.x + 0.32, y: region.y + 0.48, w: heroW - 0.7, h: 0.5, fontFace: theme.titleFont, fontSize: 24, bold: true, color: 'FFFFFF' }});
  const lines = first.items && first.items.length ? first.items : [first.summary || '构建可复制增长路径'];
  slide.addText(lines.map((item, idx) => ({{ text: item, options: {{ bullet: {{ indent: 14 }}, breakLine: idx < lines.length - 1 }} }})), {{ x: region.x + 0.38, y: region.y + 1.28, w: heroW - 1.0, h: 1.7, fontFace: theme.bodyFont, fontSize: 15, color: 'FFFFFF', margin: 0.03, fit: 'shrink', breakLine: true }});
  const sideX = region.x + heroW + 0.28;
  const sideW = Math.max(1.7, region.x + region.w - sideX);
  slideConfig.blocks.slice(1, 4).forEach((block, idx) => addCard(slide, theme, sideX, region.y + 0.16 + idx * 1.45, sideW, 1.16, block, idx % 2 ? theme.accent : theme.primary, 'normal'));
}}

function addMeeting(slide, theme) {{
  const labels = ['进展', '风险', '行动'];
  const blocks = slideConfig.blocks.slice(0, 3);
  const region = slideConfig.contentRegion;
  const gap = 0.28;
  const cardW = (region.w - gap * 2) / 3;
  blocks.forEach((block, idx) => {{
    const accent = idx === 1 ? theme.neutral : (idx === 2 ? theme.accent : theme.primary);
    const x = region.x + idx * (cardW + gap);
    slide.addShape('roundRect', {{ x, y: region.y + 0.22, w: cardW, h: region.h - 0.62, rectRadius: 0.08, fill: {{ color: theme.light }}, line: {{ color: theme.divider, pt: 1 }} }});
    slide.addShape('roundRect', {{ x: x + 0.24, y: region.y + 0.46, w: 0.82, h: 0.34, rectRadius: 0.08, fill: {{ color: accent }}, line: {{ color: accent, transparency: 100 }} }});
    addText(slide, labels[idx] || '模块', {{ theme, x: x + 0.3, y: region.y + 0.54, w: 0.68, h: 0.1, fontSize: 8.8, color: 'FFFFFF', bold: true, align: 'center' }});
    addText(slide, block.title, {{ theme, x: x + 0.24, y: region.y + 1.0, w: cardW - 0.48, h: 0.44, fontSize: 15.5, bold: true, color: theme.text, fontFace: theme.titleFont }});
    const lines = block.items && block.items.length ? block.items : [block.summary || '明确下一步动作'];
    slide.addText(lines.map((item, j) => ({{ text: item, options: {{ bullet: {{ indent: 12 }}, breakLine: j < lines.length - 1 }} }})), {{ x: x + 0.24, y: region.y + 1.63, w: cardW - 0.52, h: region.h - 2.3, fontFace: theme.bodyFont, fontSize: 11.2, color: theme.text, margin: 0.02, fit: 'shrink', breakLine: true }});
  }});
}}

function createSlide(pres, theme) {{
  const slide = pres.addSlide();
  slide.background = {{ color: theme.bg }};
  addTitle(slide, theme);
  if (slideConfig.layout === 'blueprint') addBlueprint(slide, theme);
  else if (slideConfig.layout === 'roadmap') addRoadmap(slide, theme);
  else if (slideConfig.layout === 'promo') addPromo(slide, theme);
  else if (slideConfig.layout === 'meeting') addMeeting(slide, theme);
  else if (slideConfig.layout === 'split') addSplit(slide, theme);
  else addGrid(slide, theme);
  addImageAssets(slide, theme);
  return slide;
}}

module.exports = {{ createSlide, slideConfig }};
"""


def write_slide_module(
    slides_dir: Path,
    spec: dict[str, Any],
    master_style: dict[str, Any],
    theme: Theme,
    total_slides: int,
    js_generator: JsGenerator | None,
    *,
    max_repair_attempts: int,
) -> None:
    filename = module_filename(int(spec.get("page_no") or 1))
    path = slides_dir / filename

    if js_generator is None:
        path.write_text(deterministic_slide_js(spec, theme, total_slides), encoding="utf-8")
        validate_slide_module(slides_dir, filename, spec)
        return

    prompt = build_page_js_prompt(spec, master_style, theme, total_slides)
    script = extract_js_code(js_generator(prompt))
    last_error = ""
    for attempt in range(max_repair_attempts + 1):
        path.write_text(script, encoding="utf-8")
        try:
            validate_slide_module(slides_dir, filename, spec)
            return
        except Exception as exc:  # noqa: BLE001 - return exact model/code validation error.
            last_error = str(exc)
            if attempt >= max_repair_attempts:
                break
            repair_prompt = build_repair_prompt(spec, master_style, theme, script, last_error)
            script = extract_js_code(js_generator(repair_prompt))
    raise RuntimeError(f"Failed to generate valid {filename}: {last_error}")


def render_ppt_from_specs(
    slide_specs: dict[str, Any],
    master_style: dict[str, Any],
    output_path: Path,
    *,
    js_generator: JsGenerator | None = None,
    only_pages: set[int] | None = None,
    max_repair_attempts: int = 2,
) -> Path:
    theme = to_theme(master_style)
    slides_dir = output_path.parent / "slides"
    ensure_node_workspace(slides_dir)

    slides = slide_specs.get("slides", [])
    total_slides = len(slides)
    for spec in slides:
        page_no = int(spec.get("page_no") or 1)
        filename = module_filename(page_no)
        should_write = only_pages is None or page_no in only_pages or not (slides_dir / filename).exists()
        if should_write:
            write_slide_module(
                slides_dir,
                spec,
                master_style,
                theme,
                total_slides,
                js_generator,
                max_repair_attempts=max_repair_attempts,
            )
        else:
            validate_slide_module(slides_dir, filename, spec)

    compile_path = slides_dir / "compile.js"
    compile_path.write_text(compile_script_js(slide_specs, theme, output_path), encoding="utf-8")
    subprocess.run(["node", str(compile_path)], cwd=slides_dir, check=True, capture_output=True, text=True)
    return output_path
