from __future__ import annotations

from pathlib import Path

from assemble_pptx import assemble_pptx


def run_stage(image_paths: list[Path], output_dir: Path, *, pptx_name: str = "deck.pptx") -> Path:
    pptx_path = output_dir / pptx_name
    assemble_pptx(image_paths, pptx_path)
    return pptx_path
