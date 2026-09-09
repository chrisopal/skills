#!/usr/bin/env python3
"""Build a reproducible, Huixin-only Skill ZIP without local projects or secrets."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

from attribution_guard import require_skill_integrity

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = {"SKILL.md", "LICENSE", "SPONSORS.md", "SPONSORS_CN.md",
             "requirements.txt", "requirements-core.txt", "INSTALL.md", ".env.example"}
TOP_DIRS = {"scripts", "references", "workflows", "templates"}
EXCLUDED = {"__pycache__", "node_modules", ".git", ".venv", "venv", "projects",
            "exports", "backup", "validation", ".pytest_cache", ".DS_Store"}


def is_reference_image(relative: Path) -> bool:
    parts = relative.parts
    return relative.suffix.lower() == ".png" and (
        parts[:2] == ("references", "ai-image-comparison")
        or (len(parts) == 5 and parts[:2] == ("templates", "decks")
            and parts[2].startswith("huixin_")
            and parts[3:] == ("images", "reference_visual.png"))
    )


def package_files(root: Path, *, include_reference_images: bool = False) -> list[Path]:
    root = root.resolve()
    files = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not include_reference_images and is_reference_image(rel):
            continue
        if not path.is_file() or any(part in EXCLUDED or part.startswith(".")
                                     for part in rel.parts):
            if rel.as_posix() != ".env.example":
                continue
        if path.is_symlink() or root not in path.resolve().parents:
            continue
        if (len(rel.parts) == 1 and rel.name not in TOP_FILES) or (
                len(rel.parts) > 1 and rel.parts[0] not in TOP_DIRS):
            continue
        if path.suffix.lower() in {".pyc", ".pyo", ".zip", ".pptx", ".pdf", ".log"}:
            continue
        if len(rel.parts) > 2 and rel.parts[:2] in {
                ("templates", "brands"), ("templates", "styles"), ("templates", "layouts"),
                ("templates", "decks")}:
            if len(rel.parts) > 3 and not rel.parts[2].startswith("huixin_"):
                continue
        files.append(path)
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--include-reference-images", action="store_true",
                        help="Include optional reference PNGs present in the source checkout")
    args = parser.parse_args()
    require_skill_integrity()
    output = args.output.expanduser().resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("Write the ZIP outside the installed Skill")
    if output.exists():
        parser.error("Output already exists; choose a new ZIP path")
    for kind in ("brands", "styles", "layouts", "decks"):
        catalog = json.loads((ROOT / "templates" / kind / f"{kind}_index.json").read_text("utf-8"))
        if any(not key.startswith("huixin_") for key in catalog):
            parser.error(f"Non-Huixin entries remain in {kind}_index.json")
        if kind == "decks" and len(catalog) != 6:
            parser.error("The distribution must retain all six Huixin Decks")
    files = package_files(ROOT, include_reference_images=args.include_reference_images)
    if args.include_reference_images and not any(
            is_reference_image(path.relative_to(ROOT)) for path in files):
        parser.error("Reference PNGs are not installed; build the reference bundle from source")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            info = zipfile.ZipInfo(f"ppt-master-plus/{path.relative_to(ROOT).as_posix()}",
                                   date_time=(2026, 9, 9, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
    print(json.dumps({"zip": str(output), "files": len(files), "bytes": output.stat().st_size,
                      "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
