from __future__ import annotations

from pathlib import Path

from assemble_pptx import assemble_pptx
from PIL import Image
from pptx import Presentation


def _write_image(path: Path, color: str) -> None:
    Image.new("RGB", (320, 180), color).save(path)


def test_assemble_pptx_preserves_one_slide_per_image(tmp_path: Path) -> None:
    image_paths = []
    for idx, color in enumerate(["#ff0000", "#00ff00", "#0000ff"], 1):
        image_path = tmp_path / f"slide_{idx:02d}.png"
        _write_image(image_path, color)
        image_paths.append(image_path)

    output_path = tmp_path / "deck.pptx"
    assemble_pptx(image_paths, output_path)

    prs = Presentation(str(output_path))

    assert len(prs.slides) == 3
