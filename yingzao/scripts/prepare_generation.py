#!/usr/bin/env python3
"""Compile and validate the exact three-image handoff for an ImageGen edit call."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _runtime import ensure_runtime

ensure_runtime(("PIL",))

try:
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit("Missing Pillow. Run scripts/check_dependencies.py.") from exc


REQUIRED_PROMPT_SECTIONS = (
    "Primary transformation:",
    "Image roles:",
    "Composition diagnosis:",
    "Composition repair:",
    "Subject treatment:",
    "Background treatment:",
    "Interaction:",
    "Reference transfer:",
    "Identity invariants:",
    "Typography layout:",
    "Text (verbatim):",
    "Do not add:",
)
OPTIONAL_PROMPT_SECTIONS = ("Display glyph design:",)
COMPILED_PROMPT_SECTION = "Mechanism bindings:"
ALL_PROMPT_SECTIONS = REQUIRED_PROMPT_SECTIONS + OPTIONAL_PROMPT_SECTIONS + (COMPILED_PROMPT_SECTION,)
REQUIRED_BINDING_DOMAINS = {"subject", "background", "typography", "interaction"}
DOMAIN_SIGNAL_CATEGORIES = {
    "subject": {"subject"},
    "background": {"background", "material", "color", "context"},
    "typography": {"typography", "content", "grid", "spacing"},
    "interaction": {"depth", "layout"},
}
MARKER_RE = re.compile(r"^[A-Z][A-Z0-9_-]{0,11}$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--guide", type=Path, required=True)
    parser.add_argument("--support", type=Path, action="append", default=[])
    parser.add_argument("--typeset-spec", type=Path, required=True)
    parser.add_argument("--typeset-report", type=Path, required=True)
    parser.add_argument("--recipe-json", type=Path, required=True)
    parser.add_argument("--design-plan", type=Path, required=True)
    parser.add_argument("--glyph-brief", type=Path)
    parser.add_argument("--prompt", type=Path, required=True)
    parser.add_argument("--output-image", type=Path, required=True)
    parser.add_argument("--manifest", type=Path)
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_metadata(path: Path) -> dict[str, Any]:
    try:
        with Image.open(path) as image:
            return {"width": image.width, "height": image.height, "format": image.format}
    except (OSError, ValueError) as exc:
        raise ValueError(f"cannot read image {path}: {exc}") from exc


def staged_image(source: Path, destination_base: Path) -> Path:
    suffix = source.suffix.lower() or ".png"
    destination = destination_base.with_suffix(suffix)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)
    return destination.resolve()


def section_value(prompt: str, heading: str) -> str:
    start = prompt.find(heading)
    if start < 0:
        return ""
    content_start = start + len(heading)
    later = [prompt.find(other, content_start) for other in ALL_PROMPT_SECTIONS if other != heading]
    later = [position for position in later if position >= 0]
    content_end = min(later) if later else len(prompt)
    return prompt[content_start:content_end].strip()


def printable_characters(text: str) -> list[str]:
    return [character for character in text if not character.isspace()]


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def nonempty_text(value: Any) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def guide_marker_map(document: dict[str, Any]) -> tuple[dict[str, str], list[str]]:
    """Collect semantic markers from a typeset spec or report."""
    markers: dict[str, str] = {}
    errors: list[str] = []
    for collection in ("primitives", "layers"):
        for index, item in enumerate(document.get(collection, [])):
            element_id = nonempty_text(item.get("id")) or f"{collection}-{index + 1}"
            marker = nonempty_text(item.get("guide_marker"))
            label = nonempty_text(item.get("guide_label"))
            if not marker:
                if label:
                    errors.append(f"{element_id}: guide_label requires guide_marker")
                continue
            if not MARKER_RE.fullmatch(marker):
                errors.append(f"{element_id}: invalid guide_marker {marker!r}")
            if not label:
                errors.append(f"{element_id}: guide_marker requires guide_label")
            elif not label.isascii() or not label.isprintable():
                errors.append(f"{element_id}: guide_label must be printable ASCII")
            previous = markers.get(marker)
            if previous is not None and previous != label:
                errors.append(
                    f"guide marker {marker!r} has conflicting labels {previous!r} and {label!r}"
                )
            markers[marker] = label
    return markers, errors


def validate_design_plan(
    plan: dict[str, Any], recipe: dict[str, Any], spec: dict[str, Any], report: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, str], list[str]]:
    """Validate that every selected Token reaches a model action or deterministic preprocessing."""
    errors: list[str] = []
    if plan.get("schema_version") != 1:
        errors.append("design plan schema_version must be 1")
    recipe_id = nonempty_text(recipe.get("id"))
    if nonempty_text(plan.get("recipe_id")) != recipe_id:
        errors.append("design plan recipe_id does not match recipe JSON")
    if recipe.get("errors"):
        errors.append("recipe JSON contains selection errors: " + "; ".join(map(str, recipe["errors"])))

    token_definitions: dict[str, dict[str, Any]] = {}
    for item in recipe.get("resolved_tokens", []):
        if isinstance(item, dict) and nonempty_text(item.get("id")):
            token_definitions[item["id"]] = item
    for item in recipe.get("optional_tokens", []):
        if isinstance(item, dict) and nonempty_text(item.get("id")):
            token_definitions[item["id"]] = item
    required_ids = {
        str(item.get("id"))
        for item in recipe.get("resolved_tokens", [])
        if isinstance(item, dict) and item.get("id")
    }
    selected_optional = plan.get("selected_optional_tokens", [])
    if not isinstance(selected_optional, list):
        errors.append("selected_optional_tokens must be a list")
        selected_optional = []
    selected_optional = list(map(str, selected_optional))
    if len(selected_optional) != len(set(selected_optional)):
        errors.append("selected_optional_tokens contains duplicates")
    optional_allowed = set(map(str, recipe.get("optional", [])))
    bad_optional = sorted(set(selected_optional) - optional_allowed)
    if bad_optional:
        errors.append("design plan selects tokens outside recipe optional list: " + ", ".join(bad_optional))
    missing_optional_definitions = sorted(set(selected_optional) - set(token_definitions))
    if missing_optional_definitions:
        errors.append(
            "recipe JSON lacks definitions for selected optional tokens; regenerate it with design_tokens.py: "
            + ", ".join(missing_optional_definitions)
        )
    active_ids = required_ids | set(selected_optional)
    forbidden = set(map(str, recipe.get("forbidden", [])))

    preprocess = plan.get("preprocess_tokens", [])
    if not isinstance(preprocess, list):
        errors.append("preprocess_tokens must be a list")
        preprocess = []
    preprocess = list(map(str, preprocess))
    if len(preprocess) != len(set(preprocess)):
        errors.append("preprocess_tokens contains duplicates")
    invalid_preprocess = sorted(
        token_id
        for token_id in preprocess
        if "preflight" not in token_id and "rectif" not in token_id
    )
    if invalid_preprocess:
        errors.append(
            "only deterministic preflight/rectification tokens may bypass model bindings: "
            + ", ".join(invalid_preprocess)
        )

    bindings = plan.get("bindings", [])
    if not isinstance(bindings, list):
        errors.append("design plan bindings must be a list")
        bindings = []
    if not 4 <= len(bindings) <= 6:
        errors.append("design plan requires 4–6 grouped model bindings")
    normalized: list[dict[str, Any]] = []
    covered: dict[str, str] = {}
    binding_ids: set[str] = set()
    domains: set[str] = set()
    domain_signal_hits: set[str] = set()
    plan_markers: set[str] = set()
    for index, item in enumerate(bindings):
        if not isinstance(item, dict):
            errors.append(f"binding {index + 1}: must be an object")
            continue
        binding_id = nonempty_text(item.get("id"))
        domain = nonempty_text(item.get("domain")).lower()
        token_ids = item.get("token_ids", [])
        target = nonempty_text(item.get("target"))
        instruction = nonempty_text(item.get("prompt_instruction"))
        visible_result = nonempty_text(item.get("visible_result"))
        markers = item.get("guide_markers", [])
        if not MARKER_RE.fullmatch(binding_id):
            errors.append(f"binding {index + 1}: invalid id {binding_id!r}")
        elif binding_id in binding_ids:
            errors.append(f"duplicate binding id {binding_id!r}")
        binding_ids.add(binding_id)
        if domain not in REQUIRED_BINDING_DOMAINS:
            errors.append(
                f"{binding_id or f'binding {index + 1}'}: domain must be subject, background, typography, or interaction"
            )
        else:
            domains.add(domain)
        if not isinstance(token_ids, list) or not token_ids:
            errors.append(f"{binding_id or f'binding {index + 1}'}: token_ids must be a non-empty list")
            token_ids = []
        if len(target) < 8:
            errors.append(f"{binding_id}: target must name a concrete image region or object")
        if len(instruction) < 20:
            errors.append(f"{binding_id}: prompt_instruction must state a concrete model action")
        if len(visible_result) < 8:
            errors.append(f"{binding_id}: visible_result must state what should be visible in the final image")
        if not isinstance(markers, list) or not markers:
            errors.append(f"{binding_id}: guide_markers must be a non-empty list")
            markers = []
        normalized_markers: list[str] = []
        for marker in markers:
            marker = str(marker)
            if not MARKER_RE.fullmatch(marker):
                errors.append(f"{binding_id}: invalid guide marker {marker!r}")
            else:
                normalized_markers.append(marker)
                plan_markers.add(marker)
        normalized_token_ids = list(map(str, token_ids))
        for token_id in normalized_token_ids:
            if token_id not in active_ids:
                errors.append(f"{binding_id}: token {token_id!r} is not active in this recipe selection")
            if token_id in forbidden:
                errors.append(f"{binding_id}: forbidden token selected: {token_id}")
            if token_id in covered:
                errors.append(
                    f"token {token_id} is mapped more than once: {covered[token_id]} and {binding_id}"
                )
            covered[token_id] = binding_id
            token_category = nonempty_text(token_definitions.get(token_id, {}).get("category"))
            if token_category in DOMAIN_SIGNAL_CATEGORIES.get(domain, set()):
                domain_signal_hits.add(domain)
        normalized.append(
            {
                "id": binding_id,
                "domain": domain,
                "token_ids": normalized_token_ids,
                "target": target,
                "prompt_instruction": instruction,
                "visible_result": visible_result,
                "guide_markers": normalized_markers,
            }
        )

    missing_domains = sorted(REQUIRED_BINDING_DOMAINS - domains)
    if missing_domains:
        errors.append("design plan is missing required model-work domains: " + ", ".join(missing_domains))
    weak_domains = sorted(domains - domain_signal_hits)
    if weak_domains:
        errors.append(
            "model-work domains lack a matching Recipe mechanism Token: " + ", ".join(weak_domains)
        )
    duplicate_preprocess = sorted(set(preprocess) & set(covered))
    if duplicate_preprocess:
        errors.append("tokens cannot be both preprocess and model-bound: " + ", ".join(duplicate_preprocess))
    delivered = set(covered) | set(preprocess)
    missing_tokens = sorted(active_ids - delivered)
    if missing_tokens:
        errors.append("active recipe tokens have no delivery path: " + ", ".join(missing_tokens))
    extra_preprocess = sorted(set(preprocess) - active_ids)
    if extra_preprocess:
        errors.append("preprocess tokens are not active in this recipe: " + ", ".join(extra_preprocess))

    spec_markers, spec_marker_errors = guide_marker_map(spec)
    report_markers, report_marker_errors = guide_marker_map(report)
    errors.extend(spec_marker_errors)
    errors.extend(report_marker_errors)
    if spec_markers != report_markers:
        errors.append("typeset spec semantic markers do not match typeset report semantic markers")
    missing_in_guide = sorted(plan_markers - set(spec_markers))
    if missing_in_guide:
        errors.append("design-plan guide markers missing from Image 3: " + ", ".join(missing_in_guide))
    unbound_in_guide = sorted(set(spec_markers) - plan_markers)
    if unbound_in_guide:
        errors.append("Image 3 contains semantic markers not bound to prompt actions: " + ", ".join(unbound_in_guide))
    return normalized, spec_markers, errors


def compile_mechanism_bindings(
    authored_prompt: str, bindings: list[dict[str, Any]], marker_labels: dict[str, str]
) -> str:
    """Insert the exact semantic plan into the prompt passed to ImageGen."""
    lines = [
        COMPILED_PROMPT_SECTION,
        "Image 3 contains labeled spatial markers. Use them as region instructions, not visible final text.",
    ]
    for binding in bindings:
        marker_text = ", ".join(
            f"{marker}={marker_labels.get(marker, 'UNRESOLVED')}" for marker in binding["guide_markers"]
        )
        lines.append(
            f"- [{binding['id']} / {binding['domain']}] Target: {binding['target']} "
            f"Action: {binding['prompt_instruction']} "
            f"Visible result: {binding['visible_result']} "
            f"Image 3 markers: {marker_text}."
        )
    lines.append(
        "Remove every marker badge, guide label, scaffold box, flat guide tint, and construction line from the final image."
    )
    block = "\n".join(lines)
    insertion_heading = "Composition diagnosis:"
    insertion = authored_prompt.find(insertion_heading)
    if insertion < 0:
        return authored_prompt.rstrip() + "\n\n" + block
    return authored_prompt[:insertion].rstrip() + "\n\n" + block + "\n\n" + authored_prompt[insertion:]


def main() -> int:
    args = parse_args()
    run_dir = args.run_dir.resolve()
    analysis_dir = run_dir / "analysis"
    inputs_dir = run_dir / "inputs"
    errors: list[str] = []

    required_files = {
        "source": args.source,
        "reference": args.reference,
        "guide": args.guide,
        "typeset spec": args.typeset_spec,
        "typeset report": args.typeset_report,
        "recipe JSON": args.recipe_json,
        "design plan": args.design_plan,
        "prompt": args.prompt,
    }
    required_files.update(
        {f"support image {index}": path for index, path in enumerate(args.support, start=1)}
    )
    for label, path in required_files.items():
        if not path.is_file():
            errors.append(f"{label} not found: {path}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    try:
        spec = load_json(args.typeset_spec)
        report = load_json(args.typeset_report)
        recipe = load_json(args.recipe_json)
        design_plan = load_json(args.design_plan)
        authored_prompt = args.prompt.read_text(encoding="utf-8").strip()
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1

    if report.get("passed") is not True:
        errors.append("typeset report must have passed=true")
    if list(spec.get("canvas", [])) != list(report.get("canvas", [])):
        errors.append("typeset spec canvas does not match typeset report canvas")

    if COMPILED_PROMPT_SECTION in authored_prompt:
        errors.append("authored prompt must not contain Mechanism bindings; prepare_generation.py compiles it")
    bindings, marker_labels, design_errors = validate_design_plan(design_plan, recipe, spec, report)
    errors.extend(design_errors)
    prompt = compile_mechanism_bindings(authored_prompt, bindings, marker_labels)

    image_data: dict[str, dict[str, Any]] = {}
    for label, path in (("source", args.source), ("reference", args.reference), ("guide", args.guide)):
        try:
            image_data[label] = image_metadata(path)
        except ValueError as exc:
            errors.append(str(exc))
    if "guide" in image_data and image_data["guide"]:
        guide_canvas = [image_data["guide"]["width"], image_data["guide"]["height"]]
        if guide_canvas != list(report.get("canvas", [])):
            errors.append(f"guide canvas {guide_canvas} does not match report canvas {report.get('canvas')}")

    missing_sections = [heading for heading in REQUIRED_PROMPT_SECTIONS if not section_value(authored_prompt, heading)]
    if missing_sections:
        errors.append("prompt sections missing or empty: " + ", ".join(missing_sections))
    roles = section_value(authored_prompt, "Image roles:")
    if roles and not all(label in roles for label in ("Image 1", "Image 2", "Image 3")):
        errors.append("Image roles must explicitly name Image 1, Image 2, and Image 3")
    for index, _path in enumerate(args.support, start=4):
        if roles and f"Image {index}" not in roles:
            errors.append(f"Image roles must explicitly name optional support Image {index}")

    display_layers = []
    for layer in spec.get("layers", []):
        role = str(layer.get("role", "")).strip().lower().replace("_", "-")
        if role in {"display", "display-title", "title", "structural-title"}:
            display_layers.append(layer)
    reinterpret_layers = [
        layer for layer in display_layers if str(layer.get("glyph_design_mode", "")).strip().lower() == "reinterpret"
    ]
    for layer in display_layers:
        mode = str(layer.get("glyph_design_mode", "")).strip().lower()
        if mode not in {"literal", "reinterpret"}:
            errors.append(f"{layer.get('id', 'display layer')}: missing explicit glyph_design_mode")
        if mode == "reinterpret" and str(layer.get("guide_render", "")).strip().lower() != "scaffold":
            errors.append(f"{layer.get('id', 'display layer')}: reinterpret requires guide_render=scaffold")

    if reinterpret_layers:
        if args.glyph_brief is None or not args.glyph_brief.is_file():
            errors.append("reinterpret display text requires --glyph-brief")
            glyph_brief = ""
        else:
            glyph_brief = args.glyph_brief.read_text(encoding="utf-8").strip()
            if len(glyph_brief) < 200:
                errors.append("glyph brief is too short to contain visible morphology and per-character actions")
        display_prompt = section_value(authored_prompt, "Display glyph design:")
        if not display_prompt:
            errors.append("reinterpret display text requires a non-empty Display glyph design section")
        for layer in reinterpret_layers:
            title = str(layer.get("text", "")).strip()
            if title and title not in display_prompt:
                errors.append(f"Display glyph design must name the exact title {title!r}")
            missing_brief_chars = [char for char in printable_characters(title) if char not in glyph_brief]
            if missing_brief_chars:
                errors.append(
                    f"glyph brief does not cover every title character in {title!r}: "
                    + " ".join(missing_brief_chars)
                )
    elif section_value(authored_prompt, "Display glyph design:"):
        errors.append("Display glyph design is present but no display layer is marked reinterpret")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    all_source_paths = [args.source, args.reference, args.guide, *args.support]
    source_hashes = [sha256(path) for path in all_source_paths]
    if len(set(source_hashes)) != len(source_hashes):
        print("ERROR: every source, reference, guide, and support input must be a distinct image")
        return 1
    output_image = args.output_image.resolve()
    if not is_within(output_image, run_dir / "final"):
        print(f"ERROR: output image must be inside {run_dir / 'final'}")
        return 1
    manifest_path = (args.manifest or (analysis_dir / "generation-call.json")).resolve()
    if not is_within(manifest_path, analysis_dir):
        print(f"ERROR: manifest must be inside {analysis_dir}")
        return 1

    staged_source = staged_image(args.source, inputs_dir / "01-edit-target")
    staged_reference = staged_image(args.reference, inputs_dir / "02-primary-reference")
    staged_guide = staged_image(args.guide, inputs_dir / "03-typeset-guide")
    staged_supports = [
        staged_image(path, inputs_dir / f"{index:02d}-support-{index - 3:02d}")
        for index, path in enumerate(args.support, start=4)
    ]
    staged_paths = [staged_source, staged_reference, staged_guide, *staged_supports]
    hashes = [sha256(path) for path in staged_paths]
    for index, path in enumerate(args.support, start=1):
        image_data[f"support-{index}"] = image_metadata(path)

    analysis_dir.mkdir(parents=True, exist_ok=True)
    staged_prompt = (analysis_dir / "04-imagegen-prompt.txt").resolve()
    staged_prompt.write_text(prompt + "\n", encoding="utf-8")
    output_image.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    tool_arguments = {
        "prompt": prompt,
        "referenced_image_paths": [str(path) for path in staged_paths],
    }
    input_order = [
        "edit-target",
        "primary-visual-reference",
        "typeset-guide",
        *[f"support-{index}" for index in range(1, len(staged_supports) + 1)],
    ]
    metadata_labels = (
        "source",
        "reference",
        "guide",
        *[f"support-{index}" for index in range(1, len(staged_supports) + 1)],
    )
    manifest = {
        "schema_version": 2,
        "action": "edit",
        "input_order": input_order,
        "referenced_image_paths": tool_arguments["referenced_image_paths"],
        "prompt_path": str(staged_prompt),
        "authored_prompt_path": str(args.prompt.resolve()),
        "prompt": prompt,
        "tool_arguments": tool_arguments,
        "recipe_json_path": str(args.recipe_json.resolve()),
        "design_plan_path": str(args.design_plan.resolve()),
        "recipe_id": recipe.get("id"),
        "mechanism_bindings": bindings,
        "guide_markers": marker_labels,
        "preprocess_tokens": list(map(str, design_plan.get("preprocess_tokens", []))),
        "token_delivery": {
            **{
                token_id: {"channel": "prompt+guide", "binding": binding["id"]}
                for binding in bindings
                for token_id in binding["token_ids"]
            },
            **{
                str(token_id): {"channel": "preprocess", "binding": None}
                for token_id in design_plan.get("preprocess_tokens", [])
            },
        },
        "typeset_spec_path": str(args.typeset_spec.resolve()),
        "typeset_report_path": str(args.typeset_report.resolve()),
        "glyph_brief_path": str(args.glyph_brief.resolve()) if args.glyph_brief else None,
        "output_path": str(output_image),
        "inputs": [
            {
                "role": role,
                "path": str(path),
                "sha256": digest,
                **image_data[label],
            }
            for role, label, path, digest in zip(
                input_order,
                metadata_labels,
                staged_paths,
                hashes,
            )
        ],
    }
    manifest["call_signature"] = hashlib.sha256(
        ("\n".join(hashes) + "\n" + prompt).encode("utf-8")
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"READY: exact ImageGen handoff written to {manifest_path}")
    print("Pass manifest.tool_arguments to ImageGen without rewriting, reordering, or omission.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
