# Effective configuration and migration contract (v1.3)

Use one existing `DESIGN.md` or equivalent project document for durable decisions: operator/task, approved scope and page ledger, token version, brand/profile/theme/density, font policy, library/provider mapping and scoped exceptions. Do not create competing design truths. Values live only in `assets/tokens.json`; generated resources and review evidence are derived.

## Independent dimensions and ownership

| Dimension | Owner | Contract |
|---|---|---|
| Brand | brand/action-text/solid/on-action/hover/selected/focus | Blue is the default, not a product invariant. Teal is a validated proof preset. Never replace danger/success or categorical series with brand. |
| Theme | light/dark semantic palette | Explicit light wins over legacy `.dark`. No `system` mode existed in v1.2; do not invent its persistence/SSR support. |
| Profile | typography emphasis, surfaces, borders, radius and rhythm | Enterprise preserves the existing appearance. Precision supports both themes. Analytics retains dark entry and Enterprise-light fallback. Profile does not change IA, data, permissions or page logic. |
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

## Migration and rollback

Existing apps keep Enterprise defaults until explicitly migrated. Preserve old `--ui-*` values and the frozen fixture; do not update it to make tests green. v1.3 tests replace CSS-block-order implementation assumptions with equivalent public token/fallback checks and add effective alias/combination assertions. Old Analytics without `data-ui-brand` retains its palette in generated CSS; opting into runtime explicit blue/teal is a reviewed migration.

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
