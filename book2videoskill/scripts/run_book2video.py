#!/usr/bin/env python3
"""Run the Book2VideoSkill scaffold pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from book2video_common import load_input, normalize_input, repo_default_projects_root, slugify_book


SCRIPT_DIR = Path(__file__).resolve().parent


def run_step(args: list[str]) -> None:
    subprocess.run([sys.executable, *args], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Input JSON file")
    parser.add_argument("--book", help="Book title")
    parser.add_argument("--author", help="Book author")
    parser.add_argument(
        "--output-root",
        default=str(repo_default_projects_root()),
        help="Output root directory. Defaults to book2videoskill/projects so each book gets a durable local project directory.",
    )
    parser.add_argument("--output-dir", help="Exact project output directory")
    parser.add_argument("--storyboard-only", action="store_true", help="Stop after Book2StoryboardTool")
    parser.add_argument("--cover-only", action="store_true", help="Generate storyboard and asset cover handoff, then stop")
    parser.add_argument("--renderer", default="openrouter-video", choices=["openrouter-video", "remotion", "hyperframe"])
    parser.add_argument("--tts-provider", default="openrouter", choices=["openrouter", "say", "none"])
    parser.add_argument("--openrouter-video-timeout-sec", type=int, default=900)
    parser.add_argument("--reuse-openrouter-video", action="store_true")
    parser.add_argument("--skip-openrouter-video-generation", action="store_true")
    args = parser.parse_args()

    raw = load_input(args.input)
    if args.book:
        raw["bookTitle"] = args.book
    if args.author:
        raw["bookAuthor"] = args.author
    input_data = normalize_input(raw)

    output_dir = Path(args.output_dir or Path(args.output_root) / slugify_book(input_data["bookTitle"]))
    storyboard_args = [str(SCRIPT_DIR / "book2storyboard.py"), "--output-dir", str(output_dir)]
    if args.input:
        storyboard_args.extend(["--input", args.input])
    if args.book:
        storyboard_args.extend(["--book", args.book])
    if args.author:
        storyboard_args.extend(["--author", args.author])

    run_step(storyboard_args)
    if args.storyboard_only:
        print(f"stopped: storyboard-only project={output_dir}")
        return 0

    run_step([str(SCRIPT_DIR / "storyboard2assets.py"), "--project-dir", str(output_dir)])
    if args.cover_only:
        print(f"stopped: cover-only project={output_dir}")
        return 0

    run_step([str(SCRIPT_DIR / "create_extracted_skill.py"), "--project-dir", str(output_dir)])
    run_step([str(SCRIPT_DIR / "openrouter_tts.py"), "--project-dir", str(output_dir), "--provider", args.tts_provider])
    render_args = [
        str(SCRIPT_DIR / "assets2video.py"),
        "--project-dir",
        str(output_dir),
        "--renderer",
        args.renderer,
        "--openrouter-video-timeout-sec",
        str(args.openrouter_video_timeout_sec),
    ]
    if args.reuse_openrouter_video:
        render_args.append("--reuse-openrouter-video")
    if args.skip_openrouter_video_generation:
        render_args.append("--skip-openrouter-video-generation")
    run_step(render_args)
    print(f"complete: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
