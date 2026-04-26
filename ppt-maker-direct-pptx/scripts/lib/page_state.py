"""Page-level state machine driving the gate workflow.

Three independent layers per page (per design §5):

    outline_status   -- {draft, pending_review, locked, needs_rework}
    intent_status    -- same set; only allowed to advance once outline_status
                        has reached `locked`
    image_status     -- aggregate of every image_placeholder.status on the page
                        {no_image, placeholder_only, partially_generated,
                         fully_generated, has_failures}

Legal transitions (per layer):

    draft        -> pending_review
    pending_review -> locked
    pending_review -> needs_rework
    needs_rework -> pending_review
    locked       -> needs_rework
    locked       -> pending_review (when user manually re-opens)

This module persists status changes back into the underlying artifact JSON
(outline.json / slide_prompts.json / slide_specs.json) and keeps a per-page
history list so dashboards and audit trails can show provenance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

LAYERS = ("outline_status", "intent_status", "image_status")
PAGE_STATES = ("draft", "pending_review", "locked", "needs_rework")
IMAGE_STATUS_VALUES = (
    "no_image",
    "placeholder_only",
    "partially_generated",
    "fully_generated",
    "has_failures",
)
IMAGE_PLACEHOLDER_STATES = ("pending", "placeholder", "generated", "skipped", "regenerating")

_LEGAL_TRANSITIONS = {
    ("draft", "pending_review"),
    ("pending_review", "locked"),
    ("pending_review", "needs_rework"),
    ("needs_rework", "pending_review"),
    ("locked", "needs_rework"),
    ("locked", "pending_review"),
}


class IllegalTransitionError(ValueError):
    pass


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class PageStateMachine:
    """Mutate page-status fields on the three artifact dicts in place.

    All three artifact dicts are optional but at least one must be supplied:
    the layer corresponding to a missing artifact will be reported as
    `unknown` (not fixable through this state machine).
    """

    outline: dict | None = None
    slide_prompts: dict | None = None
    slide_specs: dict | None = None
    history: dict[int, list[dict]] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def can_transition(self, current: str | None, to_state: str) -> bool:
        if current is None:
            current = "draft"
        if current == to_state:
            return True
        if to_state not in PAGE_STATES:
            return False
        return (current, to_state) in _LEGAL_TRANSITIONS

    def transition(self, page_no: int, layer: str, to_state: str, reason: str = "") -> bool:
        if layer not in ("outline_status", "intent_status"):
            raise IllegalTransitionError(
                f"only outline_status and intent_status are user-mutable; got {layer!r}"
            )
        if to_state not in PAGE_STATES:
            raise IllegalTransitionError(f"unknown page state {to_state!r}")
        slide = self._slide_for(layer, page_no)
        if slide is None:
            raise IllegalTransitionError(
                f"no slide page_no={page_no} found in artifact for layer {layer!r}"
            )
        if layer == "intent_status":
            outline_state = self._read_outline_status(page_no)
            if outline_state != "locked" and to_state in {"pending_review", "locked"}:
                raise IllegalTransitionError(
                    f"intent_status -> {to_state!r} requires outline_status==locked "
                    f"(currently {outline_state!r}) on page {page_no}"
                )
        current = slide.get(layer, "draft")
        if not self.can_transition(current, to_state):
            raise IllegalTransitionError(
                f"page {page_no}: illegal {layer} transition {current!r} -> {to_state!r}"
            )
        if current == to_state:
            return False
        slide[layer] = to_state
        self.history.setdefault(page_no, []).append({
            "ts": _now_iso(),
            "layer": layer,
            "from": current,
            "to": to_state,
            "reason": reason,
        })
        return True

    def aggregate_image_status(self, page_no: int) -> str:
        if self.slide_specs is None:
            return "no_image"
        for slide in self.slide_specs.get("slides", []):
            if slide.get("page_no") != page_no:
                continue
            placeholders = slide.get("image_placeholders") or []
            if not placeholders:
                return "no_image"
            statuses = [p.get("status", "placeholder") for p in placeholders]
            if all(s == "skipped" for s in statuses):
                return "no_image"
            if "regenerating" in statuses or any(
                p.get("fallback_reason") for p in placeholders
            ):
                return "has_failures"
            generated = sum(1 for s in statuses if s == "generated")
            real_slots = sum(1 for s in statuses if s != "skipped")
            if real_slots == 0:
                return "no_image"
            if generated == real_slots:
                return "fully_generated"
            if generated > 0:
                return "partially_generated"
            return "placeholder_only"
        return "no_image"

    def status_for(self, page_no: int) -> dict:
        return {
            "outline_status": self._read_outline_status(page_no),
            "intent_status": self._read_intent_status(page_no),
            "image_status": self.aggregate_image_status(page_no),
        }

    def page_numbers(self) -> list[int]:
        seen: set[int] = set()
        for source in (self.outline, self.slide_prompts, self.slide_specs):
            if not source:
                continue
            for slide in source.get("slides", []):
                page_no = slide.get("page_no")
                if isinstance(page_no, int):
                    seen.add(page_no)
        return sorted(seen)

    def history_for(self, page_no: int) -> list[dict]:
        return list(self.history.get(page_no, []))

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _slide_for(self, layer: str, page_no: int) -> dict | None:
        source = (
            self.outline if layer == "outline_status"
            else self.slide_prompts if layer == "intent_status"
            else None
        )
        if source is None:
            return None
        for slide in source.get("slides", []):
            if slide.get("page_no") == page_no:
                return slide
        return None

    def _read_outline_status(self, page_no: int) -> str:
        slide = self._slide_for("outline_status", page_no)
        if slide is None:
            return "unknown"
        return slide.get("outline_status", "draft")

    def _read_intent_status(self, page_no: int) -> str:
        slide = self._slide_for("intent_status", page_no)
        if slide is None:
            return "unknown"
        return slide.get("intent_status", "draft")


def load_machine(
    *,
    outline_path: Path | None = None,
    slide_prompts_path: Path | None = None,
    slide_specs_path: Path | None = None,
) -> PageStateMachine:
    def _read(path: Path | None) -> dict | None:
        if path is None or not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    return PageStateMachine(
        outline=_read(outline_path),
        slide_prompts=_read(slide_prompts_path),
        slide_specs=_read(slide_specs_path),
    )


def persist_machine(
    machine: PageStateMachine,
    *,
    outline_path: Path | None = None,
    slide_prompts_path: Path | None = None,
) -> int:
    written = 0
    if machine.outline is not None and outline_path is not None:
        outline_path.write_text(
            json.dumps(machine.outline, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written += 1
    if machine.slide_prompts is not None and slide_prompts_path is not None:
        slide_prompts_path.write_text(
            json.dumps(machine.slide_prompts, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        written += 1
    return written
