#!/usr/bin/env python3
"""Validate a Book2VideoSkill project directory."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from book2video_common import ensure_storyboard_v12_fields, is_principles, is_pyramid_principle, read_json

try:
    from PIL import Image, ImageStat
except ImportError:  # pragma: no cover - validated at runtime.
    Image = None
    ImageStat = None


REQUIRED_FILES = [
    "video_brief.md",
    "book_research.json",
    "book_core.json",
    "style_bible.json",
    "cover_poster_plan.json",
    "storyboard.json",
    "narration_script.md",
    "xiaohongshu_publish.md",
]

ASSET_STAGE_FILES = [
    "asset_manifest.json",
    "imagegen_prompts.json",
    "assets_ready_report.md",
    "visual_plan.json",
    "visual_plan.md",
    "style_frames_manifest.json",
    "motion_graphics_manifest.json",
]
RENDER_STAGE_FILES = [
    "render_plan.json",
    "render_report.md",
    "poster.png",
    "output/poster.png",
    "output/final_video.mp4",
    "render_timing.json",
    "dynamic_video_manifest.json",
    "assembly_timeline.json",
    "subtitles/all.ass",
]
PYRAMID_TERMS = ["结论先行", "以上统下", "归类分组", "逻辑递进", "AI汇报结构生成器"]
PRINCIPLES_TERMS = ["极度求真", "极度透明", "创意择优", "痛苦 + 反思 = 进步", "可信度加权决策", "AI原则复盘教练"]


def require_file(project_dir: Path, rel_path: str, errors: list[str]) -> Path:
    path = project_dir / rel_path
    if not path.exists():
        errors.append(f"missing required file: {rel_path}")
    return path


def validate_path_refs(project_dir: Path, manifest: dict, errors: list[str]) -> None:
    refs: list[str] = []
    for key in ["coverImage", "mascotImage", "musicAsset", "imagegenCoverElement"]:
        if key in manifest and manifest[key].get("path"):
            refs.append(manifest[key]["path"])
    for key in ["sceneImages", "ttsAssets", "subtitleAssets"]:
        for item in manifest.get(key, []):
            if item.get("path"):
                refs.append(item["path"])
    for rel_path in refs:
        if not (project_dir / rel_path).exists():
            errors.append(f"asset manifest path does not exist: {rel_path}")


def visual_crop_score(image_path: Path) -> tuple[float, float] | None:
    if Image is None or ImageStat is None or not image_path.exists():
        return None
    image = Image.open(image_path).convert("RGB")
    width, height = image.size
    crop = image.crop((int(width * 0.13), int(height * 0.12), int(width * 0.87), int(height * 0.76)))
    stat = ImageStat.Stat(crop)
    avg_stddev = sum(stat.stddev) / len(stat.stddev)
    pixels = crop.load()
    sample_step = max(1, min(crop.size) // 120)
    varied = 0
    total = 0
    for y in range(0, crop.height, sample_step):
        for x in range(0, crop.width, sample_step):
            r, g, b = pixels[x, y]
            distance = abs(r - 255) + abs(g - 247) + abs(b - 236)
            if distance > 32:
                varied += 1
            total += 1
    varied_ratio = varied / total if total else 0
    return avg_stddev, varied_ratio


def validate_scene_visual_density(project_dir: Path, scenes: list[dict], errors: list[str]) -> None:
    for scene in scenes:
        scene_id = scene.get("sceneId", "<missing>")
        score = visual_crop_score(project_dir / "scene_images" / f"{scene_id}.png")
        if score is None:
            continue
        avg_stddev, varied_ratio = score
        if avg_stddev < 8.0 or varied_ratio < 0.025:
            errors.append(
                f"scene image visual area appears empty: {scene_id} "
                f"(stddev={avg_stddev:.2f}, variedRatio={varied_ratio:.3f})"
            )


def probe_video_duration(video_path: Path) -> float | None:
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(video_path),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if probe.returncode != 0:
        return None
    try:
        return float(probe.stdout.strip())
    except ValueError:
        return None


def validate_video_visual_density(video_path: Path, errors: list[str]) -> None:
    if Image is None or ImageStat is None or not video_path.exists():
        return
    duration = probe_video_duration(video_path) or 0
    sample_times = [max(1.0, duration * 0.12), max(1.0, duration * 0.5), max(1.0, duration * 0.88)]
    with tempfile.TemporaryDirectory(prefix="book2video-frames-") as tmp:
        valid_scores = []
        for index, sample_time in enumerate(sample_times, start=1):
            frame_path = Path(tmp) / f"frame-{index}.png"
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{sample_time:.3f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    str(frame_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if result.returncode != 0 or not frame_path.exists():
                errors.append(f"could not extract validation frame from final_video.mp4 at {sample_time:.2f}s")
                continue
            score = visual_crop_score(frame_path)
            if score is not None:
                valid_scores.append(score)
        if valid_scores and all(avg_stddev < 8.0 or varied_ratio < 0.025 for avg_stddev, varied_ratio in valid_scores):
            score_text = ", ".join(f"stddev={s:.2f}/varied={v:.3f}" for s, v in valid_scores)
            errors.append(f"final_video.mp4 visual area appears empty across sampled frames ({score_text})")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_dir", help="Book2Video project directory")
    parser.add_argument("--require-assets", action="store_true", help="Require asset stage files")
    parser.add_argument("--require-render", action="store_true", help="Require real final render media")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    errors: list[str] = []
    warnings: list[str] = []
    render_duration: float | None = None

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
    ensure_storyboard_v12_fields(storyboard)

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
        "visualRole",
        "recommendedVisualMode",
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
    if is_principles(book_core.get("bookTitle", "")):
        for term in PRINCIPLES_TERMS:
            if term not in all_text:
                errors.append(f"principles output missing term: {term}")
        if book_core.get("visualModel", {}).get("type") != "flywheel":
            errors.append("principles visualModel.type must be flywheel")

    has_asset_stage = (project_dir / "asset_manifest.json").exists()
    if args.require_assets or has_asset_stage:
        for rel_path in ASSET_STAGE_FILES:
            require_file(project_dir, rel_path, errors)
        if (project_dir / "asset_manifest.json").exists():
            manifest = read_json(project_dir / "asset_manifest.json")
            if manifest.get("imageProvider", {}).get("default") != "imagegen":
                errors.append("asset_manifest imageProvider.default must be imagegen")
            imagegen_prompts = read_json(project_dir / "imagegen_prompts.json") if (project_dir / "imagegen_prompts.json").exists() else []
            if len(imagegen_prompts) < len(scenes) + 1:
                errors.append("imagegen_prompts must include poster plus one prompt per scene")
            for prompt in imagegen_prompts:
                if not prompt.get("targetPath", "").startswith("imagegen_sources/"):
                    errors.append(f"imagegen prompt targetPath must point to imagegen_sources/: {prompt.get('assetId', '<missing>')}")
            validate_path_refs(project_dir, manifest, errors)
            if len(manifest.get("sceneImages", [])) != len(scenes):
                errors.append("asset_manifest sceneImages count must match storyboard scenes")
            if len(manifest.get("ttsAssets", [])) != len(scenes):
                errors.append("asset_manifest ttsAssets count must match storyboard scenes")
            if any(item.get("status") == "placeholder" for item in manifest.get("sceneImages", [])):
                warnings.append("scene visuals are placeholder handoffs; real image provider not yet run")
            validate_scene_visual_density(project_dir, scenes, errors)
        if (project_dir / "visual_plan.json").exists():
            visual_plan = read_json(project_dir / "visual_plan.json")
            if visual_plan.get("visualStrategy", {}).get("overallMode") != "hybrid_ai_video_motion_graphics":
                errors.append("visual_plan visualStrategy.overallMode must be hybrid_ai_video_motion_graphics")
            if visual_plan.get("globalRules", {}).get("textRendering") != "renderer_overlay":
                errors.append("visual_plan globalRules.textRendering must be renderer_overlay")
            if len(visual_plan.get("scenes", [])) != len(scenes):
                errors.append("visual_plan scenes count must match storyboard scenes")
            for scene_plan in visual_plan.get("scenes", []):
                strategy = scene_plan.get("generationStrategy", {})
                if not strategy.get("rendererTextOverlay"):
                    errors.append(f"visual_plan scene must use rendererTextOverlay: {scene_plan.get('sceneId')}")
        if (project_dir / "style_frames_manifest.json").exists():
            style_frames = read_json(project_dir / "style_frames_manifest.json").get("styleFrames", [])
            if len(style_frames) != len(scenes):
                errors.append("style_frames_manifest count must match storyboard scenes")
            for frame in style_frames:
                if not (project_dir / frame.get("assetPath", "")).exists():
                    errors.append(f"style frame asset missing: {frame.get('assetPath')}")

    has_render_stage = (project_dir / "render_plan.json").exists()
    if has_render_stage:
        for rel_path in RENDER_STAGE_FILES:
            require_file(project_dir, rel_path, errors)
        render_plan = read_json(project_dir / "render_plan.json")
        if (project_dir / "render_timing.json").exists():
            render_timing = read_json(project_dir / "render_timing.json")
            expected_render_duration = round(sum(float(value) for value in render_timing.get("sceneDurations", {}).values()), 3)
            render_duration = float(render_timing.get("durationSec", expected_render_duration))
        else:
            expected_render_duration = float(total_duration)
        if round(float(render_plan.get("durationSec", 0)), 3) != round(expected_render_duration, 3):
            errors.append("render_plan durationSec must equal render_timing duration")
        if render_plan.get("providerStatus") == "openrouter-video":
            manifest_path = project_dir / "openrouter_video_manifest.json"
            require_file(project_dir, "openrouter_video_manifest.json", errors)
            if manifest_path.exists():
                video_manifest = read_json(manifest_path)
                if video_manifest.get("status") != "generated":
                    errors.append("openrouter_video_manifest status must be generated when providerStatus is openrouter-video")
                clip_paths = {item.get("sceneId"): item.get("path") for item in video_manifest.get("assets", [])}
                for scene in scenes:
                    rel_path = clip_paths.get(scene["sceneId"])
                    if not rel_path or not (project_dir / rel_path).exists():
                        errors.append(f"missing OpenRouter video clip for scene: {scene['sceneId']}")
        extracted_skill_zips = list(project_dir.glob("*.zip"))
        if not extracted_skill_zips:
            errors.append("missing extracted book-derived skill zip")
        if (project_dir / "project_bundle.zip").exists():
            errors.append("project_bundle.zip should not be generated")
        if not (project_dir / "remotion" / "src" / "Root.tsx").exists():
            errors.append("missing generated Remotion project: remotion/src/Root.tsx")
        if (project_dir / "dynamic_video_manifest.json").exists():
            dynamic_manifest = read_json(project_dir / "dynamic_video_manifest.json")
            if len(dynamic_manifest.get("dynamicClips", [])) != len(scenes):
                errors.append("dynamic_video_manifest dynamicClips count must match storyboard scenes")
        if (project_dir / "assembly_timeline.json").exists():
            timeline = read_json(project_dir / "assembly_timeline.json")
            if round(float(timeline.get("durationSec", 0)), 3) != round(expected_render_duration, 3):
                errors.append("assembly_timeline durationSec must equal render_timing duration")

    if args.require_render:
        real_outputs = [
            "output/final_video.mp4",
            "poster.png",
            "output/poster.png",
            "output/narration.m4a",
            "tts_manifest.json",
            "subtitles/all.ass",
        ]
        for rel_path in real_outputs:
            require_file(project_dir, rel_path, errors)
        final_video = project_dir / "output/final_video.mp4"
        if final_video.exists():
            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "a:0",
                    "-show_entries",
                    "stream=codec_type",
                    "-of",
                    "csv=p=0",
                    str(final_video),
                ],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if probe.returncode != 0 or "audio" not in probe.stdout:
                errors.append("final_video.mp4 must contain an audio stream")
            validate_video_visual_density(final_video, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1

    render_note = f" renderDuration={render_duration:g}s" if render_duration is not None else ""
    print(f"OK: {project_dir} scenes={len(scenes)} storyboardDuration={total_duration}s{render_note}")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
