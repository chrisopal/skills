"""Shared types for the lint pipeline.

Every individual lint script (schema/geometry/style/content) returns a list of
LintResult instances. The orchestrator merges them into the lint_report.json
shape defined by `assets/schemas/lint_report.schema.json`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional

CATEGORY_VALUES = {"schema", "layout_geometry", "style_consistency", "content_quality"}
SEVERITY_VALUES = {"pass", "warn", "fail"}


@dataclass(frozen=True)
class LintResult:
    category: str
    rule: str
    severity: str
    detail: str = ""
    page_no: Optional[int] = None
    auto_fixable: bool = False

    def __post_init__(self):
        if self.category not in CATEGORY_VALUES:
            raise ValueError(f"unknown category: {self.category}")
        if self.severity not in SEVERITY_VALUES:
            raise ValueError(f"unknown severity: {self.severity}")

    def to_result_dict(self) -> dict:
        d = {
            "category": self.category,
            "rule": self.rule,
            "severity": self.severity,
        }
        if self.page_no is not None:
            d["page_no"] = self.page_no
        if self.detail:
            d["detail"] = self.detail
        d["auto_fixable"] = self.auto_fixable
        return d

    def to_deck_dict(self) -> dict:
        d = {
            "category": self.category,
            "rule": self.rule,
            "severity": self.severity,
        }
        if self.detail:
            d["detail"] = self.detail
        return d


def split_results(results: list[LintResult]) -> tuple[list[LintResult], list[LintResult]]:
    """Partition into per-page (page_no set) and deck-level (page_no None) buckets."""

    per_page = [r for r in results if r.page_no is not None]
    deck = [r for r in results if r.page_no is None]
    return per_page, deck
