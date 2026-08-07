#!/usr/bin/env python3
"""Create a deterministic approved signoff fixture for the local smoke test only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pptx import Presentation

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from common import sha256_file, write_json


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    source = Path(args.source).resolve()
    candidate = Path(args.candidate).resolve()
    count = len(Presentation(str(candidate)).slides)
    write_json(
        args.out,
        {
            "version": "1.0.0",
            "status": "approved",
            "reviewer": "Automated smoke fixture; not a human approval",
            "reviewed_at": "2026-08-07T00:00:00Z",
            "source_file": str(source),
            "source_sha256": sha256_file(source),
            "candidate_file": str(candidate),
            "candidate_sha256": sha256_file(candidate),
            "reviewed_slides": list(range(1, count + 1)),
            "confirmed_checks": [
                "rendered_all_slides",
                "checked_slide_overflow",
                "checked_alignment",
                "checked_fonts",
                "checked_images",
                "checked_editability",
            ],
            "notes": "仅用于自动化冒烟测试；真实交付必须由人工创建 signoff。",
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
