# Analytics Profile

`analytics` is an optional dark data-analysis Profile for dense charts, comparisons and monitoring surfaces. It is not a replacement for the Enterprise baseline and it does not change business execution mode, permissions, routes or data contracts.

## Supported combinations

- `data-ui="enterprise"` with no profile or `data-ui-profile="enterprise"`: Enterprise light/dark baseline.
- `data-ui-profile="analytics"` + `data-theme="dark"`: Analytics palette and series tokens.
- `data-ui-profile="analytics"` + `data-theme="light"`: unsupported combination; explicitly falls back to Enterprise light values.
- `data-density="standard|compact"` is independent of both Profile and theme. Compact changes layout tokens only.

Resolve using [the shared configuration contract](design-system-contract.md): foundation → theme → supported Profile → explicit brand → density. Missing-brand Analytics CSS keeps its legacy action palette; explicit brand owns action/hover/selected/focus and wins over that palette. A Profile may override visual expression and data-series tokens only when declared in `tokens.json`; it must not silently replace state colors with a chart series. Keep `brand`, readable `action-text`, solid action plus `on-action`, `state-*`, and `data-series-*` separate. Series colors describe measured categories; success, warning and danger describe business state.

The generated CSS is the source of the cascade. Set attributes on `html`; generated selectors are root-scoped. An explicit `data-theme` takes precedence over a legacy `.dark` class. Body portals inherit this root context. For a nested provider with a different theme or profile, transfer its resolved custom properties to the Teleport/dialog root via the host theme provider; copying attributes onto a non-html element alone does not activate these selectors. Do not use wildcard selectors to repair a missing inheritance path.

Use the Profile only when the data is real or clearly labelled fixture data and the visual task benefits from comparison. Keep chart legends, units, zero values, uncertainty and failure states visible. Do not add radar, trend or KPI decoration without a data contract. The runnable references label all content as simulated and expose Profile, theme and density selectors for interaction checks.
