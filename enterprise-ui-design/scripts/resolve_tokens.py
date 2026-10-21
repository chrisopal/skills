#!/usr/bin/env python3
"""Resolve and validate the Enterprise UI token configuration.

The resolver is intentionally dependency-free and is the one source used by
the CSS emitter and the runtime configuration bridge.  A requested brand,
profile, theme or density is never allowed to leak an unresolved reference or
an unsupported combination into the generated runtime table.
"""
from __future__ import annotations

import copy
import itertools
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


ROOT = Path(__file__).resolve().parents[1]
AXES = ("brand", "profile", "theme", "density")
BRAND_KEYS = {
    "brand",
    "action-text",
    "action-text-hover",
    "action-solid",
    "action-solid-hover",
    "on-action",
    "selected-bg",
    "focus-ring",
}
STATUS_KEYS = {"success", "warning", "danger", "danger-bg", "danger-border"}
SERIES_PREFIX = "data-series-"
DENSITY_KEYS = {
    "layout-panel-inset",
    "layout-field-gap",
    "density-control-height",
    "density-cell-padding-block",
    "density-cell-padding-inline",
}
REF_PATTERN = re.compile(r"^@([A-Za-z0-9_.-]+)$")
CSS_REF_PATTERN = re.compile(r"var\(--ui-([A-Za-z0-9_-]+)\)")
TRACKING_PATTERN = re.compile(r"^(?:0|\d+(?:\.\d+)?)(?:px|em|rem|%)?$")
NUMERIC_VARIANTS = {"normal", "tabular-nums"}
FONT_ROLE_NAMES = {
    "body", "label", "meta", "title", "section", "metric", "reading",
    "nav", "table-heading", "record", "unit", "code",
}


class TokenConfigError(ValueError):
    """Raised when a token configuration cannot be safely resolved."""


def load_tokens(path: Path | str = ROOT / "assets" / "tokens.json") -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _profile_names(tokens: Mapping[str, Any]) -> list[str]:
    return list(tokens.get("profiles", {}))


def _theme_names(tokens: Mapping[str, Any]) -> list[str]:
    return list(tokens.get("modes", {}))


def _density_names(tokens: Mapping[str, Any]) -> list[str]:
    return list(tokens.get("densities", {}))


def _brand_names(tokens: Mapping[str, Any]) -> list[str]:
    return list(tokens.get("brands", {}))


def _all_token_keys(tokens: Mapping[str, Any]) -> set[str]:
    keys = set(tokens.get("common", {}))
    for values in tokens.get("modes", {}).values():
        keys.update(values)
    for profile in tokens.get("profiles", {}).values():
        keys.update(profile.get("common", {}))
        for values in profile.get("modes", {}).values():
            keys.update(values)
    for brand in tokens.get("brands", {}).values():
        keys.update(brand.get("tokens", {}))
        for values in brand.get("modes", {}).values():
            keys.update(values)
    for values in tokens.get("densities", {}).values():
        keys.update(values)
    return keys


def _iter_values(tokens: Mapping[str, Any]) -> Iterable[tuple[str, Any]]:
    yield from ((f"common.{key}", value) for key, value in tokens.get("common", {}).items())
    for theme, values in tokens.get("modes", {}).items():
        yield from ((f"modes.{theme}.{key}", value) for key, value in values.items())
    for profile, definition in tokens.get("profiles", {}).items():
        yield from ((f"profiles.{profile}.common.{key}", value)
                    for key, value in definition.get("common", {}).items())
        for theme, values in definition.get("modes", {}).items():
            yield from ((f"profiles.{profile}.modes.{theme}.{key}", value)
                        for key, value in values.items())
    for brand, definition in tokens.get("brands", {}).items():
        yield from ((f"brands.{brand}.tokens.{key}", value)
                    for key, value in definition.get("tokens", {}).items())
        for theme, values in definition.get("modes", {}).items():
            yield from ((f"brands.{brand}.modes.{theme}.{key}", value)
                        for key, value in values.items())
    for density, values in tokens.get("densities", {}).items():
        yield from ((f"densities.{density}.{key}", value) for key, value in values.items())


def _walk_values(value: Any, location: str) -> Iterable[tuple[str, Any]]:
    """Yield every nested value so recipes are validated like token layers."""
    if isinstance(value, Mapping):
        if set(value) == {"$ref"}:
            # A reference object is an atomic value.  Keeping it intact lets
            # validation preserve the source path and detect self-cycles.
            yield location, value
            return
        for key, child in value.items():
            yield from _walk_values(child, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk_values(child, f"{location}[{index}]")
    else:
        yield location, value


def _iter_all_references(tokens: Mapping[str, Any]) -> Iterable[tuple[str, Any]]:
    for location, value in _iter_values(tokens):
        yield location, value
    for section in ("aliases", "semantics", "components", "layout"):
        if section in tokens:
            yield from _walk_values(tokens[section], section)


def _ref_target(tokens: Mapping[str, Any], ref: str) -> Any:
    aliases = tokens.get("aliases", {})
    if ref in aliases:
        return aliases[ref]
    parts = ref.split(".")
    current: Any = tokens
    for part in parts:
        if not isinstance(current, Mapping) or part not in current:
            raise TokenConfigError(f"missing token reference: {ref}")
        current = current[part]
    return current


def _resolve_ref(tokens: Mapping[str, Any], ref: str, stack: tuple[str, ...] = ()) -> Any:
    ref = ref.lstrip("@")
    if ref in stack:
        cycle = " -> ".join((*stack, ref))
        raise TokenConfigError(f"cyclic token reference: {cycle}")
    target = _ref_target(tokens, ref)
    if ref in tokens.get("aliases", {}):
        if not isinstance(target, str):
            raise TokenConfigError(f"alias must point to a token path: {ref}")
        target_ref = target[1:] if target.startswith("@") else target
        return _resolve_ref(tokens, target_ref, (*stack, ref))
    if isinstance(target, Mapping) and set(target) == {"$ref"}:
        target_ref = target["$ref"]
        if not isinstance(target_ref, str):
            raise TokenConfigError(f"invalid token reference: {target_ref!r}")
        return _resolve_ref(tokens, target_ref, (*stack, ref))
    if isinstance(target, str):
        match = REF_PATTERN.fullmatch(target)
        if match:
            return _resolve_ref(tokens, match.group(1), (*stack, ref))
    return target


def _canonical_token_key(tokens: Mapping[str, Any], ref: str, stack: tuple[str, ...] = ()) -> str | None:
    """Map an alias or token path to its effective flat token key when possible."""
    if ref in stack:
        cycle = " -> ".join((*stack, ref))
        raise TokenConfigError(f"cyclic token reference: {cycle}")
    if ref in tokens.get("aliases", {}):
        target = tokens["aliases"][ref]
        if not isinstance(target, str):
            raise TokenConfigError(f"alias must point to a token path: {ref}")
        return _canonical_token_key(tokens, target.lstrip("@"), (*stack, ref))
    parts = ref.split(".")
    if len(parts) == 2 and parts[0] in {"common", "modes", "profiles", "brands", "densities"}:
        return parts[-1]
    if len(parts) == 3 and parts[0] in {"modes", "densities"}:
        return parts[-1]
    if len(parts) == 4 and parts[0] in {"profiles", "brands"}:
        return parts[-1]
    return None


def _nested_target(tokens: Mapping[str, Any], ref: str) -> Any:
    parts = ref.split(".")
    current: Any = tokens
    for part in parts:
        if not isinstance(current, Mapping) or part not in current:
            raise TokenConfigError(f"missing token reference: {ref}")
        current = current[part]
    return current


def _resolve_alias_value(tokens: Mapping[str, Any], value: Any, stack: tuple[str, ...] = ()) -> Any:
    if isinstance(value, Mapping) and set(value) == {"$ref"}:
        ref = value["$ref"]
        if not isinstance(ref, str):
            raise TokenConfigError(f"invalid token reference: {ref!r}")
        return _resolve_ref(tokens, ref, stack)
    if isinstance(value, str):
        match = REF_PATTERN.fullmatch(value)
        if match:
            return _resolve_ref(tokens, match.group(1), stack)
    return value


def validate_references(tokens: Mapping[str, Any]) -> None:
    for location, value in _iter_all_references(tokens):
        try:
            _resolve_alias_value(tokens, value, (location,))
        except TokenConfigError as exc:
            raise TokenConfigError(f"{location}: {exc}") from exc
    for alias in tokens.get("aliases", {}):
        try:
            _resolve_ref(tokens, alias, (f"aliases.{alias}",))
        except TokenConfigError as exc:
            raise TokenConfigError(f"aliases.{alias}: {exc}") from exc
    css_sources: dict[str, list[Any]] = {}
    for location, value in _iter_values(tokens):
        key = location.rsplit(".", 1)[-1]
        css_sources.setdefault(key, []).append(value)

    def check_css_key(key: str, stack: tuple[str, ...]) -> None:
        if key in stack:
            cycle = " -> ".join((*stack, key))
            raise TokenConfigError(f"cyclic CSS token reference: {cycle}")
        if key not in _all_token_keys(tokens):
            raise TokenConfigError(f"missing CSS token reference: {key}")
        for source in css_sources.get(key, []):
            for nested in CSS_REF_PATTERN.findall(source):
                check_css_key(nested, (*stack, key))

    for location, value in _iter_all_references(tokens):
        if not isinstance(value, str):
            continue
        for key in CSS_REF_PATTERN.findall(value):
            try:
                check_css_key(key, ())
            except TokenConfigError as exc:
                raise TokenConfigError(f"{location}: {exc}") from exc


def validate_ownership(tokens: Mapping[str, Any]) -> None:
    """Validate that axis-specific overrides stay inside their ownership.

    The explicit brand contract is deliberately narrow: it may change action
    semantics, but it may never replace business statuses or chart series.
    Density owns only the configured density keys, keeping typography and
    theme/profile semantics independent.
    """
    brands = tokens.get("brands", {})
    for brand, definition in brands.items():
        values = set(definition.get("tokens", {}))
        values.update(key for mode in definition.get("modes", {}).values() for key in mode)
        unknown = values - BRAND_KEYS
        if unknown:
            raise TokenConfigError(
                f"brands.{brand} owns unsupported tokens: {', '.join(sorted(unknown))}"
            )
        forbidden = values & (STATUS_KEYS | {key for key in _all_token_keys(tokens)
                                             if key.startswith(SERIES_PREFIX)})
        if forbidden:
            raise TokenConfigError(
                f"brands.{brand} cannot override status/series tokens: {', '.join(sorted(forbidden))}"
            )
    declared_density = tokens.get("ownership", {}).get("density", [])
    density_keys = set(declared_density) if declared_density else DENSITY_KEYS
    for density, values in tokens.get("densities", {}).items():
        unknown = set(values) - density_keys
        if unknown:
            raise TokenConfigError(
                f"densities.{density} owns non-density tokens: {', '.join(sorted(unknown))}"
            )
        missing = set(values) - set(tokens.get("common", {}))
        if missing:
            raise TokenConfigError(
                f"densities.{density} references undefined common tokens: {', '.join(sorted(missing))}"
            )
    for profile, definition in tokens.get("profiles", {}).items():
        fallback = definition.get("fallback")
        if fallback and fallback not in tokens.get("profiles", {}):
            raise TokenConfigError(f"profiles.{profile}.fallback is unknown: {fallback}")
        supported = definition.get("supported-themes", [])
        unknown = set(supported) - set(_theme_names(tokens))
        if unknown:
            raise TokenConfigError(
                f"profiles.{profile} supports unknown themes: {', '.join(sorted(unknown))}"
            )
        unknown_modes = set(definition.get("modes", {})) - set(supported)
        if unknown_modes:
            raise TokenConfigError(
                f"profiles.{profile} defines unsupported themes: {', '.join(sorted(unknown_modes))}"
            )
        exceptions = tokens.get("ownership", {}).get("profile-brand-exceptions", {})
        allowed_brand_themes = set(exceptions.get(profile, []))
        for theme, values in definition.get("modes", {}).items():
            profile_brand_keys = set(values) & BRAND_KEYS
            if profile_brand_keys and theme not in allowed_brand_themes:
                raise TokenConfigError(
                    f"profiles.{profile}.modes.{theme} cannot override brand tokens: "
                    f"{', '.join(sorted(profile_brand_keys))}"
                )
        profile_brand_keys = set(definition.get("common", {})) & BRAND_KEYS
        if profile_brand_keys:
            raise TokenConfigError(
                f"profiles.{profile}.common cannot override brand tokens: "
                f"{', '.join(sorted(profile_brand_keys))}"
            )


def validate_semantics(tokens: Mapping[str, Any]) -> None:
    semantics = tokens.get("semantics", {})
    font = semantics.get("font", {})
    roles = font.get("roles", {})
    if set(roles) != FONT_ROLE_NAMES:
        missing = FONT_ROLE_NAMES - set(roles)
        extra = set(roles) - FONT_ROLE_NAMES
        detail = []
        if missing:
            detail.append("missing=" + ",".join(sorted(missing)))
        if extra:
            detail.append("unknown=" + ",".join(sorted(extra)))
        raise TokenConfigError("semantics.font.roles schema mismatch: " + "; ".join(detail))
    for role, definition in roles.items():
        required = {"family", "size", "line", "weight", "tracking", "numeric"}
        if set(definition) != required:
            raise TokenConfigError(f"semantics.font.roles.{role} must define {sorted(required)}")
        tracking = definition["tracking"]
        if not isinstance(tracking, str) or not TRACKING_PATTERN.fullmatch(tracking):
            raise TokenConfigError(f"semantics.font.roles.{role}.tracking must be non-negative")
        numeric = definition["numeric"]
        if numeric not in NUMERIC_VARIANTS:
            raise TokenConfigError(
                f"semantics.font.roles.{role}.numeric must be one of {sorted(NUMERIC_VARIANTS)}"
            )
    if font.get("unit") != "px":
        raise TokenConfigError("semantics.font.unit must be px")


def validate_tokens(tokens: Mapping[str, Any]) -> None:
    if not isinstance(tokens, Mapping):
        raise TokenConfigError("token document must be an object")
    meta = tokens.get("meta")
    if not isinstance(meta, Mapping) or not isinstance(meta.get("version"), str):
        raise TokenConfigError("meta.version is required")
    for section in ("common", "modes", "profiles", "densities"):
        if section not in tokens or not isinstance(tokens[section], Mapping):
            raise TokenConfigError(f"missing token section: {section}")
    if "brands" not in tokens or not isinstance(tokens["brands"], Mapping) or not tokens["brands"]:
        raise TokenConfigError("brands must be a non-empty object")
    if "light" not in tokens["modes"] or "dark" not in tokens["modes"]:
        raise TokenConfigError("modes.light and modes.dark are required")
    if "standard" not in tokens["densities"] or "compact" not in tokens["densities"]:
        raise TokenConfigError("densities.standard and densities.compact are required")
    defaults = tokens.get("defaults", {})
    if not isinstance(defaults, Mapping):
        raise TokenConfigError("defaults must be an object")
    if defaults.get("profile", "enterprise") not in tokens.get("profiles", {}):
        raise TokenConfigError("defaults.profile is unknown")
    if defaults.get("theme", "light") not in tokens.get("modes", {}):
        raise TokenConfigError("defaults.theme is unknown")
    if defaults.get("density", "standard") not in tokens.get("densities", {}):
        raise TokenConfigError("defaults.density is unknown")
    if defaults.get("brand", "blue") not in tokens.get("brands", {}):
        raise TokenConfigError("defaults.brand is unknown")
    validate_references(tokens)
    validate_ownership(tokens)
    validate_semantics(tokens)


def _luminance(color: str) -> float:
    if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
        raise TokenConfigError(f"contrast checks require six-digit hex colors: {color!r}")
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045
              else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return sum(channel * weight for channel, weight in zip(linear, (0.2126, 0.7152, 0.0722)))


def contrast_ratio(foreground: str, background: str) -> float:
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def validate_contrast(tokens: Mapping[str, Any]) -> None:
    """Check declared foreground/background pairs for every supported axis tuple."""
    pairs = tokens.get("contrast-pairs", [])
    for brand, profile, theme, density in itertools.product(
        _brand_names(tokens), _profile_names(tokens), _theme_names(tokens), _density_names(tokens)
    ):
        result = resolve_config(tokens, brand=brand, profile=profile, theme=theme, density=density)
        values = result["values"]
        for pair in pairs:
            if len(pair) != 3:
                raise TokenConfigError(f"invalid contrast pair: {pair!r}")
            foreground, background, minimum = pair
            if foreground not in values or background not in values:
                raise TokenConfigError(f"contrast pair references missing token: {pair!r}")
            actual = contrast_ratio(values[foreground], values[background])
            if actual < float(minimum):
                raise TokenConfigError(
                    f"contrast {actual:.2f} < {minimum} for {brand}/{profile}/{theme}/{density}: "
                    f"{foreground} on {background}"
                )


def _fallback_name(tokens: Mapping[str, Any], axis: str, requested: str | None) -> tuple[str, str | None]:
    defaults = tokens.get("defaults", {})
    values = {
        "brand": _brand_names(tokens),
        "profile": _profile_names(tokens),
        "theme": _theme_names(tokens),
        "density": _density_names(tokens),
    }[axis]
    default = defaults.get(axis, values[0] if values else None)
    if requested in values:
        return requested, None
    if axis == "profile" and requested:
        profile = tokens.get("profiles", {}).get(requested, {})
        fallback = profile.get("fallback")
        if fallback in values:
            return fallback, f"profile:{requested}->{fallback}"
    return default, f"{axis}:{requested}->{default}" if requested is not None else None


def _resolve_profile_theme(tokens: Mapping[str, Any], profile: str, theme: str) -> tuple[str, str, list[str]]:
    fallback_notes: list[str] = []
    definition = tokens["profiles"][profile]
    supported = definition.get("supported-themes", _theme_names(tokens))
    if theme in supported:
        return profile, theme, fallback_notes
    fallback_profile = definition.get("fallback") or tokens.get("defaults", {}).get("profile", "enterprise")
    if fallback_profile not in tokens.get("profiles", {}):
        fallback_profile = tokens.get("defaults", {}).get("profile", "enterprise")
    fallback_theme = theme if theme in tokens.get("modes", {}) else tokens.get("defaults", {}).get("theme", "light")
    fallback_supported = tokens["profiles"].get(fallback_profile, {}).get(
        "supported-themes", _theme_names(tokens)
    )
    if fallback_theme not in fallback_supported:
        fallback_theme = tokens.get("defaults", {}).get("theme", "light")
        if fallback_theme not in fallback_supported:
            fallback_theme = fallback_supported[0]
    fallback_notes.append(f"profile-theme:{profile}/{theme}->{fallback_profile}/{fallback_theme}")
    return fallback_profile, fallback_theme, fallback_notes


def _resolve_effective_value(
    value: Any,
    tokens: Mapping[str, Any],
    resolved: Mapping[str, Any],
    stack: tuple[str, ...] = (),
) -> Any:
    """Resolve nested aliases and CSS custom-property references recursively."""
    if isinstance(value, Mapping):
        if set(value) == {"$ref"}:
            ref = value["$ref"]
            if not isinstance(ref, str):
                raise TokenConfigError(f"invalid effective token reference: {ref!r}")
            ref = ref.lstrip("@")
            if ref in stack:
                cycle = " -> ".join((*stack, ref))
                raise TokenConfigError(f"cyclic effective token reference: {cycle}")
            return _resolve_effective_value(
                ref if ref.startswith("@") else "@" + ref,
                tokens,
                resolved,
                stack,
            )
        return {key: _resolve_effective_value(child, tokens, resolved, stack)
                for key, child in value.items()}
    if isinstance(value, list):
        return [_resolve_effective_value(child, tokens, resolved, stack) for child in value]
    if not isinstance(value, str):
        return value

    match = REF_PATTERN.fullmatch(value)
    if match:
        ref = match.group(1)
        if ref in stack:
            cycle = " -> ".join((*stack, ref))
            raise TokenConfigError(f"cyclic effective token reference: {cycle}")
        key = _canonical_token_key(tokens, ref)
        if key is not None:
            if key in stack:
                cycle = " -> ".join((*stack, key))
                raise TokenConfigError(f"cyclic effective token reference: {cycle}")
            if key not in resolved:
                raise TokenConfigError(f"missing effective token reference: {key}")
            return _resolve_effective_value(resolved[key], tokens, resolved, (*stack, key))
        target = _nested_target(tokens, ref)
        return _resolve_effective_value(target, tokens, resolved, (*stack, ref))

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in resolved:
            raise TokenConfigError(f"missing effective CSS token reference: {key}")
        if key in stack:
            cycle = " -> ".join((*stack, key))
            raise TokenConfigError(f"cyclic effective CSS token reference: {cycle}")
        return str(_resolve_effective_value(resolved[key], tokens, resolved, (*stack, key)))

    return CSS_REF_PATTERN.sub(replace, value)


def _resolve_recipe(tokens: Mapping[str, Any], recipe: Mapping[str, Any], values: Mapping[str, Any]) -> dict[str, Any]:
    return _resolve_effective_value(recipe, tokens, values)


def resolve_config(
    tokens: Mapping[str, Any],
    *,
    brand: str | None = None,
    profile: str | None = None,
    theme: str | None = None,
    density: str | None = None,
) -> dict[str, Any]:
    """Resolve one requested configuration to a fully concrete value map."""
    validate_tokens(tokens)
    defaults = tokens.get("defaults", {})
    requested = {
        "brand": brand if brand is not None else defaults.get("brand", "blue"),
        "profile": profile if profile is not None else defaults.get("profile", "enterprise"),
        "theme": theme if theme is not None else defaults.get("theme", "light"),
        "density": density if density is not None else defaults.get("density", "standard"),
    }
    fallback_notes: list[str] = []
    effective: dict[str, str] = {}
    for axis in AXES:
        value, note = _fallback_name(tokens, axis, requested[axis])
        if value is None:
            raise TokenConfigError(f"no configured value for axis: {axis}")
        effective[axis] = value
        if note:
            fallback_notes.append(note)
    effective["profile"], effective["theme"], profile_notes = _resolve_profile_theme(
        tokens, effective["profile"], effective["theme"]
    )
    fallback_notes.extend(profile_notes)

    values: dict[str, Any] = copy.deepcopy(tokens.get("common", {}))
    values.update(tokens.get("modes", {}).get(effective["theme"], {}))
    profile_definition = tokens["profiles"].get(effective["profile"], {})
    values.update(profile_definition.get("common", {}))
    values.update(profile_definition.get("modes", {}).get(effective["theme"], {}))

    # A missing brand is intentional: the profile/theme palette remains intact,
    # which preserves the legacy analytics action colours. Explicit brand
    # selection is the only operation that applies brand action semantics.
    brand_applied = brand is not None
    if brand_applied:
        brand_definition = tokens["brands"][effective["brand"]]
        values.update(brand_definition.get("tokens", {}))
        values.update(brand_definition.get("modes", {}).get(effective["theme"], {}))
    values.update(tokens.get("densities", {}).get(effective["density"], {}))

    # Resolve aliases and CSS var references against the complete effective map.
    raw_values = values
    values = {
        key: _resolve_effective_value(value, tokens, raw_values, (key,))
        for key, value in raw_values.items()
    }
    semantics = _resolve_recipe(tokens, tokens.get("semantics", {}), values)
    components = _resolve_recipe(tokens, tokens.get("components", {}), values)
    layout = _resolve_recipe(tokens, tokens.get("layout", {}), values)

    return {
        "requested": requested,
        "effective": effective,
        "brandApplied": brand_applied,
        "fallbacks": fallback_notes,
        "values": values,
        "semantics": semantics,
        "components": components,
        "layout": layout,
    }


def _combination_key(config: Mapping[str, str]) -> str:
    return "/".join(config[axis] for axis in AXES)


def build_runtime_config(tokens: Mapping[str, Any]) -> dict[str, Any]:
    validate_tokens(tokens)
    defaults = tokens.get("defaults", {"brand": "blue", "profile": "enterprise", "theme": "light", "density": "standard"})
    default_resolution = resolve_config(tokens)
    combinations: list[dict[str, Any]] = []
    for values in itertools.product(
        _brand_names(tokens), _profile_names(tokens), _theme_names(tokens), _density_names(tokens)
    ):
        requested = dict(zip(AXES, values))
        resolved = resolve_config(tokens, **requested)
        combinations.append({
            "key": _combination_key(requested),
            "requested": resolved["requested"],
            "effective": resolved["effective"],
            "fallbacks": resolved["fallbacks"],
            "supported": not resolved["fallbacks"],
            "values": resolved["values"],
            "semantics": resolved["semantics"],
            "components": resolved["components"],
            "layout": resolved["layout"],
        })
    profile_metadata = {}
    for name, definition in tokens.get("profiles", {}).items():
        profile_metadata[name] = {
            "label": definition.get("label", name),
            "supportedThemes": definition.get("supported-themes", []),
            "fallback": definition.get("fallback", defaults.get("profile", "enterprise")),
        }
    return {
        "schema": "enterprise-ui-design/config/v1",
        "meta": tokens.get("meta", {}),
        "defaults": {
            "ui": "enterprise",
            "brand": defaults.get("brand", "blue"),
            "profile": defaults.get("profile", "enterprise"),
            "theme": defaults.get("theme", "light"),
            "density": defaults.get("density", "standard"),
            "effective": default_resolution["effective"],
            "values": default_resolution["values"],
            "semantics": default_resolution["semantics"],
            "components": default_resolution["components"],
            "layout": default_resolution["layout"],
        },
        "supported": {
            "brands": {
                name: {"label": definition.get("label", name)}
                for name, definition in tokens.get("brands", {}).items()
            },
            "profiles": profile_metadata,
            "themes": _theme_names(tokens),
            "densities": _density_names(tokens),
        },
        "fallbacks": {
            "brand": defaults.get("brand", "blue"),
            "profile": defaults.get("profile", "enterprise"),
            "theme": defaults.get("theme", "light"),
            "density": defaults.get("density", "standard"),
            "profileTheme": {
                name: {
                    theme: resolve_config(tokens, profile=name, theme=theme)["effective"]
                    for theme in _theme_names(tokens)
                }
                for name in _profile_names(tokens)
            },
        },
        "ownership": copy.deepcopy(tokens.get("ownership", {})),
        "aliases": copy.deepcopy(tokens.get("aliases", {})),
        "semantics": copy.deepcopy(tokens.get("semantics", {})),
        "components": copy.deepcopy(tokens.get("components", {})),
        "layout": copy.deepcopy(tokens.get("layout", {})),
        "combinations": combinations,
    }


def runtime_json(tokens: Mapping[str, Any]) -> str:
    return json.dumps(build_runtime_config(tokens), ensure_ascii=False, indent=2, sort_keys=False) + "\n"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokens", type=Path, default=ROOT / "assets" / "tokens.json")
    args = parser.parse_args()
    config = build_runtime_config(load_tokens(args.tokens))
    print(json.dumps(config, ensure_ascii=False, indent=2))
