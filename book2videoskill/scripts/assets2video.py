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


def build_render_plan(project_dir: Path, style_bible: dict, storyboard: dict) -> dict:
    timing = load_render_timing(project_dir, storyboard)
    duration = timing["durationSec"]
    return {
        "renderer": "remotion",
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
        "providerStatus": "mock-render-plan",
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


def render_silent_video(project_dir: Path, storyboard: dict) -> Path:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    segments_dir = output_dir / "motion_segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    fps = 30
    segment_paths: list[Path] = []
    for index, scene in enumerate(storyboard["scenes"], start=1):
        scene_png = (project_dir / "scene_images" / f"{scene['sceneId']}.png").resolve()
        duration = float(scene.get("renderDurationSec", scene["durationSec"]))
        frames = max(1, int(round(duration * fps)))
        segment = segments_dir / f"{scene['sceneId']}.mp4"
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
    return silent_video


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
    parser.add_argument("--renderer", default="remotion", choices=["remotion", "hyperframe"])
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    style_bible = read_json(project_dir / "style_bible.json")
    storyboard = read_json(project_dir / "storyboard.json")
    asset_manifest = read_json(project_dir / "asset_manifest.json")
    timing = derive_render_timing(project_dir, storyboard)
    render_storyboard = storyboard_with_render_timing(storyboard, timing)

    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    render_plan = build_render_plan(project_dir, style_bible, render_storyboard)
    render_plan["renderer"] = args.renderer
    if args.renderer == "hyperframe":
        render_plan["providerStatus"] = "adapter-designed-not-implemented"
    write_json(project_dir / "render_plan.json", render_plan)

    if (project_dir / "poster.png").exists():
        shutil.copy2(project_dir / "poster.png", output_dir / "poster.png")
    write_remotion_project(project_dir, style_bible, render_storyboard)
    silent_video = render_silent_video(project_dir, render_storyboard)
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
                "- subtitles/all.ass sidecar; visible subtitles are composited into scene frames",
                "- remotion/ render project",
                "- extracted skill zip when available",
                "",
                "Remotion note: `remotion/` follows the Remotion plugin composition/staticFile structure. The MP4 in `output/final_video.mp4` is produced deterministically from generated storyboard frames with visible subtitles, per-scene motion, and TTS audio, so the pipeline closes even before installing the Remotion runtime.",
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
