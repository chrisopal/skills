"""Build a master_style.json from a reference image (PPT screenshot, web hero, etc).

Two-stage pipeline:

  1. Pure-Python palette extraction  ->  seeds color_strategy.
  2. Vision model (with the image + extracted palette as input) -> fills in
     typography, deck_voice, module_layout_patterns, forbidden_elements,
     and confidence ratings.

The vision call is wrapped behind an injectable `vision_caller` so tests can
mock the model. The script merges the vision response on top of palette-derived
defaults, sets `source: "reference_extracted"`, and validates against the
master_style schema before returning.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, ValidationError

from importlib import util as _importlib_util

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "master_style.schema.json"
DEFAULT_OUT_PATH = SKILL_ROOT / "artifacts" / "master_style.json"


def _load_palette_module():
    name = "palette_extraction"
    if name in sys.modules:
        return sys.modules[name]
    lib_path = SKILL_ROOT / "scripts" / "lib" / "palette_extraction.py"
    spec = _importlib_util.spec_from_file_location(name, lib_path)
    module = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


palette_mod = _load_palette_module()


class ReferenceStyleError(RuntimeError):
    pass


@dataclass
class ReferenceResult:
    master_style: dict
    palette: list  # list[PaletteColor]


def _build_vision_prompt(palette_hexes: list[str]) -> str:
    return (
        "You are a presentation design analyst. Look at the reference image "
        "and produce a master_style supplement JSON object with these fields only:\n"
        "  - typography (object of typography slots; same shape as in the schema)\n"
        "  - deck_voice (string)\n"
        "  - visual_positioning (string)\n"
        "  - module_layout_patterns (array of strings)\n"
        "  - forbidden_elements (array of strings)\n"
        "  - chart_rules (array of strings)\n"
        "  - icon_rules (array of strings)\n"
        "  - language (BCP-47 string)\n"
        "  - template_id (kebab-case string)\n"
        "  - template_name (string)\n"
        "  - prompt_block (string)\n"
        "  - confidence (object of dotted-path -> [0,1] number)\n\n"
        f"Pre-extracted palette (top 6, dominance-sorted): {', '.join(palette_hexes)}.\n"
        "Do NOT include color_strategy in your response - it is already set.\n"
        "Output JSON only."
    )


def build_master_style(
    image_path: Path,
    *,
    vision_caller: Callable[[bytes, str], Any],
    n_colors: int = 6,
) -> ReferenceResult:
    if not image_path.exists():
        raise FileNotFoundError(image_path)

    palette = palette_mod.extract_palette(image_path, n_colors=n_colors)
    color_strategy = palette_mod.palette_to_color_strategy(palette)

    image_bytes = image_path.read_bytes()
    prompt = _build_vision_prompt([c.hex for c in palette])
    raw = vision_caller(image_bytes, prompt)
    if not isinstance(raw, dict):
        raise ReferenceStyleError("vision model returned non-object response")

    if "color_strategy" in raw:
        raw.pop("color_strategy", None)

    master_style: dict[str, Any] = {
        "language": raw.get("language", "zh-CN"),
        "color_strategy": color_strategy,
        "source": "reference_extracted",
        "parent_template_id": None,
    }
    for key in (
        "template_id", "template_name", "visual_positioning", "deck_voice",
        "typography", "title_hierarchy_rules", "layout_system",
        "module_layout_patterns", "chart_rules", "icon_rules",
        "forbidden_elements", "prompt_block", "confidence",
        "pattern_palette", "lock_fields",
    ):
        if key in raw:
            master_style[key] = raw[key]

    master_style.setdefault("template_id", "reference-extracted")
    master_style.setdefault("template_name", "Reference Extracted")
    master_style.setdefault("typography", {"title_font": "Inter", "body_font": "Inter"})

    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(master_style), key=lambda e: list(e.path))
    if errors:
        raise ReferenceStyleError(
            "assembled master_style failed schema validation: "
            + "; ".join(f"{list(e.path)}: {e.message}" for e in errors[:5])
        )

    return ReferenceResult(master_style=master_style, palette=palette)


def _default_vision_caller_from_env() -> Callable[[bytes, str], Any]:
    """OpenAI-compatible vision caller. Resolves provider config in order:
        api_key   LLM_API_KEY  →  OPENROUTER_API_KEY
        base_url  LLM_BASE_URL →  OPENROUTER_BASE_URL
        model     LLM_VISION_MODEL  →  OPENROUTER_VISION_MODEL  →  LLM_TEXT_MODEL
    """

    import httpx  # local import to keep tests light

    api_key = (os.environ.get("LLM_API_KEY") or os.environ.get("OPENROUTER_API_KEY") or "").strip()
    if not api_key:
        raise ReferenceStyleError(
            "LLM API key is required. Set LLM_API_KEY (or legacy OPENROUTER_API_KEY)."
        )
    base_url = (
        os.environ.get("LLM_BASE_URL") or os.environ.get("OPENROUTER_BASE_URL") or ""
    ).strip()
    if not base_url:
        raise ReferenceStyleError(
            "LLM base URL is required. Set LLM_BASE_URL (or legacy OPENROUTER_BASE_URL)."
        )
    model = (
        os.environ.get("LLM_VISION_MODEL")
        or os.environ.get("OPENROUTER_VISION_MODEL")
        or os.environ.get("LLM_TEXT_MODEL")
        or ""
    ).strip()
    if not model:
        raise ReferenceStyleError(
            "LLM vision model is required. Set LLM_VISION_MODEL (or LLM_TEXT_MODEL)."
        )
    client = httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=httpx.Timeout(180.0, connect=20.0),
    )

    def call(image_bytes: bytes, prompt: str) -> Any:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        response = client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract master_style from a reference image.")
    parser.add_argument("--file", type=Path, required=True, help="Path to PNG/JPG/etc.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    parser.add_argument("--n-colors", type=int, default=6)
    args = parser.parse_args(argv)

    caller = _default_vision_caller_from_env()
    result = build_master_style(args.file, vision_caller=caller, n_colors=args.n_colors)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result.master_style, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {args.out}. palette={[c.hex for c in result.palette]} "
        f"source={result.master_style['source']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
