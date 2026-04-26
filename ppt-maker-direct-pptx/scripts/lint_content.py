"""Content quality lint pass.

Two deterministic checks plus one optional LLM judge:

  1. (deterministic) every slide must declare a non-empty core_message
  2. (deterministic) cross-page duplicate detection — pages with core_message
     similarity > 0.8 are flagged so the user can de-duplicate
  3. (optional) audience fit — one LLM call per slide rates 0..1; scores below
     a threshold (default 0.6) emit a warn-class result

The LLM call is wrapped behind an injectable `model_caller(prompt) -> dict`
so tests stay offline. Pass `--skip-content-judge` (or omit caller) to skip
step 3 entirely.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Callable

SKILL_ROOT = Path(__file__).resolve().parent.parent

DUPLICATE_THRESHOLD = 0.8
AUDIENCE_FIT_THRESHOLD = 0.6


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / rel_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


lint_common = _load_local("lint_common", "scripts/lib/lint_common.py")


def _check_core_message_present(slides: list[dict]) -> list:
    out = []
    for slide in slides:
        core = (slide.get("core_message") or "").strip()
        if not core:
            out.append(lint_common.LintResult(
                category="content_quality",
                rule="missing_core_message",
                severity="fail",
                detail="slide is missing core_message",
                page_no=slide.get("page_no"),
                auto_fixable=False,
            ))
    return out


def _check_duplicate_core_messages(slides: list[dict], *, threshold: float = DUPLICATE_THRESHOLD) -> list:
    out = []
    cores: list[tuple[int, str]] = [
        (s.get("page_no"), (s.get("core_message") or "").strip())
        for s in slides
    ]
    cores = [(p, c) for p, c in cores if c]
    seen = set()
    for i in range(len(cores)):
        for j in range(i + 1, len(cores)):
            page_a, core_a = cores[i]
            page_b, core_b = cores[j]
            ratio = SequenceMatcher(None, core_a, core_b).ratio()
            if ratio > threshold and (page_a, page_b) not in seen:
                out.append(lint_common.LintResult(
                    category="content_quality",
                    rule="duplicate_core_message",
                    severity="warn",
                    detail=(
                        f"page {page_a} and page {page_b} have similar core_message "
                        f"(ratio={ratio:.2f})"
                    ),
                    page_no=page_a,
                    auto_fixable=False,
                ))
                seen.add((page_a, page_b))
    return out


def _judge_audience_fit(
    slide: dict,
    audience: str | None,
    *,
    model_caller: Callable[[str], Any],
    threshold: float,
) -> list:
    if not audience:
        return []
    prompt = (
        "You are a presentation editor. Rate from 0 to 1 how well the following "
        "slide fits the stated audience. Reply with one JSON object: "
        "{\"score\": <0..1>, \"reason\": \"<short reason>\"}.\n\n"
        f"Audience: {audience}\n\n"
        f"Slide page_no: {slide.get('page_no')}\n"
        f"Slide title: {slide.get('title')}\n"
        f"Core message: {slide.get('core_message')}\n"
        f"Speaker notes: {slide.get('speaker_notes', '')}\n"
    )
    raw = model_caller(prompt)
    if not isinstance(raw, dict):
        return [lint_common.LintResult(
            category="content_quality",
            rule="audience_judge_unavailable",
            severity="warn",
            detail="model returned non-object response",
            page_no=slide.get("page_no"),
        )]
    score = raw.get("score")
    reason = raw.get("reason", "")
    if not isinstance(score, (int, float)):
        return [lint_common.LintResult(
            category="content_quality",
            rule="audience_judge_unavailable",
            severity="warn",
            detail=f"model returned non-numeric score: {raw!r}",
            page_no=slide.get("page_no"),
        )]
    if score < threshold:
        return [lint_common.LintResult(
            category="content_quality",
            rule="audience_fit_low",
            severity="warn",
            detail=f"audience fit score={score:.2f} (<{threshold}) — {reason}",
            page_no=slide.get("page_no"),
        )]
    return []


def lint_content(
    slide_prompts: dict,
    *,
    audience: str | None = None,
    model_caller: Callable[[str], Any] | None = None,
    duplicate_threshold: float = DUPLICATE_THRESHOLD,
    audience_threshold: float = AUDIENCE_FIT_THRESHOLD,
) -> list:
    slides = slide_prompts.get("slides", [])
    out: list = []
    out.extend(_check_core_message_present(slides))
    out.extend(_check_duplicate_core_messages(slides, threshold=duplicate_threshold))
    if model_caller is not None:
        for slide in slides:
            if not (slide.get("core_message") or "").strip():
                continue
            out.extend(_judge_audience_fit(
                slide, audience, model_caller=model_caller, threshold=audience_threshold,
            ))
    return out


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM-augmented content quality lint.")
    parser.add_argument("--slide-prompts", required=True, type=Path)
    parser.add_argument("--audience", type=str, help="Audience description for fit judge")
    parser.add_argument("--skip-content-judge", action="store_true",
                        help="Skip the LLM audience-fit pass")
    args = parser.parse_args(argv)
    caller = None
    if not args.skip_content_judge and args.audience:
        from scripts.style_from_nl import _default_caller_from_env  # type: ignore
        caller = _default_caller_from_env()
    results = lint_content(_read(args.slide_prompts), audience=args.audience, model_caller=caller)
    fails = [r for r in results if r.severity == "fail"]
    print(json.dumps({
        "results": [r.to_result_dict() for r in results],
        "summary": {
            "fail": len(fails),
            "warn": sum(r.severity == "warn" for r in results),
        },
    }, ensure_ascii=False, indent=2))
    return 0 if not fails else 2


if __name__ == "__main__":
    sys.exit(main())
