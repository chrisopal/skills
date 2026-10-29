"""Regression tests for the v1.3 resolver and runtime bridge."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from resolve_tokens import (  # noqa: E402
    TokenConfigError,
    build_runtime_config,
    load_tokens,
    resolve_config,
    validate_references,
    validate_tokens,
)
from generate_tokens import render_css  # noqa: E402


class RuntimeConfigContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tokens = load_tokens(ROOT / "assets" / "tokens.json")
        cls.runtime = build_runtime_config(cls.tokens)

    def test_generated_json_matches_runtime_shape(self):
        disk = json.loads((ROOT / "assets" / "design-config.json").read_text(encoding="utf-8"))
        self.assertEqual(disk, self.runtime)
        self.assertEqual(disk["schema"], "enterprise-ui-design/config/v1")
        self.assertEqual(set(disk["defaults"]), {
            "ui", "brand", "profile", "theme", "density", "effective", "values",
            "semantics", "components", "layout",
        })
        self.assertEqual(len(disk["combinations"]), 80)
        legacy = [c for c in disk["combinations"] if c["requested"]["brand"] in ("blue", "teal") and c["requested"]["profile"] in ("enterprise", "analytics", "precision")]
        self.assertEqual(len(legacy), 24)

    def test_generated_js_is_the_same_config_for_no_flash_load(self):
        source = (ROOT / "assets" / "design-config.js").read_text(encoding="utf-8")
        prefix = "window.__UI_DESIGN_CONFIG__ = "
        self.assertIn(prefix, source)
        payload = source.split(prefix, 1)[1].rsplit(";\n", 1)[0]
        self.assertEqual(json.loads(payload), self.runtime)

    def test_values_are_fully_resolved_and_semantic_axes_are_present(self):
        for combination in self.runtime["combinations"]:
            self.assertFalse(any("var(--ui-" in str(value) for value in combination["values"].values()))
        self.assertIn("font", self.runtime["semantics"])
        self.assertIn("roles", self.runtime["semantics"]["font"])
        self.assertEqual(self.runtime["combinations"][0]["semantics"]["font"]["roles"]["title"]["size"], "24px")
        self.assertIn("button", self.runtime["components"])
        self.assertIn("page", self.runtime["layout"])

    def test_css_consumer_aliases_follow_effective_profile_and_density(self):
        roles = ("body", "label", "meta", "title", "section", "metric", "reading",
                 "nav", "table-heading", "record", "unit", "code")
        properties = ("family", "size", "weight", "line", "tracking", "numeric")
        common = self.tokens["common"]
        for role in roles:
            for property_name in properties:
                self.assertIn(f"type-{role}-{property_name}", common)

        precision = resolve_config(self.tokens, profile="precision", theme="light", density="compact")
        self.assertEqual(precision["values"]["type-title-size"], "24px")
        self.assertEqual(precision["values"]["type-title-weight"], "700")
        self.assertEqual(precision["values"]["type-title-line"], "1.25")
        self.assertEqual(precision["values"]["type-metric-line"], "1.15")
        self.assertEqual(precision["values"]["type-title-numeric"], "normal")
        self.assertEqual(precision["values"]["type-metric-numeric"], "tabular-nums")
        for role in ("body", "label", "meta", "title", "section", "metric", "reading",
                     "nav", "table-heading", "record", "unit", "code"):
            self.assertEqual(precision["values"][f"type-{role}-tracking"], "0")
        self.assertEqual(precision["values"]["type-section-line"], "1.4")
        self.assertEqual(precision["values"]["type-body-size"], "14px")
        self.assertEqual(precision["values"]["z-dialog"], "200")
        self.assertEqual(precision["values"]["focus-offset"], "2px")
        self.assertEqual(precision["values"]["motion-standard"], "220ms")

        css = (ROOT / "assets" / "tokens.css").read_text(encoding="utf-8")
        self.assertIn("--ui-type-title-size: var(--ui-font-title);", css)
        self.assertIn("--ui-type-title-line: var(--ui-line-title);", css)
        self.assertIn("--ui-z-dialog: 200;", css)

    def test_effective_recipes_follow_profile_and_density(self):
        precision = resolve_config(self.tokens, profile="precision", theme="light", density="compact")
        self.assertEqual(precision["semantics"]["font"]["roles"]["title"]["weight"], "700")
        self.assertEqual(precision["components"]["button"]["height"], "28px")
        self.assertEqual(precision["components"]["panel"]["inset"], "16px")
        self.assertEqual(precision["components"]["table"]["cellPaddingBlock"], "8px")
        self.assertEqual(precision["layout"]["section"]["gap"], "28px")

    def test_unknown_values_fall_back_without_partial_resolution(self):
        resolved = resolve_config(
            self.tokens,
            brand="unknown-brand",
            profile="unknown-profile",
            theme="unknown-theme",
            density="unknown-density",
        )
        self.assertEqual(resolved["effective"], {
            "brand": "blue", "profile": "enterprise", "theme": "light", "density": "standard"
        })
        self.assertTrue(resolved["fallbacks"])
        self.assertEqual(resolved["values"]["font-body"], "14px")

    def test_analytics_missing_brand_keeps_legacy_action_palette(self):
        missing = resolve_config(self.tokens, profile="analytics", theme="dark")
        explicit = resolve_config(self.tokens, brand="blue", profile="analytics", theme="dark")
        self.assertFalse(missing["brandApplied"])
        self.assertEqual(missing["values"]["action-text"], "#95B7FF")
        self.assertNotEqual(explicit["values"]["action-text"], missing["values"]["action-text"])

    def test_alias_missing_and_cycle_are_rejected(self):
        missing = copy.deepcopy(self.tokens)
        missing["aliases"]["broken"] = "common.does-not-exist"
        with self.assertRaises(TokenConfigError):
            validate_references(missing)

        cycle = copy.deepcopy(self.tokens)
        cycle["aliases"]["cycle-a"] = "cycle-b"
        cycle["aliases"]["cycle-b"] = "cycle-a"
        with self.assertRaises(TokenConfigError):
            validate_references(cycle)

        css_cycle = copy.deepcopy(self.tokens)
        css_cycle["common"]["cycle-a"] = "var(--ui-cycle-b)"
        css_cycle["common"]["cycle-b"] = "var(--ui-cycle-a)"
        with self.assertRaises(TokenConfigError):
            validate_tokens(css_cycle)

        css_missing = copy.deepcopy(self.tokens)
        css_missing["common"]["missing-ref"] = "var(--ui-no-such-token)"
        with self.assertRaises(TokenConfigError):
            validate_tokens(css_missing)

        mapping_ref = copy.deepcopy(self.tokens)
        mapping_ref["components"]["ref-check"] = {"value": {"$ref": "common.font-body"}}
        self.assertEqual(
            resolve_config(mapping_ref)["components"]["ref-check"]["value"],
            "14px",
        )
        mapping_ref["common"]["mapping-ref"] = {"$ref": "common.font-body"}
        self.assertIn("--ui-mapping-ref: var(--ui-font-body);", render_css(mapping_ref))

        flat_alias = copy.deepcopy(self.tokens)
        flat_alias["common"]["proof-alias"] = "@common.weight-page-title"
        self.assertEqual(
            resolve_config(flat_alias, profile="precision")["values"]["proof-alias"],
            "700",
        )
        self.assertIn("--ui-proof-alias: var(--ui-weight-page-title);", render_css(flat_alias))

        nested_cycle = copy.deepcopy(self.tokens)
        nested_cycle["components"]["cycle"] = {"$ref": "components.cycle"}
        with self.assertRaises(TokenConfigError):
            validate_tokens(nested_cycle)

        dangling_nested = copy.deepcopy(self.tokens)
        dangling_nested["layout"]["broken"] = {"$ref": "layout.no-such-value"}
        with self.assertRaises(TokenConfigError):
            validate_tokens(dangling_nested)

    def test_invalid_ownership_is_rejected_before_generation(self):
        broken = copy.deepcopy(self.tokens)
        broken["densities"]["compact"]["font-body"] = "12px"
        with self.assertRaises(TokenConfigError):
            validate_tokens(broken)

        profile_brand = copy.deepcopy(self.tokens)
        profile_brand["profiles"]["precision"]["modes"]["light"]["action-text"] = "#111111"
        with self.assertRaises(TokenConfigError):
            validate_tokens(profile_brand)

    def test_invalid_schema_and_css_aliases_are_rejected(self):
        missing_meta = copy.deepcopy(self.tokens)
        del missing_meta["meta"]["version"]
        with self.assertRaises(TokenConfigError):
            validate_tokens(missing_meta)

        missing_brand = copy.deepcopy(self.tokens)
        del missing_brand["brands"]
        with self.assertRaises(TokenConfigError):
            validate_tokens(missing_brand)

        negative_tracking = copy.deepcopy(self.tokens)
        negative_tracking["semantics"]["font"]["roles"]["record"]["tracking"] = "-0.01em"
        with self.assertRaises(TokenConfigError):
            validate_tokens(negative_tracking)

        invalid_numeric = copy.deepcopy(self.tokens)
        invalid_numeric["semantics"]["font"]["roles"]["title"]["numeric"] = "0"
        with self.assertRaises(TokenConfigError):
            validate_tokens(invalid_numeric)

        alias = copy.deepcopy(self.tokens)
        alias["common"]["test-alias"] = "@common.font-body"
        css = render_css(alias)
        self.assertIn("--ui-test-alias: var(--ui-font-body);", css)


if __name__ == "__main__":
    unittest.main()
