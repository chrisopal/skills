#!/usr/bin/env python3
"""Render PPTX slides to PNG via LibreOffice and Poppler."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pptx import Presentation

from common import emu_to_in, ensure_dir, sha256_file, write_json


def find_executable(candidates: list[str]) -> str | None:
    for name in candidates:
        path = shutil.which(name)
        if path:
            return path
    return None


def run_command(cmd: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def convert_to_pdf(input_path: Path, temp_dir: Path) -> tuple[Path, list[str]]:
    soffice = find_executable(["soffice", "libreoffice"])
    if not soffice:
        raise RuntimeError("LibreOffice/soffice not found. Install it or run structural audit without rendering.")

    logs: list[str] = []
    profile = temp_dir / "lo_profile"
    home = temp_dir / "home"
    convert_dir = temp_dir / "convert"
    profile.mkdir(parents=True, exist_ok=True)
    home.mkdir(parents=True, exist_ok=True)
    convert_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(home)

    base_cmd = [
        soffice,
        f"-env:UserInstallation=file://{profile}",
        "--headless",
        "--invisible",
        "--nologo",
        "--norestore",
    ]
    proc = run_command(base_cmd + ["--convert-to", "pdf", "--outdir", str(convert_dir), str(input_path)], env)
    logs.append(proc.stdout.strip())
    logs.append(proc.stderr.strip())
    pdf_path = convert_dir / f"{input_path.stem}.pdf"
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        return pdf_path, [line for line in logs if line]

    # Some decks export more reliably after an intermediate ODP normalization.
    proc = run_command(base_cmd + ["--convert-to", "odp", "--outdir", str(convert_dir), str(input_path)], env)
    logs.extend([proc.stdout.strip(), proc.stderr.strip()])
    odp_path = convert_dir / f"{input_path.stem}.odp"
    if odp_path.exists():
        proc = run_command(base_cmd + ["--convert-to", "pdf", "--outdir", str(convert_dir), str(odp_path)], env)
        logs.extend([proc.stdout.strip(), proc.stderr.strip()])
    if pdf_path.exists() and pdf_path.stat().st_size > 0:
        return pdf_path, [line for line in logs if line]

    raise RuntimeError("LibreOffice could not convert the deck to PDF. " + " | ".join(line for line in logs if line))


def render_pptx(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    width_px: int = 1600,
    height_px: int = 900,
    keep_pdf: bool = False,
) -> dict[str, Any]:
    input_path = Path(input_path).resolve()
    output_dir = ensure_dir(output_dir).resolve()
    if not input_path.exists():
        raise FileNotFoundError(input_path)

    rasterizer = find_executable(["pdftocairo", "pdftoppm"])
    if not rasterizer:
        raise RuntimeError("Poppler renderer not found (pdftocairo/pdftoppm).")

    prs = Presentation(str(input_path))
    width_in = emu_to_in(prs.slide_width)
    height_in = emu_to_in(prs.slide_height)
    if width_in <= 0 or height_in <= 0:
        raise RuntimeError("Invalid slide dimensions.")
    dpi = max(72, round(min(width_px / width_in, height_px / height_in)))

    for existing in output_dir.glob("slide-*.png"):
        existing.unlink()

    with tempfile.TemporaryDirectory(prefix="ppt_render_") as tmp:
        temp_dir = Path(tmp)
        pdf_path, conversion_logs = convert_to_pdf(input_path, temp_dir)
        prefix = output_dir / "rendered"
        if Path(rasterizer).name == "pdftocairo":
            cmd = [rasterizer, "-png", "-r", str(dpi), str(pdf_path), str(prefix)]
        else:
            cmd = [rasterizer, "-png", "-r", str(dpi), str(pdf_path), str(prefix)]
        proc = run_command(cmd)
        if proc.returncode != 0:
            raise RuntimeError(f"Rasterization failed: {proc.stderr.strip() or proc.stdout.strip()}")

        generated: list[tuple[int, Path]] = []
        for path in output_dir.glob("rendered-*.png"):
            match = re.search(r"-(\d+)\.png$", path.name)
            if match:
                generated.append((int(match.group(1)), path))
        generated.sort(key=lambda item: item[0])
        if not generated:
            raise RuntimeError("Rasterizer completed but produced no slide images.")

        slide_paths: list[str] = []
        for number, src in generated:
            dst = output_dir / f"slide-{number}.png"
            src.replace(dst)
            slide_paths.append(str(dst))

        if keep_pdf:
            shutil.copy2(pdf_path, output_dir / f"{input_path.stem}.pdf")

    manifest = {
        "version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": str(input_path),
        "source_sha256": sha256_file(input_path),
        "slide_count": len(slide_paths),
        "slide_width_in": width_in,
        "slide_height_in": height_in,
        "dpi": dpi,
        "width_target_px": width_px,
        "height_target_px": height_px,
        "slides": slide_paths,
        "conversion_logs": conversion_logs,
    }
    write_json(output_dir / "render_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a PPTX deck to slide PNGs.")
    parser.add_argument("input", help="Input PPTX/PPTM")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--width", type=int, default=1600, help="Target maximum width")
    parser.add_argument("--height", type=int, default=900, help="Target maximum height")
    parser.add_argument("--keep-pdf", action="store_true", help="Keep the intermediate PDF")
    args = parser.parse_args()
    try:
        result = render_pptx(
            args.input,
            args.out,
            width_px=args.width,
            height_px=args.height,
            keep_pdf=args.keep_pdf,
        )
        print(f"Rendered {result['slide_count']} slides to {args.out}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
