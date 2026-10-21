#!/usr/bin/env python3
"""Emit scoped token CSS and the shared runtime configuration bridge."""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from pathlib import Path
import sys

from resolve_tokens import (
    _canonical_token_key,
    load_tokens,
    runtime_json,
    validate_tokens,
)


ROOT = Path(__file__).resolve().parents[1]


def _rule(selector: str, values: dict[str, object]) -> str:
    declarations = "\n".join(f"  --ui-{key}: {value};" for key, value in values.items())
    return f"{selector} {{\n{declarations}\n}}"


def _theme_selectors(profile: str | None, theme: str) -> str:
    profile_selector = f'[data-ui-profile="{profile}"]' if profile else ""
    explicit = f'html[data-ui="enterprise"]{profile_selector}[data-theme="{theme}"]'
    if theme == "dark":
        legacy = f'html.dark[data-ui="enterprise"]{profile_selector}:not([data-theme="light"])'
        return f"{explicit},\n{legacy}"
    return explicit


def _css_layer(tokens: dict, values: dict, *, profile: str = "enterprise",
               theme: str = "light", brand: str | None = None) -> dict:
    """Render flat aliases as CSS vars so profile inheritance remains live."""
    result = {}
    for key, value in values.items():
        reference = None
        if isinstance(value, Mapping):
            if set(value) != {"$ref"} or not isinstance(value["$ref"], str):
                raise ValueError(f"CSS layer value must be scalar or atomic $ref: {value!r}")
            reference = value["$ref"]
        elif isinstance(value, str) and value.startswith("@"):
            reference = value
        if reference is not None:
            token_key = _canonical_token_key(tokens, reference.lstrip("@"))
            if token_key is None:
                raise ValueError(f"CSS layer alias does not resolve to a flat token: {reference}")
            result[key] = f"var(--ui-{token_key})"
        else:
            result[key] = value
    return result


def render_css(tokens: dict) -> str:
    validate_tokens(tokens)
    parts = [
        f"/* Enterprise Workbench UI {tokens['meta']['version']}. Token-only: no resets or component overrides.\n"
        "   Generated from tokens.json by scripts/generate_tokens.py; do not edit by hand.\n"
        "   Profile cascade: enterprise base -> theme -> optional profile -> density.\n"
        "   Explicit brand follows profile and owns action semantics only.\n"
        "   Unsupported profile/theme combinations inherit the declared profile fallback.\n"
        "   Missing brand preserves the profile/theme action palette; explicit brand selectors override it.\n"
        "   Root-scoped tokens inherit into body portals; nested providers must transfer resolved variables. */",
        _rule('html[data-ui="enterprise"]', _css_layer(
            tokens, tokens["common"] | tokens["modes"]["light"], theme="light")),
        _rule(
            'html[data-ui="enterprise"][data-theme="dark"],\n'
            'html.dark[data-ui="enterprise"]:not([data-theme="light"])',
            _css_layer(tokens, tokens["modes"]["dark"], theme="dark"),
        ),
    ]
    enterprise = tokens.get("profiles", {}).get("enterprise", {})
    if enterprise.get("modes", {}).get("dark"):
        parts.append(_rule(_theme_selectors(None, "dark"), _css_layer(
            tokens, enterprise["modes"]["dark"], theme="dark")))
    for name, profile in tokens.get("profiles", {}).items():
        if name == "enterprise":
            continue
        profile_common = profile.get("common", {})
        for theme, values in profile.get("modes", {}).items():
            parts.append(_rule(_theme_selectors(name, theme), _css_layer(
                tokens, profile_common | values, profile=name, theme=theme)))
    for name, brand in tokens.get("brands", {}).items():
        base = brand.get("tokens", {})
        if base:
            parts.append(_rule(
                f'html[data-ui="enterprise"][data-ui-brand="{name}"]:not([data-theme="dark"]),\n'
                f'html[data-ui="enterprise"][data-ui-brand="{name}"][data-theme="light"]',
                _css_layer(tokens, base, theme="light", brand=name),
            ))
        for theme, values in brand.get("modes", {}).items():
            parts.append(_rule(
                f'html[data-ui="enterprise"][data-ui-brand="{name}"][data-theme="{theme}"],\n'
                f'html.dark[data-ui="enterprise"][data-ui-brand="{name}"]:not([data-theme="light"])',
                _css_layer(tokens, values, theme=theme, brand=name),
            ))
    for name, values in tokens.get("densities", {}).items():
        if values:
            # Profile selectors carry data-ui, data-ui-profile and data-theme.
            # Keep compact density at the same specificity so it wins for both
            # profile roots and legacy roots without a profile attribute.
            density_selector = (
                f'html[data-ui="enterprise"][data-density="{name}"][data-ui-profile],\n'
                f'html[data-ui="enterprise"][data-density="{name}"]:not([data-ui-profile]),\n'
                f'html.dark[data-ui="enterprise"][data-density="{name}"][data-ui-profile]:not([data-theme="light"]),\n'
                f'html.dark[data-ui="enterprise"][data-density="{name}"]:not([data-ui-profile]):not([data-theme="light"])'
            )
            parts.append(_rule(density_selector, _css_layer(
                tokens, values, theme="light")))
    return "\n\n".join(parts) + "\n"


def render_runtime_js(config_text: str) -> str:
    return (
        "/* Generated from tokens.json by scripts/generate_tokens.py; do not edit by hand. */\n"
        "window.__UI_DESIGN_CONFIG__ = " + config_text + ";\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, default=ROOT / "assets" / "tokens.json")
    parser.add_argument("--output", type=Path, default=ROOT / "assets" / "tokens.css")
    parser.add_argument("--config-output", type=Path, default=ROOT / "assets" / "design-config.json")
    parser.add_argument("--config-js-output", type=Path, default=ROOT / "assets" / "design-config.js")
    parser.add_argument("--check", action="store_true",
                        help="Fail if CSS/runtime files are missing or stale; do not write.")
    args = parser.parse_args()
    tokens = load_tokens(args.tokens)
    expected_css = render_css(tokens)
    expected_config = runtime_json(tokens)
    expected_js = render_runtime_js(expected_config)
    expected = {
        args.output: expected_css,
        args.config_output: expected_config,
        args.config_js_output: expected_js,
    }
    stale = [path for path, content in expected.items()
             if not path.exists() or path.read_text(encoding="utf-8") != content]
    if args.check:
        if stale:
            print("Generated token outputs are stale: " + ", ".join(str(path) for path in stale), file=sys.stderr)
            return 1
        print("Token CSS and runtime configuration match JSON.")
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"Generated {args.output.name}, {args.config_output.name}, and {args.config_js_output.name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
