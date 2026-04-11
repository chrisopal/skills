#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import copy
import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml
from PIL import Image, ImageDraw

from assemble_pptx import assemble_pptx
from validate_job import find_missing_required_fields, has_confirmed_template


TEMPLATE_VARIANT_BUNDLES = {
    "huixin": {
        "aliases": ["慧新"],
        "preset_asset": "huixin_template.json",
        "brief_asset": "huixin_master_style_brief.json",
    },
    "huixin-product-solution": {
        "aliases": ["慧新-产品及解决方案介绍", "慧新产品及解决方案介绍", "产品及解决方案介绍风格"],
        "preset_asset": "huixin_product_solution_template.json",
        "brief_asset": "huixin_product_solution_master_style_brief.json",
    },
    "huixin-market-promo": {
        "aliases": ["慧新-市场宣传", "慧新市场宣传", "市场宣传风格"],
        "preset_asset": "huixin_market_promo_template.json",
        "brief_asset": "huixin_market_promo_master_style_brief.json",
    },
    "huixin-internal-meeting": {
        "aliases": ["慧新-内部会议", "慧新内部会议", "内部会议风格"],
        "preset_asset": "huixin_internal_meeting_template.json",
        "brief_asset": "huixin_internal_meeting_master_style_brief.json",
    },
}


def skill_root() -> Path:
    return Path(__file__).resolve().parents[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run a confirmation-first image PPT job from job.json to pptx."
    )
    parser.add_argument("job", help="Path to the job.json file")
    parser.add_argument(
        "--config",
        default=str(skill_root() / "assets" / "model_config.yaml"),
        help="Path to model config yaml",
    )
    parser.add_argument(
        "--output-dir",
        default="",
        help="Optional output directory override",
    )
    parser.add_argument(
        "--auto-approve-outline",
        action="store_true",
        help="Continue immediately after generating outline",
    )
    parser.add_argument(
        "--auto-approve-prompts",
        action="store_true",
        help="Continue immediately after generating slide prompts",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip live model calls and generate placeholder outputs",
    )
    return parser


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_asset_json(name: str) -> dict[str, Any]:
    return load_json(skill_root() / "assets" / name)


def resolve_template_variant_key(template_id: str | None, template_name: str | None) -> str | None:
    normalized_id = (template_id or "").strip().lower()
    normalized_name = (template_name or "").strip()
    if normalized_id in TEMPLATE_VARIANT_BUNDLES:
        return normalized_id
    for key, bundle in TEMPLATE_VARIANT_BUNDLES.items():
        if normalized_name and normalized_name in bundle["aliases"]:
            return key
    return None


def load_template_variant_bundle(template_id: str | None, template_name: str | None) -> dict[str, Any] | None:
    key = resolve_template_variant_key(template_id, template_name)
    if not key:
        return None
    bundle = TEMPLATE_VARIANT_BUNDLES[key]
    preset = load_asset_json(bundle["preset_asset"])
    brief = load_asset_json(bundle["brief_asset"])
    return {"key": key, "preset": preset, "brief": brief}


def available_template_choices() -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for key, bundle in TEMPLATE_VARIANT_BUNDLES.items():
        preset = load_asset_json(bundle["preset_asset"])
        result.append(
            {
                "template_id": key,
                "template_name": preset.get("template_name", key),
                "style_summary": preset.get("style_summary", ""),
            }
        )
    return result


def resolve_output_dir(job: dict[str, Any], cli_output_dir: str, job_path: Path) -> Path:
    if cli_output_dir:
        return Path(cli_output_dir).expanduser().resolve()
    output_dir = job.get("output", {}).get("directory")
    if output_dir:
        return (job_path.parent / output_dir).resolve()
    return (job_path.parent / "artifacts").resolve()


def build_openrouter_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def call_text_model(
    client: httpx.Client,
    model: str,
    prompt: str,
    *,
    temperature: float = 0.3,
) -> dict[str, Any]:
    if "json" not in prompt.lower():
        prompt = f"{prompt}\n\nReturn valid JSON only."
    response = client.post(
        "/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "response_format": {"type": "json_object"},
        },
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def call_image_model(
    client: httpx.Client,
    model: str,
    prompt: str,
    resolution: str,
) -> bytes:
    response = client.post(
        "/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "modalities": ["image", "text"],
            "temperature": 0.1,
            "image_config": {
                "aspect_ratio": "16:9",
                "image_size": "4K",
            },
        },
    )
    response.raise_for_status()
    message = response.json()["choices"][0]["message"]
    images = message.get("images") or []
    for image in images:
        image_url = image.get("image_url", {}).get("url", "")
        if image_url.startswith("data:"):
            return base64.b64decode(image_url.split(",", 1)[1])
        if image_url.startswith("http"):
            image_response = httpx.get(image_url, timeout=60.0)
            image_response.raise_for_status()
            return image_response.content
    raise ValueError("No image data returned from image model")


def load_prompt_template(name: str) -> str:
    content = (skill_root() / "references" / "prompt-templates.md").read_text(encoding="utf-8")
    anchor = f"## {name}"
    start = content.index(anchor)
    next_idx = content.find("\n## ", start + 1)
    block = content[start : next_idx if next_idx != -1 else len(content)]
    first = block.find("```text")
    last = block.rfind("```")
    if first == -1 or last == -1 or last <= first:
        raise ValueError(f"Prompt template not found: {name}")
    return block[first + len("```text") : last].strip()


def openrouter_client(config: dict[str, Any]) -> httpx.Client | None:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        return None
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    return httpx.Client(
        base_url=base_url,
        headers=build_openrouter_headers(api_key),
        timeout=httpx.Timeout(180.0, connect=20.0),
    )


def normalize_selected_template(job: dict[str, Any]) -> dict[str, Any] | None:
    bundle = load_template_variant_bundle(job.get("template_id"), job.get("template_name"))
    if bundle:
        job["template_id"] = bundle["preset"]["template_id"]
        job["template_name"] = bundle["preset"]["template_name"]
        job["style"] = bundle["preset"]["template_name"]
        return bundle

    style_value = str(job.get("style", "")).strip()
    if style_value:
        bundle = load_template_variant_bundle(None, style_value)
        if bundle:
            job["template_id"] = bundle["preset"]["template_id"]
            job["template_name"] = bundle["preset"]["template_name"]
            job["style"] = bundle["preset"]["template_name"]
            return bundle
    return None


def heuristic_template_recommendation(job: dict[str, Any]) -> dict[str, str]:
    combined = " ".join(
        str(job.get(field, "") or "")
        for field in ("style", "purpose", "topic", "target_audience")
    ).lower()
    if any(word in combined for word in ["市场", "宣传", "活动", "发布", "品牌"]):
        key = "huixin-market-promo"
    elif any(word in combined for word in ["会议", "周会", "月会", "复盘", "经营会", "项目会", "内部"]):
        key = "huixin-internal-meeting"
    elif any(word in combined for word in ["产品", "方案", "售前", "解决方案", "能力介绍"]):
        key = "huixin-product-solution"
    else:
        key = "huixin"
    bundle = load_template_variant_bundle(key, None)
    assert bundle is not None
    return {
        "recommended_template_id": bundle["preset"]["template_id"],
        "recommended_template_name": bundle["preset"]["template_name"],
        "reason": f"根据用途“{job.get('purpose', '')}”与风格“{job.get('style', '')}”推荐该模板。",
    }


def recommend_template(
    job: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, str]:
    if dry_run or client is None:
        return heuristic_template_recommendation(job)

    prompt = load_prompt_template("Template Recommendation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        templates_json=json.dumps(available_template_choices(), ensure_ascii=False, indent=2),
    )
    result = call_text_model(client, config["text_model"], prompt)
    template_id = result.get("recommended_template_id", "")
    template_name = result.get("recommended_template_name", "")
    bundle = load_template_variant_bundle(template_id, template_name)
    if not bundle:
        return heuristic_template_recommendation(job)
    return {
        "recommended_template_id": bundle["preset"]["template_id"],
        "recommended_template_name": bundle["preset"]["template_name"],
        "reason": result.get("reason", ""),
    }


def build_requirement_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": job.get("template_id"),
        "template_name": job.get("template_name"),
        "topic": job.get("topic"),
        "target_audience": job.get("target_audience"),
        "purpose": job.get("purpose"),
        "style": job.get("style"),
        "page_count": job.get("page_count"),
        "key_points": job.get("key_points", []),
        "must_have_sections": job.get("must_have_sections", []),
        "constraints": job.get("constraints", {}),
    }


def build_requirement_summary_text(job: dict[str, Any], recommendation: dict[str, str] | None = None) -> str:
    pieces = [
        f"主题：{job.get('topic', '')}",
        f"目标受众：{job.get('target_audience', '')}",
        f"用途：{job.get('purpose', '')}",
        f"风格：{job.get('style', '')}",
        f"页数：{job.get('page_count', '')} 页",
    ]
    if job.get("key_points"):
        pieces.append(f"聚焦内容：{' / '.join(str(x) for x in job.get('key_points', []))}")
    if recommendation:
        pieces.append(
            f"推荐模板：{recommendation['recommended_template_name']} ({recommendation['recommended_template_id']})"
        )
    return "；".join(piece for piece in pieces if piece and not piece.endswith("："))


def ensure_requirement_gate(
    job_path: Path,
    job: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> tuple[bool, dict[str, Any] | None]:
    required_missing = find_missing_required_fields(job)
    selected_bundle = normalize_selected_template(job)
    recommendation = None
    if not required_missing and not selected_bundle:
        recommendation = recommend_template(job, client, config, dry_run=dry_run)
    if recommendation:
        job["recommended_template_id"] = recommendation["recommended_template_id"]
        job["recommended_template_name"] = recommendation["recommended_template_name"]
    job["requirement_summary"] = build_requirement_summary_text(job, recommendation)
    write_json(job_path, job)

    if required_missing:
        print("[ERROR] job.json 缺少必要字段：")
        for item in required_missing:
            print(f"- {item}")
        print("")
        print("当前需求摘要：")
        print(job["requirement_summary"])
        return False, None

    if not job.get("requirement_confirmed"):
        print("[STOP] 请先确认需求信息，再继续。")
        print(job["requirement_summary"])
        if recommendation:
            print(
                f"推荐模板：{recommendation['recommended_template_name']} ({recommendation['recommended_template_id']})"
            )
            print("请确认后将 requirement_confirmed 设为 true；如接受推荐，请将 template_id/template_name 写入 job.json。")
        return False, None

    if selected_bundle is None:
        print("[STOP] 请先确认模板/风格，再继续。")
        if recommendation:
            print(
                f"推荐模板：{recommendation['recommended_template_name']} ({recommendation['recommended_template_id']})"
            )
            print("请将推荐模板写入 job.json 的 template_id/template_name 后重新运行。")
        else:
            print("当前 style 无法映射到已知模板，请补充明确的 template_id/template_name。")
        return False, None

    job["template_id"] = selected_bundle["preset"]["template_id"]
    job["template_name"] = selected_bundle["preset"]["template_name"]
    job["style"] = selected_bundle["preset"]["template_name"]
    write_json(job_path, job)
    return True, selected_bundle


def normalize_outline_slide(raw: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "page_no": int(raw.get("page_no", index)),
        "title": raw.get("title") or raw.get("page_title") or f"第{index}页",
        "subtitle": raw.get("subtitle") or raw.get("page_subtitle") or "",
        "purpose": raw.get("purpose") or raw.get("page_goal") or "",
        "layout_type": raw.get("layout_type") or raw.get("layout") or "content",
        "key_blocks": normalize_key_blocks(raw.get("key_blocks", [])),
    }


def normalize_outline_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_slides = payload.get("slides") or payload.get("outline") or []
    return {
        "storyline": payload.get("storyline") or payload.get("storyline_summary") or "",
        "deck_structure": payload.get("deck_structure", []),
        "slides": [normalize_outline_slide(slide, index + 1) for index, slide in enumerate(raw_slides)],
    }


def normalize_key_blocks(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if isinstance(raw, list):
        normalized: list[Any] = []
        for item in raw:
            if isinstance(item, dict):
                block = {
                    "title": str(item.get("title", "")).strip(),
                    "items": [str(x).strip() for x in item.get("items", []) if str(x).strip()],
                    "summary": str(item.get("summary", "")).strip(),
                }
                normalized.append(block)
            else:
                text = str(item).strip()
                if text:
                    normalized.append(text)
        return normalized
    text = str(raw).strip()
    return [text] if text else []


def normalize_slide_intent(raw: dict[str, Any], fallback: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "page_no": int(raw.get("page_no", fallback.get("page_no", index))),
        "title": raw.get("title") or fallback.get("title") or f"第{index}页",
        "subtitle": raw.get("subtitle") or fallback.get("subtitle") or "",
        "page_goal": raw.get("page_goal") or raw.get("purpose") or raw.get("slide_role") or fallback.get("purpose") or "",
        "layout_type": raw.get("layout_type") or fallback.get("layout_type") or "content",
        "key_blocks": normalize_key_blocks(raw.get("key_blocks", fallback.get("key_blocks", []))),
        "visual_focus": raw.get("visual_focus") or "",
        "detail_notes": raw.get("detail_notes") or "",
        "compiled_prompt": raw.get("compiled_prompt") or raw.get("image_prompt") or "",
    }


def format_key_blocks_for_prompt(key_blocks: list[Any]) -> str:
    lines: list[str] = []
    for block in key_blocks:
        if isinstance(block, dict):
            title = block.get("title", "")
            items = block.get("items", [])
            summary = block.get("summary", "")
            if title:
                lines.append(f"- 模块标题：{title}")
            for item in items:
                lines.append(f"  - 要点：{item}")
            if summary:
                lines.append(f"  - 说明：{summary}")
        else:
            lines.append(f"- {block}")
    return "\n".join(lines) if lines else "- 使用 2-4 个核心内容模块"


def format_list(items: list[Any]) -> str:
    return "\n".join(f"- {item}" for item in items if str(item).strip()) or "- 无"


def format_dict_items(data: dict[str, Any]) -> str:
    lines = []
    for key, value in data.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                lines.append(f"- {key}.{sub_key}: {sub_value}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) if lines else "- 无"


def compile_slide_prompt(
    job: dict[str, Any],
    master_style: dict[str, Any],
    slide: dict[str, Any],
    *,
    additional_instruction: str = "",
) -> str:
    template_block = master_style.get("prompt_block", "")
    color_strategy = master_style.get("color_strategy", {})
    typography = master_style.get("typography", {})
    title_rules = master_style.get("title_hierarchy_rules", [])
    layout_system = master_style.get("layout_system", {})
    layout_patterns = master_style.get("module_layout_patterns", [])
    chart_rules = master_style.get("chart_rules", [])
    icon_rules = master_style.get("icon_rules", [])
    forbidden = master_style.get("forbidden_elements", [])

    visible_title = slide.get("title", "")
    visible_subtitle = slide.get("subtitle", "")
    page_goal = slide.get("page_goal", "")
    visual_focus = slide.get("visual_focus", "")
    detail_notes = slide.get("detail_notes", "")

    invisible_guidance = []
    if page_goal:
        invisible_guidance.append(f"- 本页目标（不要原文照搬到页面边角）：{page_goal}")
    if visual_focus:
        invisible_guidance.append(f"- 视觉焦点：{visual_focus}")
    if detail_notes:
        invisible_guidance.append(f"- 细节说明：{detail_notes}")
    if additional_instruction.strip():
        invisible_guidance.append(f"- 额外重编译要求：{additional_instruction.strip()}")
    invisible_text = "\n".join(invisible_guidance) if invisible_guidance else "- 无"

    return f"""你是一位专业的企业级PPT整页视觉设计师。请直接生成完整幻灯片图片。

== 输出硬约束 ==
- 语言：中文
- 画布：16:9 横版
- 分辨率：3840x2160
- 输出必须是一整页完整幻灯片，不是背景图
- 只渲染用户可见内容，不要把 audience、purpose、template name、page number、chapter tag、16:9、页脚说明、边角微文案渲染出来
- 页面必须保持高管汇报风格：结构清晰、留白克制、信息密度高但可读
- 页面必须和同一 deck 里的其他页面在配色角色、标题区节奏、卡片风格、边距、图标线性风格上保持一致

== 需求上下文（仅作不可见指导） ==
- 主题：{job.get('topic', '')}
- 目标受众：{job.get('target_audience', '')}
- 用途：{job.get('purpose', '')}
- 模板：{job.get('template_name') or job.get('style', '')}

== Deck 级 Master Style 契约 ==
- 视觉定位：{master_style.get('visual_positioning', '')}
- Deck 语气：{master_style.get('deck_voice', '')}
- 模板风格块：
{template_block or '- 无'}
- 配色策略：
{format_dict_items(color_strategy)}
- 字体与字号规则：
{format_dict_items(typography)}
- 标题层级规则：
{format_list(title_rules)}
- 布局系统：
{format_dict_items(layout_system)}
- 常用模块版式：
{format_list(layout_patterns)}
- 图表规则：
{format_list(chart_rules)}
- 图标规则：
{format_list(icon_rules)}
- 明确禁止：
{format_list(forbidden)}

== 当前页面意图 ==
- 页面标题（可见）：{visible_title}
- 页面副标题（可见）：{visible_subtitle or '无'}
- 版式类型：{slide.get('layout_type', 'content')}
- 核心内容模块（可见内容）：
{format_key_blocks_for_prompt(slide.get('key_blocks', []))}
- 不可见指导：
{invisible_text}

== 页面渲染规则 ==
- 只渲染标题、副标题、模块标题、模块正文、标签、数字、图示
- 默认使用 2-4 个大模块，除非 layout_type 明确要求矩阵、路线图或多层结构
- 不要出现随机小字、模板名、浮水印、额外说明框
- 若模块较多，优先用卡片、分层、矩阵、路线图、流程图等图示化表达，而不是长段文字
- 所有模块之间要有明确层级、对齐和分隔，避免像拼贴图
"""


def build_single_slide_compiled_prompt(
    title: str,
    prompt_text: str,
    template_bundle: dict[str, Any] | None,
) -> str:
    if not template_bundle:
        return (
            "语言：中文。请生成一页完整的16:9企业级PPT整页图片。只渲染主标题、副标题、核心模块和必要标签，"
            "不要生成边角小字、页码、模板名、16:9、脚注或随机微文案。\n\n"
            f"页面标题：{title.strip() or '单页PPT'}\n"
            f"单页需求：\n{prompt_text.strip()}"
        )

    brief = template_bundle["brief"]
    return compile_slide_prompt(
        {
            "topic": template_bundle["preset"].get("template_name", ""),
            "target_audience": "单页即时生成",
            "purpose": "单页PPT直出",
            "template_name": template_bundle["preset"].get("template_name", ""),
            "style": template_bundle["preset"].get("template_name", ""),
        },
        brief,
        {
            "title": title.strip() or "单页PPT",
            "subtitle": "",
            "page_goal": "根据用户的单页要求生成完整整页图片",
            "layout_type": "single-slide",
            "key_blocks": [prompt_text.strip()],
            "visual_focus": "严格体现模板风格约束",
            "detail_notes": "单页快捷模式，保留模板一致性",
        },
    )


def generate_master_style(
    job: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    selected_bundle: dict[str, Any] | None,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if job.get("master_style"):
        return job["master_style"]

    if selected_bundle is not None:
        brief = copy.deepcopy(selected_bundle["brief"])
        brief["deck_topic"] = job.get("topic", "")
        brief["target_audience"] = job.get("target_audience", "")
        brief["purpose"] = job.get("purpose", "")
        return brief

    if dry_run:
        return {
            "visual_positioning": "正式、专业、结构化",
            "deck_voice": "理性、克制、信息清晰",
            "color_strategy": {"background": "#FFFFFF"},
            "typography": {"title_font": "Microsoft YaHei", "body_font": "Microsoft YaHei"},
            "title_hierarchy_rules": ["每页一个主标题"],
            "layout_system": {"grid": "12-column"},
            "module_layout_patterns": ["双栏对照", "四卡片矩阵"],
            "chart_rules": ["扁平化 2D 图表"],
            "icon_rules": ["统一线性图标"],
            "forbidden_elements": ["3D图表", "随机角标"],
            "prompt_block": "语言：中文，白底，结构化布局。",
        }

    if client is None:
        raise RuntimeError("OpenRouter client is not configured")

    prompt = load_prompt_template("Master Style Brief Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        template_preset_json=json.dumps({}, ensure_ascii=False, indent=2),
    )
    return call_text_model(client, config["text_model"], prompt)


def generate_outline(
    job: dict[str, Any],
    master_style: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    if job.get("outline"):
        return normalize_outline_payload({"storyline": job.get("storyline", ""), "slides": job["outline"]})

    if dry_run:
        slides = []
        for idx in range(1, int(job["page_count"]) + 1):
            slides.append(
                {
                    "page_no": idx,
                    "title": f"{job['topic']} - 第{idx}页",
                    "subtitle": "",
                    "purpose": "支撑整体叙事",
                    "layout_type": "content",
                    "key_blocks": job.get("key_points", [])[:3] or [f"关键模块{idx}A", f"关键模块{idx}B"],
                }
            )
        return {"storyline": f"围绕{job['topic']}逐步展开", "deck_structure": [], "slides": slides}

    if client is None:
        raise RuntimeError("OpenRouter client is not configured")

    prompt = load_prompt_template("Outline Generation Prompt").format(
        requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
        page_count=job["page_count"],
    )
    return normalize_outline_payload(call_text_model(client, config["text_model"], prompt))


def generate_slide_prompts(
    job: dict[str, Any],
    master_style: dict[str, Any],
    outline_payload: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    *,
    dry_run: bool,
) -> dict[str, Any]:
    outline_slides = outline_payload.get("slides", [])

    if job.get("slides"):
        slides = [
            normalize_slide_intent(slide, outline_slides[index] if index < len(outline_slides) else {}, index + 1)
            for index, slide in enumerate(job["slides"])
        ]
    elif dry_run:
        slides = []
        for index, slide in enumerate(outline_slides, start=1):
            slides.append(
                normalize_slide_intent(
                    {
                        "page_no": slide["page_no"],
                        "title": slide["title"],
                        "subtitle": slide.get("subtitle", ""),
                        "page_goal": slide.get("purpose", ""),
                        "layout_type": slide.get("layout_type", "content"),
                        "key_blocks": slide.get("key_blocks", []),
                        "visual_focus": "突出本页最重要的 1-2 个结构模块",
                        "detail_notes": "页面以图示化表达为主，少长段文字。",
                    },
                    slide,
                    index,
                )
            )
    else:
        if client is None:
            raise RuntimeError("OpenRouter client is not configured")
        prompt = load_prompt_template("Per-Slide Prompt Generation Prompt").format(
            requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False, indent=2),
            master_style_json=json.dumps(master_style, ensure_ascii=False, indent=2),
            outline_json=json.dumps(outline_payload, ensure_ascii=False, indent=2),
        )
        payload = call_text_model(client, config["text_model"], prompt)
        raw_slides = payload.get("slides") or payload.get("pages") or []
        slides = []
        for index, outline_slide in enumerate(outline_slides, start=1):
            raw_slide = raw_slides[index - 1] if index - 1 < len(raw_slides) else {}
            slides.append(normalize_slide_intent(raw_slide, outline_slide, index))

    compiled = []
    for slide in slides:
        slide["compiled_prompt"] = compile_slide_prompt(job, master_style, slide)
        compiled.append(slide)
    return {"slides": compiled}


def create_placeholder_image(title: str, page_no: int, output_path: Path) -> None:
    image = Image.new("RGB", (1920, 1080), "#FFFFFF")
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 80, 1840, 1000), outline="#0F95B6", width=8)
    draw.rounded_rectangle((120, 160, 1800, 300), radius=28, fill="#F5F7FA", outline="#E5E7EB")
    draw.text((160, 185), f"{page_no}. {title}", fill="#1E1E1E")
    draw.rounded_rectangle((120, 360, 860, 900), radius=28, fill="#F5F7FA", outline="#A8D86B")
    draw.rounded_rectangle((940, 360, 1800, 900), radius=28, fill="#F5F7FA", outline="#0F95B6")
    image.save(output_path)


def render_images(
    slide_prompts: dict[str, Any],
    client: httpx.Client | None,
    config: dict[str, Any],
    output_dir: Path,
    *,
    dry_run: bool,
) -> list[Path]:
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    image_paths: list[Path] = []
    for slide in slide_prompts["slides"]:
        output_path = image_dir / f"slide_{int(slide['page_no']):02d}.png"
        compiled_prompt = slide.get("compiled_prompt") or slide.get("image_prompt") or ""
        if dry_run:
            create_placeholder_image(slide["title"], int(slide["page_no"]), output_path)
        else:
            if client is None:
                raise RuntimeError("OpenRouter client is not configured")
            prompt = load_prompt_template("Image Rendering Wrapper Prompt").format(
                resolution=config.get("resolution", "3840x2160"),
                image_prompt=compiled_prompt,
            )
            image_bytes = call_image_model(
                client,
                config["image_model"],
                prompt,
                config.get("resolution", "3840x2160"),
            )
            output_path.write_bytes(image_bytes)
        image_paths.append(output_path)
    return image_paths


def persist_stage(output_dir: Path, name: str, data: dict[str, Any]) -> Path:
    path = output_dir / name
    write_json(path, data)
    return path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    config = load_yaml(Path(args.config).expanduser().resolve())
    client = None if args.dry_run else openrouter_client(config)

    try:
        passed, selected_bundle = ensure_requirement_gate(job_path, job, client, config, dry_run=args.dry_run)
        if not passed:
            return 0

        output_dir = resolve_output_dir(job, args.output_dir, job_path)
        output_dir.mkdir(parents=True, exist_ok=True)

        master_style = generate_master_style(job, client, config, selected_bundle, dry_run=args.dry_run)
        persist_stage(output_dir, "master_style.json", master_style)

        outline_payload = generate_outline(job, master_style, client, config, dry_run=args.dry_run)
        persist_stage(output_dir, "outline.json", outline_payload)
        if not (args.auto_approve_outline or job.get("outline_approved")):
            print(f"[STOP] 已生成大纲：{output_dir / 'outline.json'}")
            print("请确认并修改后，将 job.json 中的 outline_approved 设为 true，或使用 --auto-approve-outline 继续。")
            return 0

        slide_prompts = generate_slide_prompts(job, master_style, outline_payload, client, config, dry_run=args.dry_run)
        persist_stage(output_dir, "slide_prompts.json", slide_prompts)
        if not (args.auto_approve_prompts or job.get("prompts_approved")):
            print(f"[STOP] 已生成逐页提示词：{output_dir / 'slide_prompts.json'}")
            print("请确认并修改后，将 job.json 中的 prompts_approved 设为 true，或使用 --auto-approve-prompts 继续。")
            return 0

        image_paths = render_images(slide_prompts, client, config, output_dir, dry_run=args.dry_run)
        pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
        pptx_path = output_dir / pptx_name
        assemble_pptx(image_paths, pptx_path)
        print(f"[OK] PPTX 已生成：{pptx_path}")
        return 0
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
