# Effective configuration and migration contract (v1.4)

Use one existing `DESIGN.md` or equivalent project document for durable decisions: operator/task, approved scope and page ledger, token version, brand/profile/theme/density, font policy, library/provider mapping and scoped exceptions. Do not create competing design truths. Values live only in `assets/tokens.json`; generated resources and review evidence are derived.

## Independent dimensions and ownership

| Dimension | Owner | Contract |
|---|---|---|
| Brand | brand/action-text/solid/on-action/hover/selected/focus and opt-in navigation colors | Blue is the default, not a product invariant. Teal is a proof preset; huixin, indigo and violet are additional palette choices on this same brand axis. Never replace danger/success or categorical series with brand. |
| Theme | light/dark semantic palette | Explicit light wins over legacy `.dark`. No `system` mode existed in v1.2; do not invent its persistence/SSR support. |
| Profile | typography emphasis, surfaces, borders, radius and rhythm | Enterprise preserves the existing appearance. Precision supports both themes. Analytics retains dark entry and Enterprise-light fallback. Huixin supports light/dark with fixed common geometry/material recipes and color-only modes. Profile does not change IA, data, permissions or page logic. |
| Density | allowlisted internal controls/cells/panel/field insets | standard/compact; body remains 14px. Narrow layout reflows and keeps touch controls reachable; it never auto-selects compact. |

`common` and `modes` retain the frozen Foundation/public v1 CSS map. Semantic role aliases → component recipes → layout recipes → adapter use these same values; no second palette framework. `scripts/resolve_tokens.py` validates sections, ownership, supported configurations, references and cycles, then resolves one effective map. Order: foundation/common → theme → supported profile (or declared fallback) → **explicit brand** → density → effective alias/component/layout resolution. Unknown axes use generated defaults and return warnings. Custom unvalidated brand input is not inserted as an arbitrary hex; it falls back and requires adding/validating a preset before adoption.

Generated `design-config.json` and synchronous `design-config.js` contain every declared combination, effective configuration and concrete values/recipes. `tokens.css` retains the `--ui-*` interface and legacy missing-brand Analytics action palette. Runtime opt-in selects a validated explicit brand; Analytics remains a profile, not a brand. A newly selected brand wins over legacy profile action colors. Resolve/fallback with the adapter, not arbitrary stylesheet load order.

## One public runtime entry

Load `design-config.js`, then `design-system.js` **before** token/component CSS. The adapter reads one persisted preference key, migrates the previous workbench preference if present, sets root values before first paint, and emits `ui-design-change`. Keep the synchronous local bundle available; a remote font/registry is not required. Host bundlers may import the JSON instead and use their existing no-flash theme bootstrap.

```js
EnterpriseDesign.apply({ brand: 'teal', profile: 'precision', theme: 'dark', density: 'compact' });
const effective = EnterpriseDesign.get();
const unsubscribe = EnterpriseDesign.bridge(config => {
  // Call the installed library's existing theme/provider API with config.values/components.
  // The reference Canvas consumer actually redraws; a library integration needs its own evidence.
});
EnterpriseDesign.transfer(portalRoot); // also supports explicit nested-provider override
```

The adapter updates styles/configuration without replacing business DOM, reloading routes, or resetting local state. Body-mounted native dialog/Tooltip inherits root tokens. For a different nested provider, transfer **effective variables**, not just html-only attributes; do the same on a Shadow host. An iframe/microfrontend needs its own versioned bridge or same-origin provider. The fixture has no iframe, Shadow application, SSR or multi-window requirement; these are integration contracts, not verified host capabilities. Portal destinations and host library APIs must appear in the component mapping.

The runnable reference uses native controls and Canvas; no second component library is installed. Map semantic values to the existing library theme API in one scoped bridge, including Teleport/portal and SVG/Canvas series, axes, tooltip and selection. A provider callback existing in code is not a completed Element Plus/Ant Design integration. Third-party internals and editor document content are outside broad normalization; theme the editor frame through supported APIs.

## Huixin three-layer adoption

Read [framework](huixin-framework.md), [components](huixin-components.md), and [themes](huixin-themes.md) according to scope. These are an explicit Profile exception, not new generic defaults or a second token framework. The imported package's separate framework/theme JSON and `data-hx-theme` runtime are not adopted. `assets/tokens.json` remains the sole authored truth; generated CSS/configuration are derived.

- `profiles.huixin.common` owns framework/component dimensions, typography and material geometry, including shadow offsets/blur and gradient angles. Recipes refer to semantic color roles; no literal colors belong in this common layer.
- `profiles.huixin.modes.light/dark` own color/alpha roles only. Changing a mode must not change geometry, typography, blur radius, shadow offset or gradient angle.
- `brands.huixin`, `brands.indigo` and `brands.violet` use the existing explicit brand dimension. Brand choices preserve status/data-series separation and never change framework/component geometry. No standalone Huixin palette adapter or storage key is added.
- Source aliases are normalized: `row-height: 52px` yields to canonical `table-row-height: 56px` (compact 44px); `donut-size: 128px` yields to canonical `chart-donut-size: 200px`. Do not maintain competing values to resemble different source files.

```js
// Initial adoption: choose all independent dimensions intentionally.
EnterpriseDesign.apply({ profile: 'huixin', brand: 'violet', theme: 'dark', density: 'standard' });
// Palette/mode controls update only color dimensions and retain active Profile/density.
EnterpriseDesign.apply({ brand: 'indigo', theme: 'light' });
```

Use the existing `EnterpriseDesign` root state, effective-value transfer and chart bridge. Body-mounted portals inherit root values; portals from nested providers need `EnterpriseDesign.transfer` with that provider's effective values. A Canvas chart must redraw through the existing bridge; changing CSS variables alone does not redraw pixels. Palette/mode switches preserve the same business DOM, focus, input values, filters, selection, dirty state and business storage. Do not reload the route or rebuild the form to change colors.

The scoped `assets/huixin-framework.css` and `assets/huixin-components.css` consume generated values, with reusable SVG symbols in `assets/huixin-icons.svg`. The [runnable Huixin reference](../assets/reference-huixin/index.html) covers `#overview`, `#resources` and `#receipt` using fixture data. Map the host's existing Element Plus/Ant Design or native library through its supported theme API; this reference does not prove either third-party integration.

Before claiming acceptance, measure identical geometry across Huixin brands/modes, exercise real mobile/keyboard paths, and test text/status/control pairs plus both gradient endpoints against their actual surfaces, including composited glass backgrounds. Imported desktop screenshots or the source package's 12 recorded combinations are historical references, not evidence for this integration. Report current-run coverage and gaps.

## Migration and rollback

Existing apps keep Enterprise defaults until explicitly migrated. Preserve old `--ui-*` values and the frozen fixture; do not update it to make tests green. v1.3 tests replace CSS-block-order implementation assumptions with equivalent public token/fallback checks and add effective alias/combination assertions. Old Analytics without `data-ui-brand` retains its palette in generated CSS; opting into a runtime explicit brand is a reviewed migration. The added Huixin Profile and huixin/indigo/violet brands leave existing blue/teal defaults unchanged.

1. Inventory every in-scope surface/state using [site planning](site-planning.md), record current behavior/screenshots, and identify the current provider/portal/chart ownership.
2. Introduce generated resources and one bridge behind the host's existing feature/config entry. Map existing components before page overrides; migrate one reviewable family at a time while preserving the full ledger.
3. Run resolver/generation/tests, candidate scan, then actual task/visual/behavior paths. Register host-specific selectors in project mappings, never in this generic Skill.
4. Roll back by selecting the previous provider/resources and persisted configuration; keep fixture/business storage separate. Reverting tokens does not undo saved business changes.

Tokens can change visual expression; switching a table to a board or changing workflow order requires a page-pattern/business decision. Do not claim a token switch does either.

## Reusable resources and executable checks

Run from the Skill directory:

```sh
python3 scripts/generate_tokens.py
python3 scripts/generate_tokens.py --check
python3 -m unittest discover -s tests -v
python3 scripts/audit_ui.py scan assets/reference-workbench assets/reference-order-flow assets/layout-recipes.css
python3 scripts/audit_ui.py coverage --manifest assets/reference-workbench/surfaces.json --report /absolute/path/to/actual-report.json
```

`scan` returns textual candidates, not AST violations. CSS/SCSS/modules, HTML styles, literal JS/TS style objects and literal Tailwind classes are candidate sources; dynamic classes, Sass evaluation and third-party internals are not classified. Definitions/generated registries are excluded. A previous scan can be passed as `--baseline` to separate existing debt from new candidates (stable path and source required). Triage each candidate; do not globally suppress it. 0, auto, percentages, layout algorithms and one-off business geometry need no token. Real encoding colors, photos and logos require scoped provenance, not replacement.

`coverage` checks a declared ledger and three independently evidenced conclusions. It does not discover every route, prove evidence contents, or execute interactions; route inventory and evidence authenticity must be reviewed. Missing states remain Not tested. Scan success, a CSS generator or unit tests cannot pass the visual/task review.

## Run the local cross-page reference

From the Skill directory, serve `python3 -m http.server 8767 --bind 127.0.0.1`, then open `http://127.0.0.1:8767/assets/reference-workbench/`. The switchers are verification controls, not a required product theme store. Only these fixtures use localStorage for data; no backend or real permission service exists.

With the already available Playwright CLI, open a dedicated isolated session on that URL, then run `run-code --filename /absolute/path/to/enterprise-ui-design/tests/browser-check.js`. The harness clears only that isolated session's fixture origin storage; never target a real application origin. Its returned matrix records all component requests, default page families, pairwise/risk samples and actual state configurations. Separate viewport screenshots, original 200% browser zoom and human/heuristic visual review remain required evidence; the harness does not automatically set visual Pass. Reconcile duplicate observations explicitly before submitting the coverage report.
