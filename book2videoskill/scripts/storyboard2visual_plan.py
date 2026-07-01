#!/usr/bin/env python3
"""Convert storyboard.json into the v1.2 visual director plan."""

from __future__ import annotations

import argparse
from pathlib import Path

from book2video_common import ensure_storyboard_v12_fields, infer_visual_role, read_json, write_json


MOTION_TYPES = {
    "hook": "slow_push_in",
    "problem": "slow_push_in",
    "book_core": "subtle_float",
    "core_model": "none",
    "sop": "pan_right",
    "ai_skill": "slow_push_in",
    "use_cases": "pan_left",
    "summary": "slow_pull_out",
}


def visual_role(scene: dict) -> str:
    return infer_visual_role(scene)


def motion_type(role: str) -> str:
    return MOTION_TYPES.get(role, "subtle_float")


def needs_image_to_video(role: str) -> bool:
    return role in {"hook", "problem", "book_core", "ai_skill", "use_cases", "summary"}


def needs_motion_graphics(role: str) -> bool:
    return role in {"hook", "core_model", "sop", "ai_skill", "use_cases", "summary"}


def motion_graphics_type(role: str, scene: dict) -> str:
    visual_type = scene.get("visualType", "")
    if "pyramid" in visual_type:
        return "pyramid_build"
    if "flywheel" in visual_type or "flow" in visual_type:
        return "process_flow"
    if role == "sop":
        return "grouping_cards"
    if role == "ai_skill":
        return "ai_pipeline"
    if role == "summary":
        return "tag_bar"
    return "concept_cards"


def overlay_text(scene: dict, duration: float) -> list[dict]:
    title_end = min(duration, 3.0)
    return [
        {
            "text": scene["title"],
            "role": "title",
            "timing": {"startSec": 0, "endSec": title_end},
            "animation": "slide",
        },
        {
            "text": scene["subtitle"],
            "role": "subtitle",
            "timing": {"startSec": 0.6, "endSec": max(1.6, duration - 0.3)},
            "animation": "fade",
        },
    ]


def motion_spec(role: str, scene: dict, duration: float) -> dict | None:
    if not needs_motion_graphics(role):
        return None
    labels = [scene["title"]]
    if role == "core_model":
        labels = ["目标", "现实", "根因", "原则", "执行"] if "原则" in scene.get("narration", "") else ["结论", "理由", "证据"]
    elif role == "ai_skill":
        labels = ["输入材料", "AI Skill", "结构化输出"]
    elif role == "sop":
        labels = ["散乱材料", "归类分组", "形成原则"]
    elements = [
        {
            "id": f"e{index}",
            "type": "diagram_node" if index > 1 else "card",
            "label": label,
            "enterAnimation": "draw_line" if index > 1 else "slide",
            "order": index,
        }
        for index, label in enumerate(labels, start=1)
    ]
    timing = []
    cursor = 0.4
    step = min(1.2, max(0.4, duration / max(1, len(elements) + 2)))
    for element in elements:
        timing.append({"elementId": element["id"], "startSec": round(cursor, 2), "endSec": round(min(duration, cursor + step), 2)})
        cursor += step * 0.75
    return {
        "type": motion_graphics_type(role, scene),
        "providerPriority": ["svg_motion", "lottie", "remotion_motion", "after_effects"],
        "durationSec": duration,
        "elements": elements,
        "timing": timing,
    }


def build_visual_plan(project_dir: Path) -> dict:
    style_bible = read_json(project_dir / "style_bible.json")
    storyboard = read_json(project_dir / "storyboard.json")
    if ensure_storyboard_v12_fields(storyboard):
        write_json(project_dir / "storyboard.json", storyboard)
    palette = style_bible["visualStyle"]["palette"]
    scene_plans = []
    for scene in storyboard["scenes"]:
        role = visual_role(scene)
        duration = float(scene.get("renderDurationSec", scene["durationSec"]))
        image_to_video = needs_image_to_video(role)
        motion_graphics = needs_motion_graphics(role)
        style_prompt = scene.get("imageSourceStrategy", {}).get("imagePrompt") or scene["visualDescription"]
        scene_plan = {
            "sceneId": scene["sceneId"],
            "visualRole": role,
            "generationStrategy": {
                "styleFrame": image_to_video or role in {"hook", "book_core", "summary"},
                "imageToVideo": image_to_video,
                "motionGraphics": motion_graphics,
                "rendererTextOverlay": True,
            },
            "styleFramePrompt": style_prompt,
            "imageToVideoPrompt": (
                "Animate this style frame into a subtle premium knowledge-video shot. "
                "Keep the composition stable. Do not add readable text. Do not change the layout. "
                f"Use gentle camera movement: {motion_type(role)}. "
                "Add subtle paper texture motion, soft parallax, and minimal character movement if present. "
                "Professional Xiaohongshu business knowledge video style. Orange primary, green secondary, warm off-white background. "
                "No dramatic motion, no cinematic chaos, no extra objects."
            )
            if image_to_video
            else None,
            "cameraMotion": {"type": motion_type(role), "intensity": "low"},
            "motionGraphicsSpec": motion_spec(role, scene, duration),
            "overlayText": overlay_text(scene, duration),
            "negativePrompt": [
                "baked Chinese text",
                "garbled text",
                "watermark",
                "logo",
                "overly cartoonish mascot",
                "dramatic chaotic camera movement",
            ],
        }
        scene_plans.append(scene_plan)
    return {
        "projectName": storyboard["projectName"],
        "bookTitle": storyboard["bookTitle"],
        "visualStrategy": {
            "overallMode": "hybrid_ai_video_motion_graphics",
            "styleFrameMode": "imagegen",
            "dynamicVideoMode": "image_to_video",
            "textMode": "renderer_overlay",
            "motionMode": "lottie_svg_remotion_or_ae",
            "finalAssemblyMode": "remotion_ffmpeg_or_ae",
        },
        "globalRules": {
            "primaryColor": palette["primary"],
            "secondaryColor": palette["secondary"],
            "textRendering": "renderer_overlay",
            "avoidBakedChineseText": True,
            "videoClipMaxDurationSec": 15,
            "useImageToVideoFor": ["hook", "problem", "book_core", "ai_skill", "use_cases", "summary"],
            "useMotionGraphicsFor": ["core_model", "sop", "ai_skill", "use_cases", "summary"],
        },
        "scenes": scene_plans,
    }


def write_report(project_dir: Path, visual_plan: dict) -> None:
    lines = [
        "# Visual Plan Report",
        "",
        f"Project: {visual_plan['projectName']}",
        f"Book: {visual_plan['bookTitle']}",
        "",
        "| Scene | Role | Style frame | Image-to-video | Motion graphics | Text overlay |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for scene in visual_plan["scenes"]:
        strategy = scene["generationStrategy"]
        lines.append(
            f"| {scene['sceneId']} | {scene['visualRole']} | {strategy['styleFrame']} | {strategy['imageToVideo']} | {strategy['motionGraphics']} | {strategy['rendererTextOverlay']} |"
        )
    (project_dir / "visual_plan.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    reports = project_dir / "reports"
    reports.mkdir(exist_ok=True)
    (reports / "visual_plan_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()
    project_dir = Path(args.project_dir)
    visual_plan = build_visual_plan(project_dir)
    write_json(project_dir / "visual_plan.json", visual_plan)
    write_report(project_dir, visual_plan)
    print(f"visual_plan_project: {project_dir}")
    print(f"visual_plan_scenes: {len(visual_plan['scenes'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
