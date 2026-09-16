#!/usr/bin/env python3
"""Validate, query, resolve, and render the Yingzao token catalog."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
import sys
from pathlib import Path
from typing import Any


CATALOG_PATH = Path(__file__).resolve().parents[1] / "references" / "design-tokens.json"
SKILL_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PLATE_DIR = SKILL_ROOT / "assets" / "reference-plates"
REFERENCE_THUMBNAIL_DIR = SKILL_ROOT / "assets" / "reference-thumbnails"
TOKEN_FIELDS = {
    "id",
    "tier",
    "category",
    "label",
    "intent",
    "value",
    "tags",
    "requires",
    "compatible",
    "conflicts",
    "constraints",
    "prompt",
    "visual",
    "sources",
}
RECIPE_FIELDS = {
    "id",
    "label",
    "family",
    "signature",
    "sources",
    "tags",
    "tokens",
    "optional",
    "forbidden",
    "invariants",
}
TIERS = {"primitive", "semantic", "component"}


def bundled_reference_assets(sources: list[str]) -> list[dict[str, str]]:
    """Resolve recipe evidence to an actual image input, preferring larger plates."""
    assets: list[dict[str, str]] = []
    for source in sources:
        plate = REFERENCE_PLATE_DIR / source
        thumbnail = REFERENCE_THUMBNAIL_DIR / source
        if plate.is_file():
            assets.append(
                {"source": source, "path": str(plate.resolve()), "quality": "plate"}
            )
        elif thumbnail.is_file():
            assets.append(
                {
                    "source": source,
                    "path": str(thumbnail.resolve()),
                    "quality": "thumbnail",
                }
            )
    return assets


def load_catalog(path: Path = CATALOG_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def token_map(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {token["id"]: token for token in catalog["tokens"]}


def resolve_requires(token_ids: list[str], tokens: dict[str, dict[str, Any]]) -> list[str]:
    resolved: list[str] = []
    active: set[str] = set()
    done: set[str] = set()

    def visit(token_id: str) -> None:
        if token_id in done:
            return
        if token_id in active:
            raise ValueError(f"dependency cycle at {token_id}")
        active.add(token_id)
        for dependency in tokens[token_id].get("requires", []):
            visit(dependency)
        active.remove(token_id)
        done.add(token_id)
        resolved.append(token_id)

    for item in token_ids:
        visit(item)
    return resolved


def selection_errors(
    token_ids: list[str], catalog: dict[str, Any], tokens: dict[str, dict[str, Any]]
) -> list[str]:
    selected = set(token_ids)
    errors: list[str] = []
    conflict_pairs: set[tuple[str, str]] = set()
    for token_id in token_ids:
        for conflict in tokens[token_id].get("conflicts", []):
            if conflict in selected:
                conflict_pairs.add(tuple(sorted((token_id, conflict))))
    for left, right in sorted(conflict_pairs):
        errors.append(f"conflict: {left} <> {right}")

    for group in catalog.get("mutex_groups", []):
        hits = [item for item in group["members"] if item in selected]
        if len(hits) > group["max"]:
            errors.append(
                f"mutex {group['id']} allows {group['max']}, got {len(hits)}: "
                + ", ".join(hits)
            )
    return errors


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    items = catalog.get("tokens")
    if not isinstance(items, list) or not items:
        return ["tokens must be a non-empty list"]

    ids = [item.get("id") for item in items]
    duplicate_ids = sorted({item for item in ids if ids.count(item) > 1})
    if duplicate_ids:
        errors.append("duplicate token ids: " + ", ".join(duplicate_ids))

    tokens = token_map(catalog)
    known = set(tokens)
    controlled = catalog.get("controlled_tags", {})
    vocabulary = controlled.get("vocabulary", [])
    aliases = controlled.get("aliases", {})
    if not vocabulary or len(vocabulary) != len(set(vocabulary)):
        errors.append("controlled_tags.vocabulary must be non-empty and unique")
    for alias, target in aliases.items():
        if target not in vocabulary:
            errors.append(f"controlled tag alias {alias!r} points to unknown target {target!r}")
    style_axes = catalog.get("style_axes", {})
    if not style_axes:
        errors.append("style_axes must define the recipe distance dimensions")
    for index, token in enumerate(items):
        missing = sorted(TOKEN_FIELDS - set(token))
        token_id = token.get("id", f"tokens[{index}]")
        if missing:
            errors.append(f"{token_id}: missing fields {', '.join(missing)}")
        if not str(token_id).startswith("cap."):
            errors.append(f"{token_id}: id must start with cap.")
        if token.get("tier") not in TIERS:
            errors.append(f"{token_id}: unknown tier {token.get('tier')!r}")
        if not token.get("tags"):
            errors.append(f"{token_id}: at least one search tag is required")
        if not token.get("constraints"):
            errors.append(f"{token_id}: at least one checkable constraint is required")
        if not token.get("sources"):
            errors.append(f"{token_id}: at least one source is required")
        for field in ("requires", "compatible", "conflicts"):
            for reference in token.get(field, []):
                if reference not in known:
                    errors.append(f"{token_id}: unknown {field} reference {reference}")
        for axis, value in token.get("value", {}).get("style_axes", {}).items():
            if axis not in style_axes:
                errors.append(f"{token_id}: unknown style axis {axis}")
            elif value not in style_axes[axis]:
                errors.append(f"{token_id}: invalid style axis value {axis}={value}")

    for group in catalog.get("mutex_groups", []):
        if not group.get("id") or group.get("max", 0) < 1:
            errors.append(f"invalid mutex group: {group}")
        for member in group.get("members", []):
            if member not in known:
                errors.append(f"{group.get('id')}: unknown member {member}")

    layout_group = next(
        (group for group in catalog.get("mutex_groups", []) if group.get("id") == "slot.layout-primary"),
        None,
    )
    if layout_group is None:
        errors.append("missing required mutex group: slot.layout-primary")

    recipe_ids: set[str] = set()
    for recipe in catalog.get("recipes", []):
        recipe_id = recipe.get("id", "<recipe>")
        missing = sorted(RECIPE_FIELDS - set(recipe))
        if missing:
            errors.append(f"{recipe_id}: missing recipe fields {', '.join(missing)}")
        if recipe_id in recipe_ids:
            errors.append(f"duplicate recipe id: {recipe_id}")
        recipe_ids.add(recipe_id)
        if not str(recipe_id).startswith("cap.recipe."):
            errors.append(f"{recipe_id}: recipe id must start with cap.recipe.")
        if not recipe.get("family"):
            errors.append(f"{recipe_id}: recipe family is required")
        if not recipe.get("signature"):
            errors.append(f"{recipe_id}: visible signature is required")
        elif len(str(recipe["signature"]).strip()) < 12:
            errors.append(f"{recipe_id}: visible signature is too vague")
        if not recipe.get("sources"):
            errors.append(f"{recipe_id}: at least one recipe source is required")
        elif not bundled_reference_assets(recipe.get("sources", [])):
            errors.append(
                f"{recipe_id}: no bundled visual reference asset for any recipe source"
            )
        if not recipe.get("tags"):
            errors.append(f"{recipe_id}: at least one recipe search tag is required")
        all_refs = recipe.get("tokens", []) + recipe.get("optional", []) + recipe.get("forbidden", [])
        for reference in all_refs:
            if reference not in known:
                errors.append(f"{recipe_id}: unknown token {reference}")
        if any(reference not in known for reference in recipe.get("tokens", [])):
            continue
        try:
            resolved = resolve_requires(recipe.get("tokens", []), tokens)
        except ValueError as exc:
            errors.append(f"{recipe_id}: {exc}")
            continue
        for issue in selection_errors(resolved, catalog, tokens):
            errors.append(f"{recipe_id}: {issue}")
        if layout_group is not None:
            layout_hits = sorted(set(resolved).intersection(layout_group.get("members", [])))
            if len(layout_hits) != 1:
                errors.append(
                    f"{recipe_id}: requires exactly one slot.layout-primary token, got "
                    + (", ".join(layout_hits) if layout_hits else "none")
                )
        evidence_ids = recipe.get("tokens", []) + recipe.get("optional", [])
        if not any(reference not in known for reference in evidence_ids):
            evidence_sources: set[str] = set()
            for token_id in resolve_requires(evidence_ids, tokens):
                evidence_sources.update(tokens[token_id].get("sources", []))
            unsupported_sources = sorted(set(recipe.get("sources", [])) - evidence_sources)
            if unsupported_sources:
                errors.append(
                    f"{recipe_id}: recipe sources lack token evidence: "
                    + ", ".join(unsupported_sources)
                )
        forbidden = set(recipe.get("forbidden", []))
        overlap = forbidden.intersection(resolved)
        if overlap:
            errors.append(f"{recipe_id}: required and forbidden: {', '.join(sorted(overlap))}")
        if not recipe.get("invariants"):
            errors.append(f"{recipe_id}: at least one invariant is required")

    searchable_tags: set[str] = set()
    for item in items + catalog.get("recipes", []):
        searchable_tags.update(item.get("tags", []))
    for tag in vocabulary:
        if tag not in searchable_tags:
            errors.append(f"controlled tag {tag!r} has no searchable token or recipe")

    return errors


def searchable_text(token: dict[str, Any]) -> str:
    fields = [
        token["id"],
        token["label"],
        token["intent"],
        " ".join(token.get("tags", [])),
        " ".join(token.get("constraints", [])),
        " ".join(token.get("sources", [])),
    ]
    return " ".join(fields).lower()


def recipe_searchable_text(recipe: dict[str, Any]) -> str:
    fields = [
        recipe["id"],
        recipe["label"],
        recipe.get("family", ""),
        recipe.get("signature", ""),
        " ".join(recipe.get("tags", [])),
        " ".join(recipe.get("sources", [])),
    ]
    return " ".join(fields).lower()


def controlled_tag_payload(catalog: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    controlled = catalog.get("controlled_tags", {})
    return list(controlled.get("vocabulary", [])), dict(controlled.get("aliases", {}))


def normalize_input_tags(
    catalog: dict[str, Any], raw_tags: list[str]
) -> tuple[list[str], list[dict[str, str]], list[str]]:
    vocabulary, aliases = controlled_tag_payload(catalog)
    allowed = set(vocabulary)
    normalized: list[str] = []
    mapping: list[dict[str, str]] = []
    unmatched: list[str] = []
    for raw in raw_tags:
        value = raw.strip()
        if not value:
            continue
        canonical = aliases.get(value, value)
        if canonical not in allowed:
            unmatched.append(value)
            continue
        if canonical not in normalized:
            normalized.append(canonical)
        mapping.append({"input": value, "canonical": canonical})
    return normalized, mapping, unmatched


def recipe_fingerprint(catalog: dict[str, Any], recipe: dict[str, Any]) -> dict[str, str]:
    tokens = token_map(catalog)
    resolved = resolve_requires(recipe.get("tokens", []), tokens)
    fingerprint = {
        "ground": "photographic",
        "polarity": "photographic",
        "era": "modern-editorial",
        "texture": "low",
        "saturation": "muted",
        "image_behavior": "hybrid",
    }
    ids = set(resolved)
    if "cap.background.paper-warm" in ids:
        fingerprint.update(ground="paper-light", era="heritage-print")
    if "cap.background.flat-field" in ids:
        fingerprint["ground"] = "flat-color"
    if "cap.background.dark-ground" in ids or "cap.color.night-blue-silver" in ids:
        fingerprint.update(ground="dark", era="nightlife")
    if "cap.context.verified-document" in ids or "cap.background.source-text-field" in ids:
        fingerprint["era"] = "archival"
    if "cap.material.arch-high-key-relief" in ids:
        fingerprint.update(polarity="high-key", texture="low", image_behavior="flat")
    if "cap.material.arch-line-engraving" in ids:
        fingerprint.update(polarity="dark-on-light", texture="fine", image_behavior="line")
    if "cap.material.arch-halftone-fine" in ids:
        fingerprint.update(polarity="dark-on-light", texture="fine", image_behavior="halftone")
    if "cap.material.arch-halftone-coarse" in ids or "cap.material.arch-xerox" in ids:
        fingerprint.update(polarity="dark-on-light", texture="coarse", image_behavior="halftone")
    if "cap.material.arch-duotone" in ids:
        fingerprint.update(polarity="dark-on-light", texture="fine", image_behavior="duotone", saturation="accent")
    if "cap.material.arch-regional-flat" in ids:
        fingerprint["image_behavior"] = "flat"
    for token_id in resolved:
        fingerprint.update(tokens[token_id].get("value", {}).get("style_axes", {}))
    return fingerprint


def style_distance(left: dict[str, str], right: dict[str, str], axes: list[str]) -> int:
    return sum(left.get(axis) != right.get(axis) for axis in axes)


def load_history(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("history must be a JSON list")
    return [item for item in payload if isinstance(item, dict)]


def record_history(path: Path, suggestions: list[dict[str, Any]]) -> None:
    history = load_history(path)
    now = datetime.now(timezone.utc).isoformat()
    for item in suggestions:
        history.append(
            {
                "recipe": item["id"],
                "family": item["family"],
                "fingerprint": item["style_fingerprint"],
                "recorded_at": now,
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history[-100:], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def query_tokens(
    catalog: dict[str, Any],
    category: str | None,
    tier: str | None,
    tag: str | None,
    search: str | None,
    compatible_with: str | None,
) -> list[dict[str, Any]]:
    tokens = token_map(catalog)
    candidates = list(catalog["tokens"])
    if category:
        candidates = [item for item in candidates if item["category"] == category]
    if tier:
        candidates = [item for item in candidates if item["tier"] == tier]
    if tag:
        needle = tag.lower()
        candidates = [item for item in candidates if any(needle in value.lower() for value in item["tags"])]
    if search:
        needle = search.lower()
        candidates = [item for item in candidates if needle in searchable_text(item)]
    if compatible_with:
        if compatible_with not in tokens:
            raise KeyError(f"unknown token: {compatible_with}")
        peer = tokens[compatible_with]
        candidates = [
            item
            for item in candidates
            if item["id"] != compatible_with
            and (
                item["id"] in peer.get("compatible", [])
                or compatible_with in item.get("compatible", [])
            )
            and item["id"] not in peer.get("conflicts", [])
            and compatible_with not in item.get("conflicts", [])
        ]
    return sorted(candidates, key=lambda item: (item["category"], item["tier"], item["id"]))


def print_tokens(items: list[dict[str, Any]], as_json: bool) -> None:
    if as_json:
        print(json.dumps(items, ensure_ascii=False, indent=2))
        return
    if not items:
        print("No matching tokens.")
        return
    width = max(len(item["id"]) for item in items)
    for item in items:
        print(f"{item['id']:<{width}}  {item['label']}  [{', '.join(item['tags'])}]")


def recipe_payload(catalog: dict[str, Any], recipe_id: str) -> dict[str, Any]:
    recipes = {item["id"]: item for item in catalog.get("recipes", [])}
    if recipe_id not in recipes:
        raise KeyError(f"unknown recipe: {recipe_id}")
    tokens = token_map(catalog)
    recipe = recipes[recipe_id]
    resolved_ids = resolve_requires(recipe["tokens"], tokens)
    return {
        "id": recipe["id"],
        "label": recipe["label"],
        "family": recipe["family"],
        "signature": recipe["signature"],
        "sources": recipe["sources"],
        "reference_assets": bundled_reference_assets(recipe["sources"]),
        "tags": recipe["tags"],
        "resolved_tokens": [tokens[item] for item in resolved_ids],
        "optional": recipe["optional"],
        "optional_tokens": [tokens[item] for item in recipe["optional"]],
        "forbidden": recipe["forbidden"],
        "forbidden_tokens": [tokens[item] for item in recipe["forbidden"]],
        "invariants": recipe["invariants"],
        "style_fingerprint": recipe_fingerprint(catalog, recipe),
        "errors": selection_errors(resolved_ids, catalog, tokens),
    }


def suggest_recipes(
    catalog: dict[str, Any],
    tags: list[str],
    excludes: set[str],
    count: int,
    maximize_distance: bool = False,
    history: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    tokens = token_map(catalog)
    normalized_tags, tag_mapping, unmatched_tags = normalize_input_tags(catalog, tags)
    scored: list[dict[str, Any]] = []
    matched_globally: set[str] = set()
    for recipe in catalog.get("recipes", []):
        if recipe["id"] in excludes:
            continue
        resolved_ids = resolve_requires(recipe["tokens"], tokens)
        direct_tags = [value.lower() for value in recipe.get("tags", [])]
        recipe_text = recipe_searchable_text(recipe)
        token_texts = [searchable_text(tokens[token_id]) for token_id in resolved_ids]
        score = 0
        matched: list[str] = []
        for raw_tag in normalized_tags:
            needle = raw_tag.lower()
            if not needle:
                continue
            tag_score = 0
            if any(needle in value or value in needle for value in direct_tags):
                tag_score = max(tag_score, 4)
            if needle in recipe_text:
                tag_score = max(tag_score, 2)
            if any(needle in value for value in token_texts):
                tag_score = max(tag_score, 1)
            if tag_score:
                matched.append(raw_tag)
                matched_globally.add(raw_tag)
                score += tag_score
        if not normalized_tags and not tags:
            score = 1
        scored.append(
            {
                "score": score,
                "recipe": recipe,
                "matched": matched,
                "fingerprint": recipe_fingerprint(catalog, recipe),
            }
        )

    for tag in normalized_tags:
        if tag not in matched_globally:
            unmatched_tags.append(tag)
    scored = [item for item in scored if not tags or item["score"] > 0]
    scored.sort(key=lambda item: (-item["score"], item["recipe"]["id"]))
    selected: list[dict[str, Any]] = []
    used_families: set[str] = set()
    history_fingerprints = [
        item.get("fingerprint", {}) for item in (history or []) if item.get("fingerprint")
    ]
    history_recipe_ids = {item.get("recipe") for item in (history or []) if item.get("recipe")}
    history_families = {item.get("family") for item in (history or []) if item.get("family")}
    axes = list(catalog.get("style_axes", {}))
    remaining = list(scored)
    while remaining and len(selected) < count:
        eligible = [item for item in remaining if item["recipe"]["family"] not in used_families]
        if not eligible:
            break
        if maximize_distance:
            comparison = [item["style_fingerprint"] for item in selected] + history_fingerprints

            def candidate_key(item: dict[str, Any]) -> tuple[float, int, str]:
                distance = min(
                    (style_distance(item["fingerprint"], prior, axes) for prior in comparison),
                    default=len(axes),
                )
                repeat_penalty = 0
                if item["recipe"]["id"] in history_recipe_ids:
                    repeat_penalty += 24
                if item["recipe"]["family"] in history_families:
                    repeat_penalty += 10
                return (item["score"] * 10 + distance * 2 - repeat_penalty, distance, item["recipe"]["id"])

            candidate = max(eligible, key=candidate_key)
        else:
            candidate = eligible[0]
        remaining.remove(candidate)
        recipe = candidate["recipe"]
        family = recipe["family"]
        selected.append(
            {
                "id": recipe["id"],
                "label": recipe["label"],
                "family": family,
                "score": candidate["score"],
                "matched_tags": candidate["matched"],
                "signature": recipe["signature"],
                "sources": recipe["sources"],
                "reference_assets": bundled_reference_assets(recipe["sources"]),
                "style_fingerprint": candidate["fingerprint"],
            }
        )
        used_families.add(family)
    metadata = {
        "normalized_tags": tag_mapping,
        "matched_tags": sorted(matched_globally),
        "unmatched_tags": list(dict.fromkeys(unmatched_tags)),
        "maximize_distance": maximize_distance,
        "history_entries": len(history or []),
    }
    return selected, metadata


def badges(values: list[str], css_class: str = "") -> str:
    return "".join(
        f'<span class="badge {css_class}">{html.escape(value)}</span>' for value in values
    )


def source_gallery(sources: list[str], reference_dir: Path | None) -> str:
    source_badges = badges(sources, "source")
    if reference_dir is None:
        return f'<div class="sources"><b>来源</b>{source_badges}</div>'
    images: list[str] = []
    for source in sources:
        path = reference_dir / source
        if path.is_file() and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            images.append(
                f'<figure><img src="{html.escape(path.resolve().as_uri(), quote=True)}" '
                f'alt="{html.escape(source, quote=True)}"><figcaption>{html.escape(source[:8])}</figcaption></figure>'
            )
    gallery = f'<div class="source-gallery">{"".join(images)}</div>' if images else ""
    return f'{gallery}<div class="sources"><b>来源</b>{source_badges}</div>'


def render_catalog(catalog: dict[str, Any], reference_dir: Path | None = None) -> str:
    categories = sorted({item["category"] for item in catalog["tokens"]})
    tiers = ["primitive", "semantic", "component"]
    cards: list[str] = []
    for item in sorted(catalog["tokens"], key=lambda value: (value["category"], value["tier"], value["id"])):
        search_blob = searchable_text(item)
        swatch = html.escape(item.get("visual", {}).get("swatch", "#ddd"), quote=True)
        glyph = html.escape(item.get("visual", {}).get("glyph", ""))
        relations = []
        if item.get("requires"):
            relations.append(f'<div><b>依赖</b>{badges(item["requires"], "requires")}</div>')
        if item.get("compatible"):
            relations.append(f'<div><b>兼容</b>{badges(item["compatible"], "compatible")}</div>')
        if item.get("conflicts"):
            relations.append(f'<div><b>冲突</b>{badges(item["conflicts"], "conflicts")}</div>')
        constraint_list = "".join(f"<li>{html.escape(value)}</li>" for value in item["constraints"])
        sources = source_gallery(item.get("sources", []), reference_dir)
        cards.append(
            f'''<article class="card" data-category="{html.escape(item['category'])}" data-tier="{html.escape(item['tier'])}" data-search="{html.escape(search_blob, quote=True)}">
  <div class="swatch" style="background:{swatch}"><span>{glyph}</span></div>
  <div class="card-body">
    <div class="eyebrow">{html.escape(item['tier'])} · {html.escape(item['category'])}</div>
    <h2>{html.escape(item['label'])}</h2>
    <code>{html.escape(item['id'])}</code>
    <p>{html.escape(item['intent'])}</p>
    <div class="tags">{badges(item['tags'])}</div>
    {sources}
    <details><summary>参数与约束</summary><pre>{html.escape(json.dumps(item['value'], ensure_ascii=False, indent=2))}</pre><ul>{constraint_list}</ul></details>
    <details><summary>关系</summary>{''.join(relations) or '<p>无显式关系</p>'}</details>
  </div>
</article>'''
        )

    recipe_cards: list[str] = []
    for recipe in catalog.get("recipes", []):
        recipe_sources = source_gallery(recipe.get("sources", []), reference_dir)
        fingerprint = recipe_fingerprint(catalog, recipe)
        recipe_cards.append(
            f'''<article class="recipe" data-search="{html.escape(recipe_searchable_text(recipe), quote=True)}">
  <div class="eyebrow">recipe · {html.escape(recipe['family'])}</div><h2>{html.escape(recipe['label'])}</h2><code>{html.escape(recipe['id'])}</code>
  <p class="signature"><b>可见特征</b> {html.escape(recipe['signature'])}</p>
  <div class="tags">{badges(recipe['tags'])}</div>
  <div class="tags">{badges([f'{key}:{value}' for key, value in fingerprint.items()], 'compatible')}</div>
  {recipe_sources}
  <p><b>必选</b>{badges(recipe['tokens'], 'requires')}</p>
  <p><b>可选</b>{badges(recipe['optional'], 'compatible')}</p>
  <p><b>禁用</b>{badges(recipe['forbidden'], 'conflicts')}</p>
  <ul>{''.join(f'<li>{html.escape(value)}</li>' for value in recipe['invariants'])}</ul>
</article>'''
        )

    coverage_cards: list[str] = []
    if reference_dir is not None and reference_dir.is_dir():
        token_links: dict[str, list[str]] = {}
        recipe_links: dict[str, list[str]] = {}
        for item in catalog["tokens"]:
            for source in item.get("sources", []):
                token_links.setdefault(source, []).append(item["id"])
        for recipe in catalog.get("recipes", []):
            for source in recipe.get("sources", []):
                recipe_links.setdefault(source, []).append(recipe["id"])
        for path in sorted(reference_dir.iterdir()):
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            source = path.name
            token_ids = token_links.get(source, [])
            recipe_ids = recipe_links.get(source, [])
            status = "recipe" if recipe_ids else ("token" if token_ids else "unmapped")
            coverage_cards.append(
                f'''<article class="coverage-card" data-search="{html.escape((source + ' ' + ' '.join(token_ids + recipe_ids)).lower(), quote=True)}">
  <img src="{html.escape(path.resolve().as_uri(), quote=True)}" alt="{html.escape(source, quote=True)}">
  <div><div class="eyebrow">{status}</div><code>{html.escape(source)}</code>
  <p><b>Tokens</b>{badges(token_ids, 'requires') if token_ids else '<span class="badge conflicts">none</span>'}</p>
  <p><b>Recipes</b>{badges(recipe_ids, 'compatible') if recipe_ids else '<span class="badge">conditional / source-only</span>'}</p></div>
</article>'''
            )

    category_options = "".join(f'<option value="{html.escape(value)}">{html.escape(value)}</option>' for value in categories)
    tier_options = "".join(f'<option value="{value}">{value}</option>' for value in tiers)
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chinese Architecture Poster · Token Catalog</title>
<style>
:root{{--paper:#eee8dd;--ink:#24211e;--muted:#766f67;--red:#a33b32;--green:#3d6b5f;--line:#cbc1b4}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:Inter,"Noto Sans SC",system-ui,sans-serif}}
header{{position:sticky;top:0;z-index:5;background:rgba(238,232,221,.94);backdrop-filter:blur(12px);border-bottom:1px solid var(--line);padding:22px clamp(20px,5vw,72px)}}
h1{{margin:0 0 6px;font:700 clamp(26px,4vw,54px)/1.05 Georgia,"Noto Serif SC",serif}}header p{{margin:0;color:var(--muted)}}
.controls{{display:grid;grid-template-columns:minmax(180px,1fr) repeat(2,minmax(130px,220px));gap:10px;margin-top:18px}}input,select{{width:100%;border:1px solid var(--line);background:#f7f3eb;padding:12px 14px;color:var(--ink);font:inherit}}
main{{padding:32px clamp(20px,5vw,72px) 80px}}.section-title{{display:flex;align-items:baseline;gap:14px;margin:40px 0 18px}}.section-title h2{{font:700 30px Georgia,"Noto Serif SC",serif;margin:0}}.count{{color:var(--muted)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:16px}}.card,.recipe{{background:#f7f3eb;border:1px solid var(--line);min-width:0}}.swatch{{height:116px;display:grid;place-items:center;border-bottom:1px solid var(--line)}}.swatch span{{font:700 38px Georgia,"Noto Serif SC",serif;white-space:pre-line;text-align:center;color:#fff;mix-blend-mode:difference}}.card-body,.recipe{{padding:18px}}.eyebrow{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}}h2{{margin:5px 0 7px;font-size:21px}}code{{font-size:11px;overflow-wrap:anywhere;color:#5d554d}}p{{line-height:1.55}}.badge{{display:inline-block;margin:3px 4px 3px 0;padding:3px 6px;border:1px solid var(--line);font-size:10px;overflow-wrap:anywhere}}.requires{{border-color:#8c7962}}.compatible{{border-color:var(--green);color:var(--green)}}.conflicts{{border-color:var(--red);color:var(--red)}}details{{border-top:1px solid #ded6ca;margin-top:12px;padding-top:10px}}summary{{cursor:pointer;font-weight:650}}pre{{white-space:pre-wrap;font-size:11px}}li{{margin:5px 0;line-height:1.4}}.recipe-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px}}.hidden{{display:none!important}}
.source-gallery{{display:flex;gap:6px;overflow-x:auto;margin:12px 0 8px}}.source-gallery figure{{margin:0;min-width:72px;width:72px}}.source-gallery img{{width:72px;height:96px;display:block;object-fit:cover;border:1px solid var(--line);background:#ddd}}.source-gallery figcaption{{font-size:9px;color:var(--muted);margin-top:3px}}.sources b{{font-size:11px;margin-right:6px}}.signature{{border-left:3px solid var(--green);padding-left:10px}}.coverage-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}}.coverage-card{{display:grid;grid-template-columns:112px 1fr;gap:12px;background:#f7f3eb;border:1px solid var(--line);padding:10px;min-width:0}}.coverage-card>img{{width:112px;height:148px;object-fit:cover;background:#ddd}}.coverage-card p{{margin:8px 0}}
@media(max-width:720px){{.controls{{grid-template-columns:1fr}}.recipe-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>
<header><h1>建筑海报 Token Catalog</h1><p>{len(catalog['tokens'])} tokens · {len(catalog.get('recipes', []))} recipes · v{html.escape(catalog['version'])}</p>
<div class="controls"><input id="q" placeholder="检索：塔、中轴、纹样、夜景、Xerox…"><select id="category"><option value="">全部类别</option>{category_options}</select><select id="tier"><option value="">全部层级</option>{tier_options}</select></div></header>
<main><div class="section-title"><h2>Tokens</h2><span class="count" id="tokenCount"></span></div><section class="grid" id="tokenGrid">{''.join(cards)}</section>
<div class="section-title"><h2>Recipes</h2><span class="count" id="recipeCount"></span></div><section class="recipe-grid" id="recipeGrid">{''.join(recipe_cards)}</section>
<div class="section-title"><h2>Reference coverage</h2><span class="count" id="coverageCount"></span></div><section class="coverage-grid">{''.join(coverage_cards)}</section></main>
<script>
const q=document.querySelector('#q'),cat=document.querySelector('#category'),tier=document.querySelector('#tier');
function apply(){{const n=q.value.trim().toLowerCase();let tc=0,rc=0,cc=0;document.querySelectorAll('.card').forEach(el=>{{const ok=(!n||el.dataset.search.includes(n))&&(!cat.value||el.dataset.category===cat.value)&&(!tier.value||el.dataset.tier===tier.value);el.classList.toggle('hidden',!ok);if(ok)tc++}});document.querySelectorAll('.recipe').forEach(el=>{{const ok=(!n||el.dataset.search.includes(n))&&!cat.value&&!tier.value;el.classList.toggle('hidden',!ok);if(ok)rc++}});document.querySelectorAll('.coverage-card').forEach(el=>{{const ok=(!n||el.dataset.search.includes(n))&&!cat.value&&!tier.value;el.classList.toggle('hidden',!ok);if(ok)cc++}});document.querySelector('#tokenCount').textContent=tc+' results';document.querySelector('#recipeCount').textContent=rc+' results';document.querySelector('#coverageCount').textContent=cc+' files'}}
[q,cat,tier].forEach(el=>el.addEventListener('input',apply));apply();
</script></body></html>'''


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH)
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="validate token references, recipes and mutex groups")

    query = subparsers.add_parser("query", help="query tokens")
    query.add_argument("--category")
    query.add_argument("--tier", choices=sorted(TIERS))
    query.add_argument("--tag")
    query.add_argument("--search")
    query.add_argument("--compatible-with")
    query.add_argument("--json", action="store_true")

    recipe = subparsers.add_parser("recipe", help="resolve one recipe and its dependencies")
    recipe.add_argument("recipe_id")
    recipe.add_argument("--json", action="store_true")

    suggest = subparsers.add_parser("suggest", help="rank diverse recipe families for photo tags")
    suggest.add_argument("--tag", action="append", default=[], help="repeat for each photo or content tag")
    suggest.add_argument("--exclude", action="append", default=[], help="recipe id to exclude")
    suggest.add_argument("--count", type=int, default=3)
    suggest.add_argument("--maximize-distance", action="store_true", help="maximize style-axis distance across suggestions and history")
    suggest.add_argument("--history", type=Path, help="optional JSON history outside the skill directory")
    suggest.add_argument("--record-history", action="store_true", help="append selected recipe fingerprints to --history")
    suggest.add_argument("--json", action="store_true")

    tags = subparsers.add_parser("tags", help="list the controlled photo-tag vocabulary")
    tags.add_argument("--search")

    render = subparsers.add_parser("render", help="render a standalone searchable HTML catalog")
    render.add_argument("--output", type=Path, required=True)
    render.add_argument("--reference-dir", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        catalog = load_catalog(args.catalog)
        errors = validate_catalog(catalog)
        if errors:
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            return 1

        if args.command == "validate":
            print(
                f"Valid: {len(catalog['tokens'])} tokens, "
                f"{len(catalog.get('recipes', []))} recipes, "
                f"{len(catalog.get('mutex_groups', []))} mutex groups."
            )
        elif args.command == "query":
            results = query_tokens(
                catalog,
                args.category,
                args.tier,
                args.tag,
                args.search,
                args.compatible_with,
            )
            print_tokens(results, args.json)
        elif args.command == "recipe":
            payload = recipe_payload(catalog, args.recipe_id)
            if args.json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(f"{payload['id']}  {payload['label']}")
                print("family:", payload["family"])
                print("signature:", payload["signature"])
                print("sources:", ", ".join(payload["sources"]))
                print("reference assets:")
                for asset in payload["reference_assets"]:
                    print(f"  {asset['quality']}  {asset['path']}")
                print("resolved:")
                for item in payload["resolved_tokens"]:
                    print(f"  {item['id']}  {item['label']}")
                print("optional:", ", ".join(payload["optional"]) or "none")
                print("forbidden:", ", ".join(payload["forbidden"]) or "none")
                print("style:", ", ".join(f"{key}={value}" for key, value in payload["style_fingerprint"].items()))
                for invariant in payload["invariants"]:
                    print("invariant:", invariant)
                if payload["errors"]:
                    for error in payload["errors"]:
                        print("ERROR:", error)
                    return 1
        elif args.command == "suggest":
            if args.count < 1:
                raise ValueError("--count must be at least 1")
            history = load_history(args.history)
            suggestions, metadata = suggest_recipes(
                catalog,
                args.tag,
                set(args.exclude),
                args.count,
                args.maximize_distance,
                history,
            )
            if args.record_history:
                if args.history is None:
                    raise ValueError("--record-history requires --history")
                record_history(args.history, suggestions)
            if args.json:
                print(json.dumps({"suggestions": suggestions, **metadata}, ensure_ascii=False, indent=2))
            elif not suggestions:
                print("No matching recipe families.")
            else:
                if metadata["unmatched_tags"]:
                    print("WARNING unmatched tags: " + ", ".join(metadata["unmatched_tags"]), file=sys.stderr)
                    print("Use `design_tokens.py tags --search <term>` to choose a controlled tag.", file=sys.stderr)
                for item in suggestions:
                    print(f"{item['id']}  {item['label']}  family={item['family']}  score={item['score']}")
                    print(f"  matched: {', '.join(item['matched_tags']) or 'none'}")
                    print(f"  signature: {item['signature']}")
                    print(f"  sources: {', '.join(item['sources'])}")
                    print("  style: " + ", ".join(f"{key}={value}" for key, value in item["style_fingerprint"].items()))
            if args.tag and not metadata["matched_tags"]:
                return 2
        elif args.command == "tags":
            vocabulary, aliases = controlled_tag_payload(catalog)
            needle = (args.search or "").lower()
            for tag in vocabulary:
                if not needle or needle in tag.lower() or any(needle in alias.lower() and target == tag for alias, target in aliases.items()):
                    linked = [alias for alias, target in aliases.items() if target == tag]
                    print(f"{tag}" + (f"  aliases={','.join(linked)}" if linked else ""))
        elif args.command == "render":
            reference_dir = args.reference_dir
            if reference_dir is None:
                candidate = args.catalog.resolve().parents[1] / "assets" / "reference-thumbnails"
                reference_dir = candidate if candidate.is_dir() else None
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_catalog(catalog, reference_dir), encoding="utf-8")
            print(args.output.resolve())
        return 0
    except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
