#!/usr/bin/env python3
"""Validate intake, evidence, and draft gates for a WeChat article case bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PHASES = ("intake", "evidence", "draft")


def load_bundle(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"cannot read bundle: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("bundle root must be a JSON object")
    return payload


def is_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def require_text(container: Any, key: str, path: str, errors: list[str]) -> None:
    if not isinstance(container, dict) or not is_text(container.get(key)):
        errors.append(f"{path}.{key} must be a non-empty string")


def require_nonempty_list(container: Any, key: str, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(container, dict) or not isinstance(container.get(key), list) or not container[key]:
        errors.append(f"{path}.{key} must be a non-empty list")
        return []
    return container[key]


def require_existing_file(value: Any, path: str, errors: list[str]) -> None:
    if not is_text(value):
        errors.append(f"{path} must be a non-empty file path")
        return
    if not Path(value).expanduser().is_file():
        errors.append(f"{path} does not exist: {value}")


def validate_intake(bundle: dict[str, Any], errors: list[str]) -> None:
    if bundle.get("schema_version") != "1.0":
        errors.append("schema_version must be 1.0")
    require_text(bundle, "topic_id", "bundle", errors)

    request = bundle.get("request")
    if not isinstance(request, dict):
        errors.append("request must be an object")
        request = {}
    for key in ("objective", "target_reader", "reader_action", "core_claim"):
        require_text(request, key, "request", errors)

    logic = bundle.get("logic")
    if not isinstance(logic, dict):
        errors.append("logic must be an object")
        logic = {}
    for key in ("methodology", "storyline"):
        values = require_nonempty_list(logic, key, "logic", errors)
        for index, value in enumerate(values):
            if not is_text(value):
                errors.append(f"logic.{key}[{index}] must be a non-empty string")

    scenario = bundle.get("scenario")
    if not isinstance(scenario, dict):
        errors.append("scenario must be an object")
        scenario = {}
    require_text(scenario, "name", "scenario", errors)
    require_text(scenario, "environment", "scenario", errors)
    if scenario.get("actual") is not True:
        errors.append("scenario.actual must be true")

    steps = require_nonempty_list(scenario, "steps", "scenario", errors)
    for index, step in enumerate(steps):
        require_text(step, "id", f"scenario.steps[{index}]", errors)
        require_text(step, "action", f"scenario.steps[{index}]", errors)

    acceptance = require_nonempty_list(scenario, "acceptance_criteria", "scenario", errors)
    for index, item in enumerate(acceptance):
        require_text(item, "id", f"scenario.acceptance_criteria[{index}]", errors)
        require_text(item, "criterion", f"scenario.acceptance_criteria[{index}]", errors)

    materials = bundle.get("materials")
    if not isinstance(materials, list) or not materials:
        errors.append("materials must be a non-empty list")
    else:
        for index, material in enumerate(materials):
            path = f"materials[{index}]"
            require_text(material, "id", path, errors)
            require_text(material, "kind", path, errors)
            require_text(material, "path_or_url", path, errors)
            require_text(material, "status", path, errors)

    wechat = bundle.get("wechat")
    if not isinstance(wechat, dict):
        errors.append("wechat must be an object")
        wechat = {}
    if wechat.get("save_mode") != "draft":
        errors.append("wechat.save_mode must be draft")
    if wechat.get("publish") is not False:
        errors.append("wechat.publish must be false")


def validate_evidence(bundle: dict[str, Any], errors: list[str]) -> None:
    validate_intake(bundle, errors)

    materials = bundle.get("materials", [])
    verified_materials = [
        item
        for item in materials
        if isinstance(item, dict) and item.get("status") == "verified"
    ] if isinstance(materials, list) else []
    if len(verified_materials) < 5:
        errors.append("evidence phase requires at least five verified materials")

    evidence = bundle.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("evidence must be an object")
        evidence = {}
    items = require_nonempty_list(evidence, "items", "evidence", errors)

    evidence_ids: set[str] = set()
    kinds: set[str] = set()
    for index, item in enumerate(items):
        path = f"evidence.items[{index}]"
        require_text(item, "id", path, errors)
        require_text(item, "kind", path, errors)
        evidence_id = item.get("id") if isinstance(item, dict) else None
        kind = item.get("kind") if isinstance(item, dict) else None
        if is_text(evidence_id):
            if evidence_id in evidence_ids:
                errors.append(f"{path}.id must be unique: {evidence_id}")
            evidence_ids.add(evidence_id)
        if is_text(kind):
            kinds.add(kind)
        if not isinstance(item, dict) or item.get("verified") is not True:
            errors.append(f"{path}.verified must be true")
        require_existing_file(item.get("path") if isinstance(item, dict) else None, f"{path}.path", errors)
        if kind == "screenshot":
            if item.get("privacy_checked") is not True:
                errors.append(f"{path}.privacy_checked must be true")
            if item.get("error_checked") is not True:
                errors.append(f"{path}.error_checked must be true")

    if "screenshot" not in kinds:
        errors.append("evidence.items must include at least one screenshot")
    if not kinds.intersection({"artifact", "readback"}):
        errors.append("evidence.items must include at least one artifact or readback")

    scenario = bundle.get("scenario", {})
    for collection_name in ("steps", "acceptance_criteria"):
        collection = scenario.get(collection_name, []) if isinstance(scenario, dict) else []
        for index, item in enumerate(collection):
            path = f"scenario.{collection_name}[{index}]"
            if not isinstance(item, dict) or item.get("status") != "passed":
                errors.append(f"{path}.status must be passed")
            refs = item.get("evidence_ids") if isinstance(item, dict) else None
            if not isinstance(refs, list) or not refs:
                errors.append(f"{path}.evidence_ids must be a non-empty list")
                continue
            for evidence_id in refs:
                if evidence_id not in evidence_ids:
                    errors.append(f"{path}.evidence_ids references unknown evidence: {evidence_id}")


def validate_draft(bundle: dict[str, Any], errors: list[str]) -> None:
    validate_evidence(bundle, errors)

    article = bundle.get("article")
    if not isinstance(article, dict):
        errors.append("article must be an object")
        article = {}
    for key in ("markdown_path", "html_path", "cover_path"):
        require_existing_file(article.get(key), f"article.{key}", errors)
    inline_paths = article.get("inline_image_paths")
    if not isinstance(inline_paths, list):
        errors.append("article.inline_image_paths must be a list")
    else:
        for index, path in enumerate(inline_paths):
            require_existing_file(path, f"article.inline_image_paths[{index}]", errors)
    if article.get("review_status") != "passed":
        errors.append("article.review_status must be passed")
    for key in ("markdown_link_residue", "local_path_residue", "privacy_residue", "error_residue"):
        if article.get(key) is not False:
            errors.append(f"article.{key} must be false")

    wechat = bundle.get("wechat")
    if not isinstance(wechat, dict):
        return
    if wechat.get("ip_whitelist_checked") is not True:
        errors.append("wechat.ip_whitelist_checked must be true")
    require_text(wechat, "media_id", "wechat", errors)
    require_existing_file(wechat.get("draft_get_path"), "wechat.draft_get_path", errors)
    if wechat.get("draft_get_verified") is not True:
        errors.append("wechat.draft_get_verified must be true")
    if wechat.get("status") != "DRAFT_SAVED":
        errors.append("wechat.status must be DRAFT_SAVED")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path, help="Path to the case-bundle JSON file")
    parser.add_argument("--phase", choices=PHASES, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        bundle = load_bundle(args.bundle)
    except ValueError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2

    errors: list[str] = []
    if args.phase == "intake":
        validate_intake(bundle, errors)
    elif args.phase == "evidence":
        validate_evidence(bundle, errors)
    else:
        validate_draft(bundle, errors)

    if errors:
        for error in errors:
            print(f"VALIDATION ERROR: {error}", file=sys.stderr)
        return 1
    print(f"VALIDATION PASSED: {args.phase}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
