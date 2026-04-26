"""Preset-inheritance helper for the master_style system.

Given a preset id (e.g. "huixin", "dark-english-business") and a set of
override paths (e.g. {"color_strategy.primary_green": "#1A237E"}), this module
loads the preset brief, applies the overrides, records provenance fields
(source / parent_template_id / lock_fields), and returns a master_style dict
suitable for downstream phases.

Lock semantics: when the preset declares lock_fields and the user attempts to
override one of them, LockedFieldError is raised before any merging happens.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Iterable

SKILL_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = SKILL_ROOT / "assets"
DEFAULT_MANIFEST_PATH = ASSETS_DIR / "template_manifest.json"


class UnknownPresetError(KeyError):
    """Raised when the requested preset id / alias is not in the manifest."""


class LockedFieldError(ValueError):
    """Raised when an override targets a field declared in lock_fields."""


def _load_manifest(manifest_path: Path) -> dict:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def _resolve_preset(manifest: dict, preset_id_or_alias: str) -> dict:
    needle = preset_id_or_alias.strip()
    for entry in manifest.get("templates", []):
        if entry["template_id"] == needle:
            return entry
        if needle in entry.get("aliases", []):
            return entry
    raise UnknownPresetError(f"Unknown preset id or alias: {preset_id_or_alias!r}")


def _split_path(dotted: str) -> list[str]:
    if not dotted:
        raise ValueError("override path must be non-empty")
    return dotted.split(".")


def _set_path(target: dict, parts: list[str], value: Any) -> None:
    cursor = target
    for key in parts[:-1]:
        nxt = cursor.get(key)
        if not isinstance(nxt, dict):
            nxt = {}
            cursor[key] = nxt
        cursor = nxt
    cursor[parts[-1]] = value


def _path_starts_with(path: list[str], prefix: list[str]) -> bool:
    if len(path) < len(prefix):
        return False
    return path[: len(prefix)] == prefix


def inherit_preset(
    preset_id: str,
    overrides: dict[str, Any] | None = None,
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    assets_dir: Path = ASSETS_DIR,
) -> dict:
    """Load `preset_id`, apply `overrides`, return a fresh master_style dict.

    Parameters
    ----------
    preset_id:
        Preset template_id or one of its registered aliases.
    overrides:
        Mapping from dotted field path -> value. Empty / None means a pure
        preset copy.
    """

    manifest = _load_manifest(manifest_path)
    entry = _resolve_preset(manifest, preset_id)
    brief_path = assets_dir / entry["brief_asset"]
    master_style = json.loads(brief_path.read_text(encoding="utf-8"))

    overrides = overrides or {}
    lock_fields = master_style.get("lock_fields", []) or []
    locked_paths = [_split_path(p) for p in lock_fields]

    if overrides:
        for raw_path in overrides:
            parts = _split_path(raw_path)
            for locked in locked_paths:
                if _path_starts_with(parts, locked):
                    raise LockedFieldError(
                        f"Cannot override locked field {raw_path!r}"
                        f" (locked via {'.'.join(locked)})"
                    )
        result = copy.deepcopy(master_style)
        for raw_path, value in overrides.items():
            _set_path(result, _split_path(raw_path), value)
        result["source"] = "hybrid"
        result["parent_template_id"] = entry["template_id"]
    else:
        result = copy.deepcopy(master_style)
        result["source"] = "preset"
        result["parent_template_id"] = None

    return result


def list_preset_ids(manifest_path: Path = DEFAULT_MANIFEST_PATH) -> list[str]:
    return [t["template_id"] for t in _load_manifest(manifest_path).get("templates", [])]
