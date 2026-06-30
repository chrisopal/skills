#!/usr/bin/env python3
"""Create v1.2 motion graphics placeholders and manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

from book2video_common import read_json, relpath, write_json


def write_svg_motion(path: Path, spec: dict, width: int, height: int) -> None:
    title = spec["type"].replace("_", " ").title()
    nodes = spec.get("elements", [])
    card_w = min(760, width - 180)
    y = 220
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="none"/>',
        f'<text x="90" y="130" font-family="Arial, sans-serif" font-size="46" font-weight="700" fill="#F97316">{title}</text>',
    ]
    for item in nodes:
        label = item.get("label", item["id"])
        lines.extend(
            [
                f'<rect x="90" y="{y}" width="{card_w}" height="90" rx="20" fill="#FFFDF7" stroke="#F4A261" stroke-width="3">',
                f'  <animate attributeName="opacity" from="0" to="1" dur="0.35s" begin="{(item["order"] - 1) * 0.16}s" fill="freeze"/>',
                "</rect>",
                f'<text x="128" y="{y + 57}" font-family="Arial, sans-serif" font-size="30" fill="#0B5D3B">{label}</text>',
            ]
        )
        y += 120
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    style_bible = read_json(project_dir / "style_bible.json")
    visual_plan = read_json(project_dir / "visual_plan.json")
    motion_dir = project_dir / "motion_graphics"
    motion_dir.mkdir(parents=True, exist_ok=True)
    assets = []
    for scene in visual_plan["scenes"]:
        spec = scene.get("motionGraphicsSpec")
        if not spec:
            continue
        asset_path = motion_dir / f"{scene['sceneId']}_{spec['type']}.svg"
        write_svg_motion(asset_path, spec, style_bible["width"], style_bible["height"])
        assets.append(
            {
                "sceneId": scene["sceneId"],
                "provider": "svg_motion",
                "type": spec["type"],
                "assetPath": relpath(asset_path, project_dir),
                "durationSec": spec["durationSec"],
                "transparentBackground": True,
                "metadata": {
                    "providerPriority": spec["providerPriority"],
                    "elements": len(spec.get("elements", [])),
                },
            }
        )
    manifest = {
        "providerPriority": ["svg_motion", "lottie", "remotion_motion", "after_effects"],
        "status": "generated" if assets else "empty",
        "motionGraphics": assets,
    }
    write_json(project_dir / "motion_graphics_manifest.json", manifest)
    report = project_dir / "reports" / "motion_report.md"
    report.parent.mkdir(exist_ok=True)
    report.write_text(
        "\n".join(
            [
                "# Motion Graphics Report",
                "",
                f"Assets: {len(assets)}",
                "Provider: svg_motion fallback placeholders with staggered element timing.",
                "",
                *[f"- {asset['sceneId']}: {asset['type']} -> {asset['assetPath']}" for asset in assets],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"motion_graphics_project: {project_dir}")
    print(f"motion_graphics: {len(assets)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
