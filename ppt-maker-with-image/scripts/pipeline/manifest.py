from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_MANIFEST_NAME = "manifest.json"
STAGE_ARTIFACTS: dict[str, str] = {
    "master_style": "master_style.json",
    "outline": "outline.json",
    "page_intent": "page_intent.json",
    "slide_prompts": "slide_prompts.json",
    "render": "images",
    "assemble": "deck.pptx",
}


def manifest_path(path: str | Path, *, filename: str = DEFAULT_MANIFEST_NAME) -> Path:
    base = Path(path).expanduser()
    if base.suffix.lower() == ".json":
        return base.resolve()
    return (base / filename).resolve()


def load_manifest(path: str | Path) -> dict[str, Any]:
    resolved = manifest_path(path)
    if not resolved.exists():
        return {"provider_capabilities": {}}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload.setdefault("provider_capabilities", {})
    return payload


def write_manifest(path: str | Path, manifest: Mapping[str, Any]) -> Path:
    resolved = manifest_path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(json.dumps(dict(manifest), ensure_ascii=False, indent=2), encoding="utf-8")
    return resolved
