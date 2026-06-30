#!/usr/bin/env python3
"""Create v1.2 style frame manifests from visual_plan.json."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from book2video_common import read_json, relpath, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    style_bible = read_json(project_dir / "style_bible.json")
    visual_plan = read_json(project_dir / "visual_plan.json")
    style_dir = project_dir / "style_frames"
    style_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for scene in visual_plan["scenes"]:
        scene_id = scene["sceneId"]
        source = project_dir / "scene_images" / f"{scene_id}.png"
        target = style_dir / f"{scene_id}.png"
        if source.exists():
            shutil.copy2(source, target)
        frames.append(
            {
                "sceneId": scene_id,
                "prompt": scene["styleFramePrompt"],
                "negativePrompt": scene["negativePrompt"],
                "assetPath": relpath(target, project_dir),
                "width": style_bible["width"],
                "height": style_bible["height"],
                "aspectRatio": style_bible["aspectRatio"],
                "metadata": {
                    "provider": "imagegen_with_component_overlay" if source.exists() else "pending_imagegen",
                    "transparentBackground": False,
                    "containsBakedChineseText": False,
                    "rendererOverlayRequired": True,
                },
            }
        )
    manifest = {
        "provider": "imagegen",
        "status": "generated" if frames else "empty",
        "styleFrames": frames,
    }
    write_json(project_dir / "style_frames_manifest.json", manifest)
    report = project_dir / "reports" / "style_frame_report.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Style Frame Report",
                "",
                f"Frames: {len(frames)}",
                "Text policy: no long Chinese text should be baked into ImageGen/video outputs; renderer overlays remain authoritative.",
                "",
                *[f"- {frame['sceneId']}: {frame['assetPath']}" for frame in frames],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"style_frames_project: {project_dir}")
    print(f"style_frames: {len(frames)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
