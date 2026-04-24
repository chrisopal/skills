#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
from typing import Any

import httpx
import yaml

from generate_image_assets import generate_assets_for_specs
from ppt_renderer import build_slide_specs, render_ppt_from_specs
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
        description="Run a confirmation-first direct PPTX job from job.json to page-level PptxGenJS modules."
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
    parser.add_argument(
        "--generate-images",
        action="store_true",
        help="Generate image assets for image_placeholders before rendering PPTX",
    )
    parser.add_argument(
        "--image-dry-run",
        action="store_true",
        help="Generate local placeholder PNGs for image_placeholders even when text/model generation is live",
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


def call_text_completion(
    client: httpx.Client,
    model: str,
    prompt: str,
    *,
    temperature: float = 0.2,
) -> str:
    response = client.post(
        "/chat/completions",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def build_js_generator(client: httpx.Client | None, config: dict[str, Any], *, dry_run: bool):
    if dry_run:
        return None
    if client is None:
        raise RuntimeError("OpenRouter client is not configured")
    model = config.get("pptx_js_model") or config["text_model"]

    def generate(prompt: str) -> str:
        return call_text_completion(client, model, prompt, temperature=0.18)

    return generate


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
        "image_placeholders": normalize_image_placeholders(raw.get("image_placeholders", []), index),
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


def normalize_str_list(raw: Any) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    text = str(raw).strip()
    return [text] if text else []


def normalize_image_placeholders(raw: Any, page_no: int) -> list[dict[str, Any]]:
    if raw is None:
        return []
    items = raw if isinstance(raw, list) else [raw]
    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(items, start=1):
        if isinstance(item, dict):
            prompt = str(item.get("prompt") or item.get("description") or item.get("purpose") or "").strip()
            if not prompt:
                continue
            normalized.append(
                {
                    "id": str(item.get("id") or f"p{page_no}_img{idx}").strip(),
                    "role": str(item.get("role") or "supporting_visual").strip(),
                    "purpose": str(item.get("purpose") or item.get("description") or prompt).strip(),
                    "prompt": prompt,
                    "placement": item.get("placement") if isinstance(item.get("placement"), dict) else {},
                    "required": bool(item.get("required", False)),
                }
            )
        else:
            prompt = str(item).strip()
            if prompt:
                normalized.append(
                    {
                        "id": f"p{page_no}_img{idx}",
                        "role": "supporting_visual",
                        "purpose": prompt,
                        "prompt": prompt,
                        "placement": {},
                        "required": False,
                    }
                )
    return normalized


def flatten_block_texts(key_blocks: list[Any]) -> list[str]:
    texts: list[str] = []
    for block in key_blocks:
        if isinstance(block, dict):
            if str(block.get("title", "")).strip():
                texts.append(str(block.get("title", "")).strip())
            texts.extend(str(item).strip() for item in block.get("items", []) if str(item).strip())
            if str(block.get("summary", "")).strip():
                texts.append(str(block.get("summary", "")).strip())
        elif str(block).strip():
            texts.append(str(block).strip())
    return texts


def infer_page_position(slide: dict[str, Any]) -> str:
    layout = str(slide.get("layout_type", "")).lower()
    title = str(slide.get("title", ""))
    goal = str(slide.get("page_goal") or slide.get("purpose") or "")
    combined = f"{layout} {title} {goal}"
    if int(slide.get("page_no", 0) or 0) == 1 or any(word in combined for word in ["封面", "cover", "总览"]):
        return "封面/方案总览：建立主题认知、方案定位和核心价值主张。"
    if any(word in combined for word in ["路线", "阶段", "计划", "roadmap"]):
        return "行动建议：说明实施路径、阶段任务和落地节奏。"
    if any(word in combined for word in ["蓝图", "架构", "平台", "architecture", "blueprint"]):
        return "方案展示：展示总体架构、能力分层或平台化解决方案。"
    if any(word in combined for word in ["场景", "应用", "scenario"]):
        return "方案展示：展开关键业务场景和可落地能力模块。"
    if any(word in combined for word in ["目标", "价值", "收益", "goal", "kpi"]):
        return "核心结论/价值目标：把业务挑战转化为可衡量的建设目标和收益方向。"
    if any(word in combined for word in ["挑战", "痛点", "问题", "problem"]):
        return "问题引入：说明客户当前挑战，并为后续方案建立必要性。"
    return "内容承接页：围绕本页主题补充论证、结构化展开或形成阶段性结论。"


def infer_core_message(slide: dict[str, Any]) -> str:
    if str(slide.get("core_message", "")).strip():
        return str(slide["core_message"]).strip()
    goal = str(slide.get("page_goal", "")).strip()
    if goal:
        return goal.rstrip("。") + "。"
    title = str(slide.get("title", "")).strip()
    texts = flatten_block_texts(slide.get("key_blocks", []))
    if texts:
        return f"{title}的核心是{texts[0]}，并通过结构化能力支撑业务闭环。"
    return f"本页希望观众记住：{title}是整套方案中的关键组成。"


def build_copy_content(slide: dict[str, Any]) -> dict[str, Any]:
    existing = slide.get("copy_content") if isinstance(slide.get("copy_content"), dict) else {}
    key_blocks = slide.get("key_blocks", [])
    flat_texts = flatten_block_texts(key_blocks)
    data_placeholders = [text for text in flat_texts if "【" in text and "】" in text]
    return {
        "main_title": existing.get("main_title") or slide.get("title", ""),
        "subtitle": existing.get("subtitle") or slide.get("subtitle", ""),
        "key_phrases": normalize_str_list(existing.get("key_phrases")) or [text for text in flat_texts[:6]],
        "body_notes": normalize_str_list(existing.get("body_notes"))
        or [str(block.get("summary", "")).strip() for block in key_blocks if isinstance(block, dict) and str(block.get("summary", "")).strip()],
        "data_placeholders": normalize_str_list(existing.get("data_placeholders")) or data_placeholders,
    }


def infer_layout_design(slide: dict[str, Any]) -> str:
    if str(slide.get("layout_design", "")).strip():
        return str(slide["layout_design"]).strip()
    layout = str(slide.get("layout_type", "content"))
    blocks = slide.get("key_blocks", [])
    block_count = len(blocks)
    if "roadmap" in layout.lower() or any(word in layout for word in ["路线", "阶段"]):
        return "时间轴/路线图布局：上方标题区，下方横向阶段卡片，阶段之间用线条和箭头连接。"
    if any(word in layout.lower() for word in ["blueprint", "architecture", "layer"]) or any(word in layout for word in ["蓝图", "架构", "分层"]):
        return "横向分层架构图：上方标题区，下方按层级排列模块，层与层之间使用结构线或数据流连接。"
    if block_count >= 4:
        return "2×2矩阵/卡片网格布局：上方标题区，下方四个等权重模块卡片，保证标题区和正文区分离。"
    if block_count == 3:
        return "上标题下三栏布局：三张并列核心卡片，突出结构对比和价值递进。"
    if slide.get("image_placeholders"):
        return "左文右图布局：左侧放核心文案和模块卡片，右侧保留独立图片占位区，图片不得覆盖文本。"
    return "咨询公司风格模块布局：上方标题结论，下方使用大卡片或双栏结构组织内容。"


def infer_visual_elements(slide: dict[str, Any]) -> list[str]:
    existing = normalize_str_list(slide.get("visual_elements"))
    if existing:
        return existing
    elements = ["圆角卡片", "Teal结构线", "绿色重点标签", "浅灰分区底"]
    layout = str(slide.get("layout_type", ""))
    if any(word in layout for word in ["路线", "roadmap", "阶段"]):
        elements.extend(["时间轴", "里程碑节点"])
    if any(word in layout for word in ["蓝图", "架构", "blueprint", "architecture"]):
        elements.extend(["分层架构模块", "数据流箭头"])
    if slide.get("image_placeholders"):
        elements.append("图片占位框")
    return elements


def build_image_placeholder_advice(slide: dict[str, Any]) -> dict[str, Any]:
    placeholders = slide.get("image_placeholders", [])
    if not placeholders:
        return {
            "needed": False,
            "note": "本页不需要图片，建议使用图形、图标或版式强化信息。",
            "placeholders": [],
        }
    result = []
    for item in placeholders:
        placement = item.get("placement", {}) if isinstance(item.get("placement"), dict) else {}
        position = (
            f"独立图片区，坐标 x={placement.get('x')}, y={placement.get('y')}, w={placement.get('w')}, h={placement.get('h')}"
            if placement
            else "右侧或独立图片区，避免覆盖文本与卡片"
        )
        result.append(
            {
                "image_position": position,
                "image_purpose": item.get("purpose", ""),
                "image_content_description": item.get("prompt", ""),
                "image_style": "白底、蓝绿灰商务科技风、扁平化、线性图标、不要文字密集",
                "image_ratio": "16:9局部视觉或4:3卡片视觉，按页面占位比例裁切",
                "image_generation_prompt": item.get("prompt", ""),
                "image_search_keywords": item.get("purpose", "") or item.get("role", ""),
            }
        )
    return {"needed": True, "note": "本页包含图片占位，图片必须位于独立保留区域。", "placeholders": result}


def infer_chart_advice(slide: dict[str, Any]) -> dict[str, Any]:
    existing = slide.get("chart_advice") if isinstance(slide.get("chart_advice"), dict) else {}
    if existing:
        return existing
    layout = str(slide.get("layout_type", "")).lower()
    title = str(slide.get("title", ""))
    combined = f"{layout} {title}"
    if any(word in combined for word in ["kpi", "目标", "收益", "证明"]):
        return {
            "needed": True,
            "chart_type": "KPI卡片/指标矩阵",
            "data_fields": ["指标名称", "当前值", "目标值", "改善幅度"],
            "visual_focus": "绿色突出目标值或改善幅度，Teal表示结构标签。",
            "data_placeholders": ["【当前指标待补充】", "【目标值待补充】", "【改善幅度待补充】"],
        }
    if any(word in combined for word in ["路线", "roadmap", "阶段"]):
        return {
            "needed": True,
            "chart_type": "阶段时间轴",
            "data_fields": ["阶段名称", "时间范围", "关键任务", "交付物"],
            "visual_focus": "按阶段递进展示，绿色强调关键里程碑。",
            "data_placeholders": ["【阶段时间待确认】", "【关键交付物待确认】"],
        }
    return {"needed": False, "note": "本页不需要图表。"}


def build_speaker_notes(job: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    existing = normalize_str_list(slide.get("speaker_notes"))
    if existing:
        return existing
    title = slide.get("title", "")
    core = infer_core_message(slide)
    return [
        f"开场先说明本页主题《{title}》在整套方案中的作用。",
        f"随后围绕核心观点展开：{core}",
        "讲解时优先讲结构和业务价值，不逐字念完页面上的每个要点。",
    ]


def build_final_generation_prompt(job: dict[str, Any], master_style: dict[str, Any], slide: dict[str, Any]) -> str:
    title = slide.get("title", "")
    style = job.get("template_name") or job.get("style") or "统一商务科技"
    copy_content = build_copy_content(slide)
    image_advice = build_image_placeholder_advice(slide)
    chart_advice = infer_chart_advice(slide)
    page_position = str(infer_page_position(slide)).rstrip("。；; ")
    core_message = str(infer_core_message(slide)).rstrip("。；; ")
    layout_design = str(infer_layout_design(slide)).rstrip("。；; ")
    image_sentence = ""
    if image_advice.get("needed"):
        first = image_advice["placeholders"][0]
        image_sentence = (
            f"如有图片，请在{first.get('image_position')}放置图片占位，图片内容为{first.get('image_content_description')}，"
            f"风格为{first.get('image_style')}。"
        )
    chart_sentence = ""
    if chart_advice.get("needed"):
        chart_sentence = f"如有图表，请使用{chart_advice.get('chart_type')}展示{', '.join(chart_advice.get('data_fields', []))}。"
    return (
        f"请生成一页 16:9 的 PPT，页面标题为《{title}》。"
        f"本页用于{page_position}，核心观点是{core_message}。"
        f"整体采用{style}风格，版式为{layout_design}。"
        f"页面包含以下文案：主标题「{copy_content.get('main_title')}」；副标题「{copy_content.get('subtitle')}」；"
        f"关键短句包括：{'；'.join(copy_content.get('key_phrases', [])[:8])}。"
        f"视觉上使用{'、'.join(infer_visual_elements(slide))}。"
        f"{image_sentence}{chart_sentence}"
        "整体要求信息清晰、留白充足、层级分明、标题区和正文区不得重叠，适合商务演示。"
    )


def enrich_slide_prompt(job: dict[str, Any], master_style: dict[str, Any], slide: dict[str, Any]) -> dict[str, Any]:
    slide["page_position"] = str(slide.get("page_position") or infer_page_position(slide)).strip()
    slide["core_message"] = str(slide.get("core_message") or infer_core_message(slide)).strip()
    slide["copy_content"] = build_copy_content(slide)
    slide["layout_design"] = infer_layout_design(slide)
    slide["visual_elements"] = infer_visual_elements(slide)
    slide["image_placeholder_advice"] = build_image_placeholder_advice(slide)
    slide["chart_advice"] = infer_chart_advice(slide)
    slide["speaker_notes"] = build_speaker_notes(job, slide)
    slide["final_generation_prompt"] = str(
        slide.get("final_generation_prompt") or build_final_generation_prompt(job, master_style, slide)
    ).strip()
    return slide


def build_quality_checklist(job: dict[str, Any], outline_payload: dict[str, Any], slides: list[dict[str, Any]]) -> dict[str, Any]:
    outline_count = len(outline_payload.get("slides", []))
    page_count = int(job.get("page_count") or outline_count or len(slides))
    titles = [str(slide.get("title", "")).strip() for slide in slides]
    duplicate_titles = sorted({title for title in titles if title and titles.count(title) > 1})
    needs_customer_input: list[str] = []
    for slide in slides:
        for value in flatten_block_texts(slide.get("key_blocks", [])) + slide.get("copy_content", {}).get("data_placeholders", []):
            if "【" in str(value) and "】" in str(value):
                needs_customer_input.append(f"第{slide.get('page_no')}页：{value}")
        chart = slide.get("chart_advice", {})
        for value in chart.get("data_placeholders", []) if isinstance(chart, dict) else []:
            needs_customer_input.append(f"第{slide.get('page_no')}页：{value}")
    return {
        "complete_outline_coverage": len(slides) == page_count and (outline_count == 0 or len(slides) == outline_count),
        "logic_gap_check": "需人工确认页间叙事是否符合客户实际业务；当前已按大纲顺序生成。",
        "one_core_message_per_page": all(bool(str(slide.get("core_message", "")).strip()) for slide in slides),
        "duplicate_pages": duplicate_titles,
        "customer_data_or_assets_needed": needs_customer_input,
        "image_placeholders_executable": all(
            (not slide.get("image_placeholder_advice", {}).get("needed"))
            or bool(slide.get("image_placeholder_advice", {}).get("placeholders"))
            for slide in slides
        ),
        "charts_have_data_fields": all(
            (not slide.get("chart_advice", {}).get("needed")) or bool(slide.get("chart_advice", {}).get("data_fields"))
            for slide in slides
        ),
        "style_consistency": f"统一使用 {job.get('template_name') or job.get('style')} 模板和 deck-level master style。",
        "audience_and_scenario_fit": f"目标受众：{job.get('target_audience', '')}；使用场景：{job.get('purpose', '')}。",
        "ready_for_ppt_generation": not duplicate_titles and len(slides) == page_count,
    }


def normalize_slide_intent(raw: dict[str, Any], fallback: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "page_no": int(raw.get("page_no", fallback.get("page_no", index))),
        "title": raw.get("title") or fallback.get("title") or f"第{index}页",
        "subtitle": raw.get("subtitle") or fallback.get("subtitle") or "",
        "page_goal": raw.get("page_goal") or raw.get("purpose") or raw.get("slide_role") or fallback.get("purpose") or "",
        "layout_type": raw.get("layout_type") or fallback.get("layout_type") or "content",
        "key_blocks": normalize_key_blocks(raw.get("key_blocks", fallback.get("key_blocks", []))),
        "image_placeholders": normalize_image_placeholders(
            raw.get("image_placeholders", fallback.get("image_placeholders", [])),
            int(raw.get("page_no", fallback.get("page_no", index))),
        ),
        "visual_focus": raw.get("visual_focus") or "",
        "detail_notes": raw.get("detail_notes") or "",
        "page_position": raw.get("page_position") or raw.get("page_role") or "",
        "core_message": raw.get("core_message") or raw.get("main_takeaway") or "",
        "copy_content": raw.get("copy_content") if isinstance(raw.get("copy_content"), dict) else {},
        "layout_design": raw.get("layout_design") or raw.get("layout_recommendation") or "",
        "visual_elements": normalize_str_list(raw.get("visual_elements")),
        "image_placeholder_advice": raw.get("image_placeholder_advice")
        if isinstance(raw.get("image_placeholder_advice"), dict)
        else {},
        "chart_advice": raw.get("chart_advice") if isinstance(raw.get("chart_advice"), dict) else {},
        "speaker_notes": normalize_str_list(raw.get("speaker_notes")),
        "final_generation_prompt": raw.get("final_generation_prompt") or "",
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


def format_image_placeholders_for_prompt(placeholders: list[dict[str, Any]]) -> str:
    if not placeholders:
        return "- 无图片占位；如页面需要场景图、产品图、架构视觉或照片，可生成 image_placeholders。"
    lines = []
    for item in placeholders:
        placement = item.get("placement", {})
        placement_text = f"，位置建议：{placement}" if placement else ""
        lines.append(
            f"- {item.get('id')}: {item.get('role')}，用途：{item.get('purpose')}，图片提示词：{item.get('prompt')}{placement_text}"
        )
    return "\n".join(lines)


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


def format_copy_content_for_prompt(copy_content: dict[str, Any]) -> str:
    return (
        f"- 主标题：{copy_content.get('main_title') or '无'}\n"
        f"- 副标题：{copy_content.get('subtitle') or '无'}\n"
        f"- 关键短句：\n{format_list(copy_content.get('key_phrases', []))}\n"
        f"- 必要说明文字：\n{format_list(copy_content.get('body_notes', []))}\n"
        f"- 数据占位符：\n{format_list(copy_content.get('data_placeholders', []))}"
    )


def format_image_advice_for_prompt(image_advice: dict[str, Any]) -> str:
    if not image_advice.get("needed"):
        return image_advice.get("note") or "本页不需要图片，建议使用图形、图标或版式强化信息。"
    lines = ["【图片占位符】"]
    for item in image_advice.get("placeholders", []):
        lines.extend(
            [
                f"- 图片位置：{item.get('image_position', '')}",
                f"- 图片用途：{item.get('image_purpose', '')}",
                f"- 图片内容描述：{item.get('image_content_description', '')}",
                f"- 图片风格：{item.get('image_style', '')}",
                f"- 图片比例：{item.get('image_ratio', '')}",
                f"- 图片生成提示词：{item.get('image_generation_prompt', '')}",
                f"- 图片搜索关键词：{item.get('image_search_keywords', '')}",
            ]
        )
    return "\n".join(lines)


def format_chart_advice_for_prompt(chart_advice: dict[str, Any]) -> str:
    if not chart_advice.get("needed"):
        return chart_advice.get("note") or "本页不需要图表。"
    return (
        f"- 图表类型：{chart_advice.get('chart_type', '')}\n"
        f"- 数据字段：{', '.join(chart_advice.get('data_fields', []))}\n"
        f"- 视觉重点：{chart_advice.get('visual_focus', '')}\n"
        f"- 数据占位符：{', '.join(chart_advice.get('data_placeholders', []))}"
    )


def compile_slide_prompt(
    job: dict[str, Any],
    master_style: dict[str, Any],
    slide: dict[str, Any],
    *,
    additional_instruction: str = "",
) -> str:
    if not slide.get("final_generation_prompt"):
        enrich_slide_prompt(job, master_style, slide)
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
    copy_content = slide.get("copy_content", {}) if isinstance(slide.get("copy_content"), dict) else build_copy_content(slide)
    image_advice = (
        slide.get("image_placeholder_advice")
        if isinstance(slide.get("image_placeholder_advice"), dict)
        else build_image_placeholder_advice(slide)
    )
    chart_advice = slide.get("chart_advice") if isinstance(slide.get("chart_advice"), dict) else infer_chart_advice(slide)
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

    return f"""你是一位专业的企业级PPT页面设计师。请生成用于直接绘制可编辑 PowerPoint 原生对象的完整页面渲染 brief。

== 输出硬约束 ==
- 语言：中文
- 画布：16:9 横版
- 输出目标：可编辑 PPTX 页面，不是整页图片
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
- 图片占位（可见区域；有图片资产时嵌图，无资产时画占位框）：
{format_image_placeholders_for_prompt(slide.get('image_placeholders', []))}
- 不可见指导：
{invisible_text}

== 每页详细 PPT 生成提示词结构 ==
1. 页面定位：
{slide.get('page_position') or infer_page_position(slide)}

2. 页面核心观点：
{slide.get('core_message') or infer_core_message(slide)}

3. 页面文案内容：
{format_copy_content_for_prompt(copy_content)}

4. 版式设计建议：
{slide.get('layout_design') or infer_layout_design(slide)}

5. 视觉元素建议：
{format_list(slide.get('visual_elements') or infer_visual_elements(slide))}

6. 图片占位建议：
{format_image_advice_for_prompt(image_advice)}

7. 图表建议：
{format_chart_advice_for_prompt(chart_advice)}

8. 演讲备注：
{format_list(slide.get('speaker_notes') or build_speaker_notes(job, slide))}

9. 最终 PPT 页面生成提示词：
{slide.get('final_generation_prompt') or build_final_generation_prompt(job, master_style, slide)}

== 页面渲染规则 ==
- 只渲染标题、副标题、模块标题、模块正文、标签、数字、图示
- 默认使用 2-4 个大模块，除非 layout_type 明确要求矩阵、路线图或多层结构
- 不要出现随机小字、模板名、浮水印、额外说明框
- 若模块较多，优先用卡片、分层、矩阵、路线图、流程图等图示化表达，而不是长段文字
- 如果存在图片占位，必须在页面中预留明确图片区，图片区不得挤压标题和核心模块
- 所有模块之间要有明确层级、对齐和分隔，避免像拼贴图
"""


def build_single_slide_compiled_prompt(
    title: str,
    prompt_text: str,
    template_bundle: dict[str, Any] | None,
) -> str:
    if not template_bundle:
        return (
            "语言：中文。请生成一页完整的16:9企业级可编辑PPT页面渲染 brief。只渲染主标题、副标题、核心模块和必要标签，"
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
            "page_goal": "根据用户的单页要求生成完整可编辑PPT页面",
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
                        "image_placeholders": slide.get("image_placeholders", []),
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
        slide = enrich_slide_prompt(job, master_style, slide)
        slide["compiled_prompt"] = compile_slide_prompt(job, master_style, slide)
        compiled.append(slide)
    return {
        "slides": compiled,
        "quality_checklist": build_quality_checklist(job, outline_payload, compiled),
    }


def persist_slide_specs(output_dir: Path, slide_prompts: dict[str, Any], job: dict[str, Any], master_style: dict[str, Any]) -> dict[str, Any]:
    slide_specs = build_slide_specs(job, master_style, slide_prompts)
    persist_stage(output_dir, "slide_specs.json", slide_specs)
    return slide_specs


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

        slide_specs = persist_slide_specs(output_dir, slide_prompts, job, master_style)
        image_generation_config = job.get("image_generation", {}) if isinstance(job.get("image_generation"), dict) else {}
        should_generate_images = args.generate_images or bool(image_generation_config.get("enabled"))
        image_dry_run = args.dry_run or args.image_dry_run or bool(image_generation_config.get("dry_run"))
        if should_generate_images:
            image_dir = output_dir / "generated-images"
            slide_specs, image_assets = generate_assets_for_specs(
                slide_specs,
                master_style,
                config,
                image_dir,
                dry_run=image_dry_run,
            )
            persist_stage(output_dir, "slide_specs.json", slide_specs)
            persist_stage(output_dir, "image_manifest.json", {"assets": image_assets})
        pptx_name = job.get("output", {}).get("pptx_filename", "deck.pptx")
        pptx_path = output_dir / pptx_name
        js_generator = build_js_generator(client, config, dry_run=args.dry_run)
        render_ppt_from_specs(slide_specs, master_style, pptx_path, js_generator=js_generator)
        print(f"[OK] PPTX 已生成：{pptx_path}")
        return 0
    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
