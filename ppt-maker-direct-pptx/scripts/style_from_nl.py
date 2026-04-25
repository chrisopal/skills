"""Generate a master_style.json from a natural-language description.

The script accepts a free-text description ("深蓝紫色赛博朋克科技风"), prompts a
text model to return a JSON object matching master_style.schema.json, validates
the result, and retries up to 3 times with structured feedback on failure.

Usage:
    python scripts/style_from_nl.py --description "..." [--out artifacts/master_style.json]

For tests, pass a callable `model_caller(prompt: str) -> dict` to
`generate_style_from_nl` instead of relying on the OpenRouter client.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Any

from jsonschema import Draft202012Validator, ValidationError

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "master_style.schema.json"

DEFAULT_OUT_PATH = SKILL_ROOT / "artifacts" / "master_style.json"
MAX_RETRIES = 3


class StyleGenerationError(RuntimeError):
    pass


@dataclass
class GenerationResult:
    master_style: dict
    attempts: int


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _build_prompt(description: str, *, prior_errors: list[ValidationError] | None = None) -> str:
    schema = _load_schema()
    base = (
        "You are a presentation design director.\n"
        "Generate a complete master_style JSON document for the deck described below.\n\n"
        f"Description:\n{description}\n\n"
        "Return ONE JSON object matching this JSON Schema (Draft 2020-12):\n"
        f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
        "Hard requirements:\n"
        "- Set source to \"nl_generated\".\n"
        "- Set parent_template_id to null.\n"
        "- Populate template_id, template_name, language, color_strategy, "
        "typography, and prompt_block.\n"
        "- color_strategy values must be 6-digit hex codes.\n"
        "- Provide a confidence object: dotted-path -> number in [0, 1].\n"
        "- Lower confidence on fields you are unsure about.\n"
        "- Do not include any field not allowed by the schema.\n"
        "Output JSON only."
    )
    if prior_errors:
        bullets = "\n".join(
            f"- {list(e.path)}: {e.message}" for e in prior_errors[:8]
        )
        base += (
            "\n\nThe previous response failed schema validation with these errors:\n"
            f"{bullets}\nFix all of them in the next response."
        )
    return base


def generate_style_from_nl(
    description: str,
    *,
    model_caller: Callable[[str], Any],
    max_retries: int = MAX_RETRIES,
) -> GenerationResult:
    if not description or not description.strip():
        raise ValueError("description must be a non-empty string")

    schema = _load_schema()
    validator = Draft202012Validator(schema)
    last_errors: list[ValidationError] = []

    for attempt in range(1, max_retries + 1):
        prompt = _build_prompt(description, prior_errors=last_errors)
        raw = model_caller(prompt)
        if not isinstance(raw, dict):
            last_errors = [ValidationError("model returned non-object")]
            continue
        errors = sorted(validator.iter_errors(raw), key=lambda e: list(e.path))
        if not errors:
            return GenerationResult(master_style=raw, attempts=attempt)
        last_errors = errors

    raise StyleGenerationError(
        f"NL style generation failed after {max_retries} attempts. "
        "Last errors: " + "; ".join(
            f"{list(e.path)}: {e.message}" for e in last_errors[:5]
        )
    )


def _default_caller_from_env() -> Callable[[str], Any]:
    """Build the production OpenRouter-backed caller. Imported lazily."""

    import httpx

    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise StyleGenerationError(
            "OPENROUTER_API_KEY is required for live NL style generation."
        )
    base_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.environ.get("OPENROUTER_TEXT_MODEL", "anthropic/claude-3.5-sonnet")
    client = httpx.Client(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=httpx.Timeout(120.0, connect=20.0),
    )

    def call(prompt: str) -> Any:
        if "json" not in prompt.lower():
            prompt = f"{prompt}\n\nReturn valid JSON only."
        response = client.post(
            "/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
            },
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)

    return call


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate master_style.json from NL.")
    parser.add_argument("--description", required=True, help="Free-text style description")
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help=f"Where to write master_style.json (default {DEFAULT_OUT_PATH})",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=MAX_RETRIES,
        help="Maximum schema-retry rounds (default %(default)s)",
    )
    args = parser.parse_args(argv)

    caller = _default_caller_from_env()
    result = generate_style_from_nl(
        args.description,
        model_caller=caller,
        max_retries=args.max_retries,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(result.master_style, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {args.out} after {result.attempts} attempt(s). "
        f"source={result.master_style.get('source')}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
