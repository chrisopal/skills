"""Mark image placeholders for regeneration without invoking the image model here.

Usage:
    python scripts/regenerate_image.py --slide-specs artifacts/slide_specs.json
        --slide 5 --img-id page-05-img-1 [--reason "user disliked first attempt"]

The script flips the matching placeholder.status to "regenerating" and appends
a history entry. The actual generation work runs through
`generate_image_assets.py --ids ...` (Phase 7), which scans for placeholders in
"pending" or "regenerating" state.

If the placeholder is already `generated`, history records the user's intent
to regenerate; the next generate_image_assets.py run will overwrite the
generated_path.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def regenerate(
    slide_specs: dict,
    *,
    page_no: int,
    img_id: str | None = None,
    reason: str = "",
) -> int:
    """Mutate slide_specs in place; return number of placeholders updated."""

    updated = 0
    for slide in slide_specs.get("slides", []):
        if slide.get("page_no") != page_no:
            continue
        for placeholder in slide.get("image_placeholders", []):
            if img_id and placeholder.get("id") != img_id:
                continue
            previous = placeholder.get("status", "placeholder")
            placeholder["status"] = "regenerating"
            placeholder.setdefault("history", []).append({
                "ts": _now_iso(),
                "from": previous,
                "to": "regenerating",
                "reason": reason or "user requested regeneration",
            })
            updated += 1
    return updated


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Mark image placeholder(s) for regeneration."
    )
    parser.add_argument("--slide-specs", required=True, type=Path)
    parser.add_argument("--slide", required=True, type=int, help="page_no")
    parser.add_argument("--img-id", help="Specific image_placeholder.id (otherwise all on page)")
    parser.add_argument("--reason", default="")
    args = parser.parse_args(argv)

    data = json.loads(args.slide_specs.read_text(encoding="utf-8"))
    updated = regenerate(data, page_no=args.slide, img_id=args.img_id, reason=args.reason)
    args.slide_specs.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    print(f"flipped {updated} placeholder(s) to status=regenerating on page {args.slide}")
    return 0 if updated else 2


if __name__ == "__main__":
    sys.exit(main())
