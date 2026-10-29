# Huixin three-layer integration

Approved scope: integrate the supplied Huixin Glass package into Enterprise UI Design, repair contrast and competing aliases, provide three interactive simulated pages, validate, back up/synchronize the installed skill, merge main and push.

## Ownership and compatibility

`enterprise-ui-design/assets/tokens.json` remains the authored source. Framework geometry and material recipes belong to `profiles.huixin.common`; component recipes consume canonical tokens. Huixin theme mode entries and explicit brand palettes contain colors only. Retain public v1 fixtures/defaults, the existing four-axis resolver, and the EnterpriseDesign runtime entry. Add profile-local density overrides rather than globally changing compact controls. No new dependencies, host application changes, or production claims.

Resolve source conflicts to `table-row-height=56px` (compact44), `chart-donut-size=200px`; remove redundant source aliases. Fix small text, states, control boundaries, series and both primary gradient endpoints. Shadow/gradient geometry is stable across palette/mode changes.

## Implementation and regression order

1. Baseline: existing 55 Enterprise tests pass; origin/main fetched, worktree clean at f84245a0.
2. Main lane owns canonical tokens, resolver/generator extensions, deterministic regression and browser acceptance evidence.
3. Independent UI lane owns scoped Huixin CSS/icon assets and runnable overview/resources/receipt fixtures, with Blueprint and declared local-only contract before code.
4. Documentation lane owns skill routing and focused three-layer guidance. Existing framework/library remains authoritative in real hosts.
5. Validate generated outputs/public fixtures, contrast, theme geometry isolation, browser interactions/recovery/portals, desktop/narrow layouts and visual comparison against supplied reference. Save screenshots/results outside tracked source; independently freeze acceptance scope before execution.
6. Back up installed skill, copy verified maintained files, compare hashes and run installed checks. Commit with Lore context, push feature branch, integrate fetched main without touching unrelated worktrees, push main normally, read back remote SHA.

## Demonstration boundary

Three pages: operational overview, testing/resources detail, sample receipt. Shared Huixin framework, three validated brand palettes (Huixin teal, indigo, violet), light/dark. Fixtures use local browser persistence only. No remote/API permission or real laboratory acceptance is implied. Theme changes preserve geometry, DOM identity, draft, filters, modal, focus and scroll; meaningful component states remain available at390px and desktop widths.
