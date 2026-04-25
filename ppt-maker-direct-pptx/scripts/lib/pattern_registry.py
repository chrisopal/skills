"""Pattern library loader + slot validator.

A PatternRegistry instance loads every `<pattern_id>.json` file in the patterns
directory, validates each against `pattern.schema.json`, and exposes lookup +
slot validation helpers used by downstream phases (intent generation, lint,
wireframe rendering, JS rendering).

`*.sample.json` files (used by the Phase 4 catalog renderer) are intentionally
ignored at load time — they hold lorem-ipsum slot values, not pattern defs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from jsonschema import Draft202012Validator, ValidationError


SKILL_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = SKILL_ROOT / "assets" / "schemas" / "pattern.schema.json"


class PatternSchemaError(ValueError):
    """Raised when a pattern file does not match pattern.schema.json."""

    def __init__(self, path: Path, errors: list[ValidationError]):
        self.path = path
        self.errors = errors
        joined = "; ".join(f"{list(e.path)}: {e.message}" for e in errors)
        super().__init__(f"{path.name} failed pattern schema: {joined}")


@dataclass(frozen=True)
class Slot:
    name: str
    required: bool
    max_chars: int | None = None
    min_chars: int | None = None
    accepts_image: bool = False


@dataclass(frozen=True)
class Pattern:
    pattern_id: str
    slots: tuple[Slot, ...]
    layout_regions: dict
    style_hooks: dict = field(default_factory=dict)
    wireframe_template: str = ""
    js_renderer: str = ""
    description: str = ""

    def slot_names(self) -> set[str]:
        return {s.name for s in self.slots}

    def required_slot_names(self) -> set[str]:
        return {s.name for s in self.slots if s.required}


@dataclass(frozen=True)
class SlotValidationError:
    slot: str
    rule: str  # "missing_required" | "max_chars" | "min_chars" | "unknown_slot"
    detail: str


def _build_pattern(data: dict) -> Pattern:
    return Pattern(
        pattern_id=data["pattern_id"],
        slots=tuple(
            Slot(
                name=s["name"],
                required=s["required"],
                max_chars=s.get("max_chars"),
                min_chars=s.get("min_chars"),
                accepts_image=s.get("accepts_image", False),
            )
            for s in data["slots"]
        ),
        layout_regions=data["layout_regions"],
        style_hooks=data.get("style_hooks", {}),
        wireframe_template=data["wireframe_template"],
        js_renderer=data["js_renderer"],
        description=data.get("description", ""),
    )


class PatternRegistry:
    def __init__(self, patterns_dir: Path, schema_path: Path = DEFAULT_SCHEMA_PATH):
        if not patterns_dir.is_dir():
            raise NotADirectoryError(f"Not a patterns directory: {patterns_dir}")
        self._patterns_dir = patterns_dir
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        self._validator = Draft202012Validator(schema)
        self._patterns: dict[str, Pattern] = {}
        self._load()

    def _load(self) -> None:
        for path in sorted(self._patterns_dir.glob("*.json")):
            if path.name.endswith(".sample.json"):
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            errors = sorted(self._validator.iter_errors(data), key=lambda e: list(e.path))
            if errors:
                raise PatternSchemaError(path, errors)
            pattern = _build_pattern(data)
            if pattern.pattern_id != path.stem:
                raise PatternSchemaError(
                    path,
                    [ValidationError(
                        f"pattern_id '{pattern.pattern_id}' does not match filename stem '{path.stem}'"
                    )],
                )
            if pattern.pattern_id in self._patterns:
                raise PatternSchemaError(
                    path,
                    [ValidationError(f"duplicate pattern_id '{pattern.pattern_id}'")],
                )
            self._patterns[pattern.pattern_id] = pattern

    def list_ids(self) -> list[str]:
        return sorted(self._patterns.keys())

    def get(self, pattern_id: str) -> Pattern:
        try:
            return self._patterns[pattern_id]
        except KeyError as exc:
            raise KeyError(f"Unknown pattern_id: {pattern_id!r}") from exc

    def __contains__(self, pattern_id: str) -> bool:
        return pattern_id in self._patterns

    def __len__(self) -> int:
        return len(self._patterns)

    def validate_slots(self, pattern_id: str, slots: dict) -> list[SlotValidationError]:
        pattern = self.get(pattern_id)
        errors: list[SlotValidationError] = []
        provided = set(slots.keys())

        for slot in pattern.slots:
            value = slots.get(slot.name)
            if value is None or value == "":
                if slot.required:
                    errors.append(SlotValidationError(
                        slot=slot.name,
                        rule="missing_required",
                        detail=f"required slot '{slot.name}' is missing or empty",
                    ))
                continue
            if isinstance(value, str):
                length = len(value)
                if slot.max_chars is not None and length > slot.max_chars:
                    errors.append(SlotValidationError(
                        slot=slot.name,
                        rule="max_chars",
                        detail=f"slot '{slot.name}' is {length} chars, exceeds max_chars={slot.max_chars}",
                    ))
                if slot.min_chars is not None and length < slot.min_chars:
                    errors.append(SlotValidationError(
                        slot=slot.name,
                        rule="min_chars",
                        detail=f"slot '{slot.name}' is {length} chars, below min_chars={slot.min_chars}",
                    ))

        unknown = provided - pattern.slot_names()
        for name in sorted(unknown):
            errors.append(SlotValidationError(
                slot=name,
                rule="unknown_slot",
                detail=f"slot '{name}' is not declared by pattern '{pattern_id}'",
            ))

        return errors
