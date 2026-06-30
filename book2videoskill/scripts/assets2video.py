#!/usr/bin/env python3
"""Create render_plan.json, render report, Remotion project, and video output."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path

from book2video_common import read_json, write_json

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - validated at runtime.
    Image = None
    ImageDraw = None
    ImageFont = None


def build_render_plan(project_dir: Path, style_bible: dict, storyboard: dict, *, renderer: str, provider_status: str) -> dict:
    timing = load_render_timing(project_dir, storyboard)
    duration = timing["durationSec"]
    return {
        "renderer": renderer,
        "providerStatus": provider_status,
        "compositionName": "BookVideoComposition",
        "coverCompositionName": "CoverPosterComposition",
        "fps": style_bible["fps"],
        "width": style_bible["width"],
        "height": style_bible["height"],
        "coverWidth": style_bible["coverWidth"],
        "coverHeight": style_bible["coverHeight"],
        "durationSec": duration,
        "durationLimitSec": storyboard["durationLimitSec"],
        "sceneOrder": [scene["sceneId"] for scene in storyboard["scenes"]],
        "globalStyleRef": "style_bible.json",
        "storyboardRef": "storyboard.json",
        "assetManifestRef": "asset_manifest.json",
        "narrationRef": "narration_script.md",
        "defaultTransition": {"type": "fade", "durationMs": 320},
        "subtitle": {"enabled": True, "mode": "key_sentence", "maxLines": 2, "highlightColor": "#FF6A00"},
        "bgm": {"enabled": True, "ducking": True, "volume": 0.18},
        "export": {"format": "mp4", "quality": "standard", "platform": style_bible["platform"]},
    }


def write_remotion_project(project_dir: Path, style_bible: dict, storyboard: dict) -> None:
    remotion_dir = project_dir / "remotion"
    src_dir = remotion_dir / "src"
    public_dir = remotion_dir / "public"
    src_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ["style_bible.json", "storyboard.json", "asset_manifest.json", "imagegen_prompts.json", "render_plan.json", "poster.png"]:
        source = project_dir / file_name
        if source.exists():
            shutil.copy2(source, public_dir / file_name)
    scene_public = public_dir / "scene_images"
    scene_public.mkdir(exist_ok=True)
    for path in (project_dir / "scene_images").glob("*.png"):
        shutil.copy2(path, scene_public / path.name)
    imagegen_public = public_dir / "imagegen_sources"
    imagegen_public.mkdir(exist_ok=True)
    for path in (project_dir / "imagegen_sources").glob("*.png"):
        shutil.copy2(path, imagegen_public / path.name)
    (remotion_dir / "package.json").write_text(
        """{
  "name": "book2video-remotion-render",
  "private": true,
  "type": "module",
  "scripts": {
    "studio": "remotion studio src/Root.tsx",
    "render": "remotion render src/Root.tsx BookVideoComposition ../output/final_video.mp4",
    "poster": "remotion still src/Root.tsx CoverPosterComposition ../output/poster.png"
  },
  "dependencies": {
    "@remotion/transitions": "latest",
    "remotion": "latest",
    "react": "latest",
    "react-dom": "latest"
  },
  "devDependencies": {
    "@remotion/cli": "latest",
    "typescript": "latest"
  }
}
""",
        encoding="utf-8",
    )
    storyboard_json = json.dumps(storyboard, ensure_ascii=False, indent=2)
    style_bible_json = json.dumps(style_bible, ensure_ascii=False, indent=2)
    (src_dir / "Root.tsx").write_text(
        f"""import React from 'react';
import {{AbsoluteFill, Composition, Img, Series, registerRoot, staticFile}} from 'remotion';

type Scene = {{
  sceneId: string;
  title: string;
  durationSec: number;
  narration: string;
}};

const storyboard = {storyboard_json};
const styleBible = {style_bible_json};
const fps = styleBible.fps;
const renderTiming = storyboard.renderTiming || Object.fromEntries(storyboard.scenes.map((scene: Scene) => [scene.sceneId, scene.durationSec]));

const palette = styleBible.visualStyle.palette;

const SceneCard = ({{scene}}: {{scene: Scene}}) => {{
  return (
    <AbsoluteFill style={{{{backgroundColor: palette.background}}}}>
      <Img
        src={{staticFile(`scene_images/${{scene.sceneId}}.png`)}}
        style={{{{width: '100%', height: '100%', objectFit: 'cover'}}}}
      />
    </AbsoluteFill>
  );
}};

export const BookVideoComposition = () => (
  <Series>
    {{storyboard.scenes.map((scene: Scene) => (
      <Series.Sequence key={{scene.sceneId}} durationInFrames={{Math.round((renderTiming[scene.sceneId] ?? scene.durationSec) * fps)}}>
        <SceneCard scene={{scene}} />
      </Series.Sequence>
    ))}}
  </Series>
);

export const CoverPosterComposition = () => (
  <AbsoluteFill>
    <Img src={{staticFile('poster.png')}} style={{{{width: '100%', height: '100%', objectFit: 'cover'}}}} />
  </AbsoluteFill>
);

export const RemotionRoot = () => (
  <>
    <Composition
      id="BookVideoComposition"
      component={{BookVideoComposition}}
      durationInFrames={{Math.round((storyboard.renderDurationSec ?? storyboard.targetDurationSec) * fps)}}
      fps={{fps}}
      width={{styleBible.width}}
      height={{styleBible.height}}
      defaultProps={{{{storyboard, styleBible}}}}
    />
    <Composition
      id="CoverPosterComposition"
      component={{CoverPosterComposition}}
      durationInFrames={{1}}
      fps={{fps}}
      width={{styleBible.coverWidth}}
      height={{styleBible.coverHeight}}
      defaultProps={{{{storyboard, styleBible}}}}
    />
  </>
);

registerRoot(RemotionRoot);
""",
        encoding="utf-8",
    )
    (remotion_dir / "README.md").write_text(
        "\n".join(
            [
                "# Remotion Render Project",
                "",
                "This directory is generated by `book2videoskill` for the current book.",
                "",
                "Commands:",
                "",
                "```bash",
                "npm install",
                "npm run poster",
                "npm run render",
                "```",
                "",
                "The already generated `../poster.png` and `../output/final_video.mp4` are closed-loop outputs with audio/subtitles when TTS assets exist. Use this Remotion project when you want to re-render with the Remotion runtime.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def ass_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def wrap_subtitle(text: str, line_len: int = 17, max_lines: int = 2) -> str:
    clean = text.strip()
    lines = [clean[index : index + line_len] for index in range(0, len(clean), line_len)]
    lines = lines[:max_lines]
    if len(clean) > line_len * max_lines:
        lines[-1] = lines[-1].rstrip("，。；、 ") + "..."
    return r"\N".join(lines)


def write_ass_subtitles(project_dir: Path, storyboard: dict, style_bible: dict) -> Path:
    subtitle_dir = project_dir / "subtitles"
    subtitle_dir.mkdir(parents=True, exist_ok=True)
    ass_path = subtitle_dir / "all.ass"
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "ScaledBorderAndShadow: yes",
        f"PlayResX: {style_bible['width']}",
        f"PlayResY: {style_bible['height']}",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Caption,Hiragino Sans GB,56,&H00FFFFFF,&H000000FF,&H7A000000,&H9A000000,0,0,0,0,100,100,0,0,1,4,1,2,72,72,120,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    elapsed = 0
    for scene in storyboard["scenes"]:
        duration = scene.get("renderDurationSec", scene["durationSec"])
        start = elapsed + 0.6
        end = max(start + 0.8, elapsed + float(duration) - 0.35)
        lines.append(f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Caption,,0,0,0,,{wrap_subtitle(scene['narration'])}")
        elapsed += float(duration)
    ass_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ass_path


def load_font(size: int, *, bold: bool = False):
    if ImageFont is None:
        return None
    candidates = [
        ("/System/Library/Fonts/Hiragino Sans GB.ttc", 2 if bold else 0),
        ("/System/Library/Fonts/STHeiti Medium.ttc", 0),
        ("/System/Library/Fonts/STHeiti Light.ttc", 1),
        ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", 0),
    ]
    for candidate, index in candidates:
        try:
            return ImageFont.truetype(candidate, size=size, index=index)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in text:
        candidate = current + char
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
                if len(lines) >= max_lines:
                    lines[-1] = lines[-1].rstrip("，。；、 ") + "..."
                    return lines
            current = char
    if current:
        lines.append(current)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1].rstrip("，。；、 ") + "..."
    return lines


def create_video_overlay(project_dir: Path, scene: dict, style_bible: dict) -> Path:
    if Image is None or ImageDraw is None:
        raise RuntimeError("Pillow is required to render OpenRouter video text overlays.")
    overlay_dir = project_dir / "output" / "video_overlays"
    overlay_dir.mkdir(parents=True, exist_ok=True)
    overlay_path = overlay_dir / f"{scene['sceneId']}.png"
    width = int(style_bible["width"])
    height = int(style_bible["height"])
    palette = style_bible.get("visualStyle", {}).get("palette", {})
    primary = palette.get("primary", "#F97316")
    secondary = palette.get("secondary", "#0B5D3B")
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    small_font = load_font(30)
    title_font = load_font(70, bold=True)
    subtitle_font = load_font(38)

    pill_text = "一本书，一个 AI Skill"
    pill_x, pill_y = 64, 58
    pill_w = int(draw.textlength(pill_text, font=small_font)) + 54
    pill_h = 58
    draw.rounded_rectangle((pill_x, pill_y, pill_x + pill_w, pill_y + pill_h), radius=29, fill=secondary)
    draw.text((pill_x + 27, pill_y + 12), pill_text, font=small_font, fill="#FFFFFF")

    panel_h = 310
    panel_y = height - panel_h - 54
    draw.rounded_rectangle((54, panel_y, width - 54, height - 54), radius=28, fill=(255, 253, 247, 232), outline=primary, width=3)
    x = 98
    y = panel_y + 42
    draw.text((x, y), scene["title"], font=title_font, fill=primary)
    y += 92
    max_width = width - 196
    for line in wrap_text(draw, scene["narration"], subtitle_font, max_width, 2):
        draw.text((x, y), line, font=subtitle_font, fill=secondary)
        y += 52
    image.save(overlay_path)
    return overlay_path


def probe_audio_duration(path: Path) -> float | None:
    if not path.exists():
        return None
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nw=1:nk=1",
            str(path),
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


def load_render_timing(project_dir: Path, storyboard: dict) -> dict:
    timing_path = project_dir / "render_timing.json"
    if timing_path.exists():
        return read_json(timing_path)
    return {
        "durationSec": storyboard["targetDurationSec"],
        "sceneDurations": {scene["sceneId"]: float(scene["durationSec"]) for scene in storyboard["scenes"]},
        "source": "storyboard",
    }


def derive_render_timing(project_dir: Path, storyboard: dict) -> dict:
    scene_durations: dict[str, float] = {}
    audio_durations: dict[str, float | None] = {}
    for scene in storyboard["scenes"]:
        scene_id = scene["sceneId"]
        audio_duration = probe_audio_duration(project_dir / "tts_audio" / f"{scene_id}.mp3")
        audio_durations[scene_id] = audio_duration
        if audio_duration is None:
            scene_durations[scene_id] = float(scene["durationSec"])
        else:
            scene_durations[scene_id] = float(max(6, math.ceil(audio_duration + 0.8)))
    total = round(sum(scene_durations.values()), 3)
    timing = {
        "durationSec": total,
        "sceneDurations": scene_durations,
        "audioDurations": audio_durations,
        "source": "tts_audio" if any(value is not None for value in audio_durations.values()) else "storyboard",
        "policy": "duration=max(6s, ceil(tts_duration+0.8s)); keeps scene transitions tight and avoids long silent holds",
    }
    write_json(project_dir / "render_timing.json", timing)
    return timing


def storyboard_with_render_timing(storyboard: dict, timing: dict) -> dict:
    timed = json.loads(json.dumps(storyboard, ensure_ascii=False))
    timed["renderDurationSec"] = timing["durationSec"]
    timed["renderTiming"] = timing["sceneDurations"]
    for scene in timed["scenes"]:
        scene["renderDurationSec"] = timing["sceneDurations"][scene["sceneId"]]
    return timed


def read_openrouter_video_manifest(project_dir: Path, storyboard: dict) -> dict | None:
    manifest_path = project_dir / "openrouter_video_manifest.json"
    if not manifest_path.exists():
        return None
    manifest = read_json(manifest_path)
    scene_ids = {scene["sceneId"] for scene in storyboard["scenes"]}
    assets = {
        item.get("sceneId"): project_dir / item.get("path", "")
        for item in manifest.get("assets", [])
        if item.get("sceneId") in scene_ids and item.get("path")
    }
    if not any((assets.get(scene_id) and assets[scene_id].exists()) for scene_id in scene_ids):
        return None
    return manifest


def run_openrouter_video(project_dir: Path, *, timeout_sec: int, reuse_existing: bool) -> bool:
    cmd = [
        str(Path(__file__).resolve().parent / "openrouter_video.py"),
        "--project-dir",
        str(project_dir),
        "--timeout-sec",
        str(timeout_sec),
    ]
    if reuse_existing:
        cmd.append("--reuse-existing")
    result = subprocess.run(
        [sys_executable(), *cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    (project_dir / "openrouter_video_run.log").write_text(
        "\n".join(["# stdout", result.stdout, "# stderr", result.stderr]) + "\n",
        encoding="utf-8",
    )
    return result.returncode == 0


def sys_executable() -> str:
    import sys

    return sys.executable


def clip_path_for_scene(project_dir: Path, manifest: dict | None, scene_id: str) -> Path | None:
    if not manifest:
        return None
    for item in manifest.get("assets", []):
        if item.get("sceneId") == scene_id and item.get("path"):
            path = project_dir / item["path"]
            return path if path.exists() else None
    return None


def render_video_track(project_dir: Path, storyboard: dict, style_bible: dict, *, openrouter_manifest: dict | None = None) -> tuple[Path, str]:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    segments_dir = output_dir / "motion_segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    fps = 30
    segment_paths: list[Path] = []
    openrouter_count = 0
    for index, scene in enumerate(storyboard["scenes"], start=1):
        scene_png = (project_dir / "scene_images" / f"{scene['sceneId']}.png").resolve()
        duration = float(scene.get("renderDurationSec", scene["durationSec"]))
        frames = max(1, int(round(duration * fps)))
        segment = segments_dir / f"{scene['sceneId']}.mp4"
        video_clip = clip_path_for_scene(project_dir, openrouter_manifest, scene["sceneId"])
        if video_clip:
            openrouter_count += 1
            overlay = create_video_overlay(project_dir, scene, style_bible)
            vf = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=rgba[base];[1:v]format=rgba[ov];[base][ov]overlay=0:0,format=yuv420p"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-stream_loop",
                    "-1",
                    "-i",
                    str(video_clip),
                    "-i",
                    str(overlay),
                    "-t",
                    f"{duration:.3f}",
                    "-filter_complex",
                    vf,
                    "-an",
                    "-r",
                    str(fps),
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(segment),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            zoom_end = 1.035 + (0.01 if index % 2 == 0 else 0)
            vf = (
                f"zoompan=z='min(1+({zoom_end}-1)*on/{frames},{zoom_end})':"
                "x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':"
                f"d={frames}:s=1080x1920:fps={fps},format=yuv420p"
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-loop",
                    "1",
                    "-i",
                    str(scene_png),
                    "-frames:v",
                    str(frames),
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-movflags",
                    "+faststart",
                    str(segment),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        segment_paths.append(segment)
    concat_path = output_dir / "ffmpeg-scenes.txt"
    concat_path.write_text("\n".join(f"file '{path.resolve().as_posix()}'" for path in segment_paths) + "\n", encoding="utf-8")
    silent_video = output_dir / "video_silent.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(silent_video),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if openrouter_count == len(storyboard["scenes"]):
        provider = "openrouter-video"
    elif openrouter_count:
        provider = f"openrouter-video-partial-{openrouter_count}-of-{len(storyboard['scenes'])}-local-remotion-fallback"
    else:
        provider = "local-remotion-fallback"
    return silent_video, provider


def build_audio_track(project_dir: Path, storyboard: dict) -> Path | None:
    output_dir = project_dir / "output"
    padded_dir = output_dir / "tts_padded"
    padded_dir.mkdir(parents=True, exist_ok=True)
    list_path = output_dir / "tts-concat.txt"
    lines: list[str] = []
    for scene in storyboard["scenes"]:
        scene_id = scene["sceneId"]
        source = project_dir / "tts_audio" / f"{scene_id}.mp3"
        if not source.exists():
            return None
        duration = float(scene.get("renderDurationSec", scene["durationSec"]))
        padded = padded_dir / f"{scene_id}.m4a"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-af",
                f"apad,atrim=0:{duration}",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(padded),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        lines.append(f"file '{padded.resolve().as_posix()}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    audio_track = output_dir / "narration.m4a"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-c",
            "copy",
            str(audio_track),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return audio_track


def escape_filter_path(path: Path) -> str:
    return path.resolve().as_posix().replace("\\", "\\\\").replace(":", "\\:")


def mux_audio(project_dir: Path, silent_video: Path, audio_track: Path | None) -> Path:
    final_video = project_dir / "output" / "final_video.mp4"
    cmd = ["ffmpeg", "-y", "-i", str(silent_video)]
    if audio_track:
        cmd.extend(["-i", str(audio_track)])
    cmd.extend(["-c:v", "copy", "-movflags", "+faststart"])
    if audio_track:
        cmd.extend(["-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "128k"])
    cmd.append(str(final_video))
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return final_video


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, help="Book2Video project directory")
    parser.add_argument("--renderer", default="openrouter-video", choices=["openrouter-video", "remotion", "hyperframe"])
    parser.add_argument("--openrouter-video-timeout-sec", type=int, default=900)
    parser.add_argument("--reuse-openrouter-video", action="store_true")
    parser.add_argument("--skip-openrouter-video-generation", action="store_true")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    style_bible = read_json(project_dir / "style_bible.json")
    storyboard = read_json(project_dir / "storyboard.json")
    asset_manifest = read_json(project_dir / "asset_manifest.json")
    timing = derive_render_timing(project_dir, storyboard)
    render_storyboard = storyboard_with_render_timing(storyboard, timing)

    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    openrouter_manifest = None
    provider_status = "local-remotion-fallback"
    if args.renderer == "openrouter-video":
        run_ok = False
        if not args.skip_openrouter_video_generation:
            run_ok = run_openrouter_video(project_dir, timeout_sec=args.openrouter_video_timeout_sec, reuse_existing=args.reuse_openrouter_video)
        openrouter_manifest = read_openrouter_video_manifest(project_dir, render_storyboard)
        if openrouter_manifest:
            provider_status = "openrouter-video" if run_ok and openrouter_manifest.get("status") == "generated" else "openrouter-video-partial-local-remotion-fallback"
        else:
            provider_status = "openrouter-video-failed-local-remotion-fallback"
    elif args.renderer == "hyperframe":
        provider_status = "adapter-designed-not-implemented-local-remotion-fallback"

    render_plan = build_render_plan(project_dir, style_bible, render_storyboard, renderer=args.renderer, provider_status=provider_status)
    write_json(project_dir / "render_plan.json", render_plan)

    if (project_dir / "poster.png").exists():
        shutil.copy2(project_dir / "poster.png", output_dir / "poster.png")
    write_remotion_project(project_dir, style_bible, render_storyboard)
    silent_video, actual_video_provider = render_video_track(project_dir, render_storyboard, style_bible, openrouter_manifest=openrouter_manifest)
    audio_track = build_audio_track(project_dir, render_storyboard)
    ass_path = write_ass_subtitles(project_dir, render_storyboard, style_bible)
    final_video = mux_audio(project_dir, silent_video, audio_track)
    stale_project_bundle = project_dir / "project_bundle.zip"
    if stale_project_bundle.exists():
        stale_project_bundle.unlink()

    render_report = project_dir / "render_report.md"
    render_report.write_text(
        "\n".join(
            [
                "# Render Report",
                "",
                f"Renderer: {args.renderer}",
                f"Actual video provider: {actual_video_provider}",
                f"Provider status: {provider_status}",
                f"Duration: {render_storyboard['renderDurationSec']} sec",
                f"Storyboard source duration: {storyboard['targetDurationSec']} sec",
                f"Scenes: {len(storyboard['scenes'])}",
                "",
                "Status: closed-loop render completed.",
                "",
                "Generated outputs:",
                "- poster.png",
                "- output/poster.png",
                "- output/final_video.mp4",
                "- output/narration.m4a" if audio_track else "- audio missing: no TTS MP3 assets found",
                "- render_timing.json",
                "- openrouter_video_manifest.json" if openrouter_manifest else "- OpenRouter video unavailable; local Remotion fallback used",
                "- subtitles/all.ass sidecar; visible subtitles are composited into scene frames",
                "- remotion/ render project",
                "- extracted skill zip when available",
                "",
                "Render note: OpenRouter video clips are preferred when `openrouter_video_manifest.json` has one generated clip per scene. If the provider fails or times out, `remotion/` plus the local ffmpeg motion-segment renderer remains the deterministic fallback with visible subtitles and TTS audio.",
                "",
                f"Scene assets generated: {sum(1 for item in asset_manifest['sceneImages'] if item.get('status') == 'generated')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    print(f"render_project: {project_dir}")
    print(f"final_video: {final_video}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
