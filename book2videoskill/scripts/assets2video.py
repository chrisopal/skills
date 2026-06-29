#!/usr/bin/env python3
"""Create render_plan.json, render report, and a project bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import zipfile
from pathlib import Path

from book2video_common import read_json, relpath, write_json


def build_render_plan(project_dir: Path, style_bible: dict, storyboard: dict) -> dict:
    return {
        "renderer": "remotion",
        "compositionName": "BookVideoComposition",
        "coverCompositionName": "CoverPosterComposition",
        "fps": style_bible["fps"],
        "width": style_bible["width"],
        "height": style_bible["height"],
        "coverWidth": style_bible["coverWidth"],
        "coverHeight": style_bible["coverHeight"],
        "durationSec": storyboard["targetDurationSec"],
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


def zip_project(project_dir: Path, zip_path: Path) -> None:
    include_suffixes = {".json", ".md", ".svg", ".srt", ".txt", ".png", ".mp4", ".zip", ".tsx", ".ts", ".js"}
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(project_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            if path.suffix in include_suffixes:
                archive.write(path, relpath(path, project_dir))


def write_remotion_project(project_dir: Path, style_bible: dict, storyboard: dict) -> None:
    remotion_dir = project_dir / "remotion"
    src_dir = remotion_dir / "src"
    public_dir = remotion_dir / "public"
    src_dir.mkdir(parents=True, exist_ok=True)
    public_dir.mkdir(parents=True, exist_ok=True)
    for file_name in ["style_bible.json", "storyboard.json", "asset_manifest.json", "render_plan.json", "poster.png"]:
        source = project_dir / file_name
        if source.exists():
            shutil.copy2(source, public_dir / file_name)
    scene_public = public_dir / "scene_images"
    scene_public.mkdir(exist_ok=True)
    for path in (project_dir / "scene_images").glob("*.png"):
        shutil.copy2(path, scene_public / path.name)
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

const palette = styleBible.visualStyle.palette;

const SceneCard = ({{scene}}: {{scene: Scene}}) => {{
  return (
    <AbsoluteFill style={{{{backgroundColor: palette.background, padding: 72, fontFamily: styleBible.visualStyle.fontFamily}}}}>
      <div style={{{{height: '100%', border: '4px solid ' + palette.line, borderRadius: 28, background: '#fff', padding: 56}}}}>
        <div style={{{{color: palette.secondary, fontSize: 30, fontWeight: 700}}}}>一本书，一个AI Skill</div>
        <h1 style={{{{color: palette.primary, fontSize: 76, lineHeight: 1.08, marginTop: 42}}}}>{{scene.title}}</h1>
        <Img src={{staticFile(`scene_images/${{scene.sceneId}}.png`)}} style={{{{width: '100%', borderRadius: 20, marginTop: 36}}}} />
        <p style={{{{fontSize: 44, lineHeight: 1.45, color: palette.secondaryText, marginTop: 40}}}}>{{scene.narration}}</p>
      </div>
    </AbsoluteFill>
  );
}};

export const BookVideoComposition = () => (
  <Series>
    {{storyboard.scenes.map((scene: Scene) => (
      <Series.Sequence key={{scene.sceneId}} durationInFrames={{Math.round(scene.durationSec * fps)}}>
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
      durationInFrames={{Math.round(storyboard.targetDurationSec * fps)}}
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
                "The already generated `../poster.png` and `../output/final_video.mp4` are the closed-loop fallback outputs. Use this Remotion project when you want to re-render with the Remotion runtime.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def render_video_with_ffmpeg(project_dir: Path, storyboard: dict) -> Path:
    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    concat_path = output_dir / "ffmpeg-scenes.txt"
    lines: list[str] = []
    for scene in storyboard["scenes"]:
        scene_png = (project_dir / "scene_images" / f"{scene['sceneId']}.png").resolve()
        lines.append(f"file '{scene_png.as_posix()}'")
        lines.append(f"duration {int(scene['durationSec'])}")
    last_png = (project_dir / "scene_images" / f"{storyboard['scenes'][-1]['sceneId']}.png").resolve()
    lines.append(f"file '{last_png.as_posix()}'")
    concat_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    final_video = output_dir / "final_video.mp4"
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_path),
        "-t",
        str(int(storyboard["targetDurationSec"])),
        "-vf",
        "fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(final_video),
    ]
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

    output_dir = project_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    render_plan = build_render_plan(project_dir, style_bible, storyboard)
    render_plan["renderer"] = args.renderer
    if args.renderer == "hyperframe":
        render_plan["providerStatus"] = "adapter-designed-not-implemented"
    write_json(project_dir / "render_plan.json", render_plan)

    if (project_dir / "poster.png").exists():
        shutil.copy2(project_dir / "poster.png", output_dir / "poster.png")
    write_remotion_project(project_dir, style_bible, storyboard)
    final_video = render_video_with_ffmpeg(project_dir, storyboard)

    render_report = project_dir / "render_report.md"
    render_report.write_text(
        "\n".join(
            [
                "# Render Report",
                "",
                f"Renderer: {args.renderer}",
                f"Duration: {storyboard['targetDurationSec']} sec",
                f"Scenes: {len(storyboard['scenes'])}",
                "",
                "Status: closed-loop render completed.",
                "",
                "Generated outputs:",
                "- poster.png",
                "- output/poster.png",
                "- output/final_video.mp4",
                "- remotion/ render project",
                "- extracted skill zip when available",
                "",
                "Remotion note: `remotion/` follows the Remotion plugin composition/staticFile structure. The MP4 in `output/final_video.mp4` is produced deterministically from the generated scene frames so the pipeline closes even before installing the Remotion runtime.",
                "",
                f"Scene assets generated: {sum(1 for item in asset_manifest['sceneImages'] if item.get('status') == 'generated')}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    bundle_path = project_dir / "project_bundle.zip"
    zip_project(project_dir, bundle_path)

    print(f"render_project: {project_dir}")
    print(f"final_video: {final_video}")
    print(f"bundle: {bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
