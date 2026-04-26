#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from run_ppt_job import load_json, resolve_output_dir, write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync edited artifacts such as outline.json and slide_prompts.json back into job.json."
    )
    parser.add_argument("job", help="Path to job.json")
    parser.add_argument("--output-dir", default="", help="Optional override for artifacts directory")
    parser.add_argument("--approve-outline", action="store_true", help="Set outline_approved=true after syncing outline.json")
    parser.add_argument("--approve-prompts", action="store_true", help="Set prompts_approved=true after syncing slide_prompts.json")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    job_path = Path(args.job).expanduser().resolve()
    job = load_json(job_path)
    output_dir = resolve_output_dir(job, args.output_dir, job_path)

    master_style_path = output_dir / "master_style.json"
    outline_path = output_dir / "outline.json"
    slide_prompts_path = output_dir / "slide_prompts.json"

    if master_style_path.exists():
        job["master_style"] = load_json(master_style_path)

    if outline_path.exists():
        outline_payload = load_json(outline_path)
        if args.approve_outline:
            for slide in outline_payload.get("slides", []) or []:
                if slide.get("outline_status") not in ("locked",):
                    slide["outline_status"] = "locked"
            write_json(outline_path, outline_payload)
        job["storyline"] = outline_payload.get("storyline", job.get("storyline", ""))
        job["outline"] = outline_payload.get("slides", [])
        if args.approve_outline:
            job["outline_approved"] = True

    if slide_prompts_path.exists():
        slides_payload = load_json(slide_prompts_path)
        if args.approve_prompts:
            for slide in slides_payload.get("slides", []) or []:
                if slide.get("intent_status") not in ("locked",):
                    slide["intent_status"] = "locked"
            write_json(slide_prompts_path, slides_payload)
        job["slides"] = slides_payload.get("slides", [])
        if args.approve_prompts:
            job["prompts_approved"] = True

    write_json(job_path, job)
    print(f"[OK] Synced artifacts back into job.json: {job_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
