"""Aggregate per-page wireframes into a single review document for gate 5.

Reads a slide_prompts.json (or any list-of-page-intents JSON) and emits a single
HTML or Markdown file with each page's wireframe embedded inline plus its
status, pattern, and any warnings.

Usage:
    python scripts/preview_dashboard.py --intents-file artifacts/slide_prompts.json
        [--master-style artifacts/master_style.json]
        [--format html|markdown]
        [--out artifacts/preview_dashboard.html]
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import util as _importlib_util
from pathlib import Path
from typing import Iterable

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_HTML = SKILL_ROOT / "artifacts" / "preview_dashboard.html"
DEFAULT_OUT_MD = SKILL_ROOT / "artifacts" / "preview_dashboard.md"


def _load_local(name: str, rel_path: str):
    if name in sys.modules:
        return sys.modules[name]
    path = SKILL_ROOT / rel_path
    spec = _importlib_util.spec_from_file_location(name, path)
    module = _importlib_util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


wireframe_mod = _load_local("render_wireframe", "scripts/render_wireframe.py")


HTML_HEAD = """<!doctype html>
<html lang='en'>
<head>
<meta charset='utf-8'>
<title>Preview dashboard</title>
<style>
body { font-family: -apple-system, system-ui, "Segoe UI", "Helvetica Neue", sans-serif;
       margin: 24px; color: #1E1E1E; background: #FAFAFA; }
.page { background: #fff; border-radius: 12px; padding: 16px 20px;
        margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
.header { display: flex; align-items: center; gap: 16px; margin-bottom: 12px; }
.page-no { font-weight: 700; font-size: 22px; color: #6B7280; min-width: 36px; }
.title { font-size: 18px; font-weight: 600; }
.meta { color: #6B7280; font-size: 13px; margin-left: auto; }
.warnings { background: #FFF7ED; border-left: 3px solid #F59E0B; padding: 8px 12px;
            margin: 8px 0 12px 0; font-size: 13px; }
.warnings ul { margin: 4px 0 0 18px; padding: 0; }
.svg-wrap svg { max-width: 100%; height: auto; border: 1px solid #E5E7EB; border-radius: 8px; }
.empty { color: #999; font-style: italic; padding: 60px; text-align: center;
         border: 2px dashed #E5E7EB; border-radius: 8px; }
</style>
</head>
<body>
<h1>Preview Dashboard</h1>
"""

HTML_FOOT = "</body></html>\n"


def _render_one_page(page_intent: dict, master_style: dict | None) -> tuple[str, list]:
    result = wireframe_mod.render_wireframe(page_intent, master_style=master_style)
    return result.svg, result.warnings


def _format_html(pages: Iterable[dict], master_style: dict | None) -> str:
    chunks = [HTML_HEAD]
    for intent in pages:
        page_no = intent.get("page_no", "?")
        title = intent.get("title", "")
        pattern_id = intent.get("pattern_id", "—")
        intent_status = intent.get("intent_status", "draft")
        svg, warnings = _render_one_page(intent, master_style)
        chunks.append("<div class='page'>")
        chunks.append(
            f"<div class='header'>"
            f"<div class='page-no'>{page_no:>2}</div>"
            f"<div class='title'>{_escape(title)}</div>"
            f"<div class='meta'>pattern={_escape(pattern_id)} · "
            f"intent_status={_escape(intent_status)}</div>"
            f"</div>"
        )
        if warnings:
            chunks.append("<div class='warnings'><strong>warnings</strong><ul>")
            for w in warnings:
                chunks.append(f"<li>{_escape(w.slot)} · {_escape(w.rule)} — {_escape(w.detail)}</li>")
            chunks.append("</ul></div>")
        chunks.append("<div class='svg-wrap'>")
        chunks.append(svg or "<div class='empty'>(no wireframe — see warnings above)</div>")
        chunks.append("</div></div>")
    chunks.append(HTML_FOOT)
    return "".join(chunks)


def _format_markdown(pages: Iterable[dict], master_style: dict | None) -> str:
    lines: list[str] = ["# Preview Dashboard\n"]
    for intent in pages:
        page_no = intent.get("page_no", "?")
        title = intent.get("title", "")
        pattern_id = intent.get("pattern_id", "—")
        intent_status = intent.get("intent_status", "draft")
        svg, warnings = _render_one_page(intent, master_style)
        lines.append(f"\n## Page {page_no} — {title}\n")
        lines.append(f"`pattern={pattern_id}` · `intent_status={intent_status}`\n")
        if warnings:
            lines.append("\n**Warnings:**\n")
            for w in warnings:
                lines.append(f"- `{w.slot}` · `{w.rule}` — {w.detail}\n")
        lines.append("\n")
        lines.append(svg if svg else "_no wireframe — see warnings above_")
        lines.append("\n")
    return "".join(lines)


def _escape(text) -> str:
    text = str(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_dashboard(intents_file: Path, *, master_style: dict | None, output_format: str) -> str:
    payload = json.loads(intents_file.read_text(encoding="utf-8"))
    pages = payload.get("slides", payload) if isinstance(payload, dict) else payload
    if output_format == "html":
        return _format_html(pages, master_style)
    if output_format == "markdown":
        return _format_markdown(pages, master_style)
    raise ValueError(f"unknown format: {output_format!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Aggregate per-page wireframes into one document.")
    parser.add_argument("--intents-file", type=Path, required=True)
    parser.add_argument("--master-style", type=Path)
    parser.add_argument("--format", choices=("html", "markdown"), default="html")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    master_style = None
    if args.master_style:
        master_style = json.loads(args.master_style.read_text(encoding="utf-8"))

    body = build_dashboard(args.intents_file, master_style=master_style, output_format=args.format)
    out = args.out or (DEFAULT_OUT_HTML if args.format == "html" else DEFAULT_OUT_MD)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
