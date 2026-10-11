#!/usr/bin/env python3
"""Validate the first-batch project-delivery skill and template suite.

Stdlib only. This checks packaging metadata and source/template coverage; it does
not claim that a project artifact is semantically correct or customer-approved.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
TEMPLATES = SKILLS / "delivery-orchestrator" / "assets" / "templates"

EXPECTED = [
    "delivery-orchestrator",
    "delivery-source-intake",
    "delivery-contract-handover",
    "delivery-initiation-kickoff",
    "delivery-master-planning",
    "delivery-discovery-planning",
    "delivery-meeting-records",
    "delivery-requirements-baseline",
    "delivery-business-blueprint",
    "delivery-progress-control",
    "delivery-resource-timesheets",
    "delivery-cost-expenses",
    "delivery-risk-issue",
    "delivery-change-control",
    "delivery-reporting",
    "delivery-milestone-acceptance",
    "delivery-artifact-review",
]

FUTURE_SKILLS = {
    "delivery-solution-design",
    "delivery-ui-field-design",
    "delivery-integration-data",
    "delivery-work-package",
    "delivery-quality-testing",
    "delivery-go-live-transition",
    "delivery-training-handover",
    "delivery-progress-control-v2",
    "delivery-closure-warranty",
}

REQUIRED_META = ("template_id", "template_version", "visibility")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end < 0:
        return {}, text
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip().strip('"')
    return values, text[end + 4 :]


def validate_skills(errors: list[str]) -> None:
    found = sorted(path.parent.name for path in SKILLS.glob("*/SKILL.md"))
    if found != sorted(EXPECTED):
        fail(errors, f"skill roster mismatch: expected {len(EXPECTED)}, found {found}")

    for name in EXPECTED:
        folder = SKILLS / name
        skill_path = folder / "SKILL.md"
        yaml_path = folder / "agents" / "openai.yaml"
        if not skill_path.exists():
            fail(errors, f"missing {skill_path}")
            continue
        if not yaml_path.exists():
            fail(errors, f"missing {yaml_path}")
        meta, body = frontmatter(skill_path.read_text(encoding="utf-8"))
        if meta.get("name") != name:
            fail(errors, f"{skill_path}: frontmatter name must be {name}")
        if not meta.get("description"):
            fail(errors, f"{skill_path}: missing description")
        if len(body.strip()) < 500:
            fail(errors, f"{skill_path}: content is too thin for a substantive skill")
        contract = "references/artifact-contract.md" in body or "../delivery-orchestrator/references/artifact-contract.md" in body
        if not contract:
            fail(errors, f"{skill_path}: missing artifact-contract reference")
        for future in FUTURE_SKILLS:
            if future in skill_path.read_text(encoding="utf-8"):
                fail(errors, f"{skill_path}: unsupported future skill reference {future}")
        if yaml_path.exists():
            yaml = yaml_path.read_text(encoding="utf-8")
            for key in ("display_name:", "short_description:", "default_prompt:", "allow_implicit_invocation:"):
                if key not in yaml:
                    fail(errors, f"{yaml_path}: missing {key}")
            if f"${name}" not in yaml:
                fail(errors, f"{yaml_path}: default_prompt must invoke ${name}")

        # Any explicitly named template must resolve after sibling installation.
        text = skill_path.read_text(encoding="utf-8")
        for match in re.finditer(r"(?:\.\./delivery-orchestrator/)?assets/templates/([A-Za-z0-9_.-]+)", text):
            template = TEMPLATES / match.group(1)
            if not template.exists():
                fail(errors, f"{skill_path}: missing referenced template {match.group(1)}")


def validate_index(errors: list[str]) -> None:
    index_path = TEMPLATES / "index.json"
    if not index_path.exists():
        fail(errors, f"missing {index_path}")
        return
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        fail(errors, f"index JSON invalid: {exc}")
        return
    if index.get("version") != "0.1.0":
        fail(errors, "index version must be 0.1.0")
    entries = index.get("templates")
    if not isinstance(entries, list) or len(entries) < 20:
        fail(errors, "index must contain the first-batch template set")
        return
    seen: set[str] = set()
    for entry in entries:
        required = {"id", "title", "format", "path", "visibility", "skill"}
        missing = required - set(entry)
        if missing:
            fail(errors, f"index entry missing {sorted(missing)}: {entry}")
            continue
        if entry["id"] in seen:
            fail(errors, f"duplicate template id {entry['id']}")
        seen.add(entry["id"])
        if entry["format"] not in {"markdown", "csv"}:
            fail(errors, f"unsupported format {entry['format']}")
        if entry["visibility"] not in {"internal", "customer"}:
            fail(errors, f"unsupported visibility {entry['visibility']}")
        if not (TEMPLATES / entry["path"]).is_file():
            fail(errors, f"index path does not exist: {entry['path']}")
        if not any("\u4e00" <= char <= "\u9fff" for char in entry["title"]):
            fail(errors, f"template title should be Chinese: {entry['title']}")
        if entry["skill"] not in EXPECTED:
            fail(errors, f"index entry uses unsupported skill {entry['skill']}")


def validate_templates(errors: list[str]) -> None:
    for path in sorted(TEMPLATES.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta, _ = frontmatter(text)
        for key in REQUIRED_META:
            if key not in meta:
                fail(errors, f"{path}: missing {key}")
        if path.name != "template-field-guide.md" and len(text.splitlines()) < 15:
            fail(errors, f"{path}: missing meaningful sections")

    for path in sorted(TEMPLATES.glob("*.csv")):
        lines = path.read_text(encoding="utf-8").splitlines()
        if any(line.startswith("#") for line in lines):
            fail(errors, f"{path}: metadata must be machine-key columns so Office export reads the header")
        data_lines = [line for line in lines if line]
        if len(data_lines) != 2:
            fail(errors, f"{path}: expected header and one blank placeholder row")
            continue
        try:
            rows = list(csv.reader(data_lines))
        except csv.Error as exc:
            fail(errors, f"{path}: invalid CSV: {exc}")
            continue
        if not rows[0] or any(not field.strip() for field in rows[0]):
            fail(errors, f"{path}: headers must be non-empty machine keys")
        if not set(REQUIRED_META).issubset(rows[0]):
            fail(errors, f"{path}: header must include {REQUIRED_META}")
        if len(rows[0]) != len(rows[1]) or any(field.strip() for field in rows[1]):
            fail(errors, f"{path}: placeholder row must have one blank cell per header")


def validate() -> list[str]:
    errors: list[str] = []
    validate_skills(errors)
    validate_index(errors)
    validate_templates(errors)
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("FAIL")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"PASS: {len(EXPECTED)} skills and {len(json.loads((TEMPLATES / 'index.json').read_text())['templates'])} templates validated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
