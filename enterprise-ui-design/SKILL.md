---
name: enterprise-ui-design
description: Create, upgrade, or audit enterprise admin and workbench frontends. Select and verify business UI patterns including Gantt, calendars, tables/grids, Tabs, drawers/dialogs, forms, feedback, charts, order stages, and end-to-end task flows and workflow usability. Improve visual hierarchy, layouts, density, themes, and responsive behavior while preserving the host product and component library. Not for marketing pages, native-mobile-only UI, or backend-only work.
---

# Enterprise UI Design

v1.3 — compatible extension of v1.2; preserve the frozen public v1 token contract.

Build from product truth and apply one visual grammar. Do not invent alternatives unless requested.

## Route the request

| Observable request | Mode | Required reference |
|---|---|---|
| New/empty project, create/build/generate UI | **Create** | [references/create-new.md](references/create-new.md) |
| Existing application, replace/upgrade/migrate/redesign | **Upgrade** | [references/upgrade-existing.md](references/upgrade-existing.md) |
| Audit/review/check/adjust/fix noncompliant UI | **Audit** | [references/audit-and-refine.md](references/audit-and-refine.md) |

If audit and implementation are both requested, capture the baseline, then fix it through Upgrade. Plan/review/audit-only requests remain read-only.

Always read [references/style-standard.md](references/style-standard.md). Before completion, apply [references/checklist.md](references/checklist.md). Use [assets/tokens.json](assets/tokens.json) as token truth and [assets/tokens.css](assets/tokens.css) only as a starter.

For cross-page scope, style/brand switching or design-system migration, read [site planning](references/site-planning.md) and [the effective configuration contract](references/design-system-contract.md). Reuse the existing project DESIGN.md and components. The [rule registry](references/audit-rules.json), [review JSON template](references/review-report.template.json) and runnable candidate/coverage checker keep technical audit, visual/task review and behavior regression separate.

For hierarchy, mixed-script rendering or font claims, read [references/typography.md](references/typography.md). For page composition, content density and state distinction, read [references/product-polish.md](references/product-polish.md). Use [references/analytics-style.md](references/analytics-style.md) only when the optional dark Analytics Profile is in scope.

For page layout, padding, alignment, grouping, or density work, also read [references/spatial-system.md](references/spatial-system.md). It defines the shared spatial contract for all three modes. Its linked runnable reference uses simulation data; it is a pattern, not a host application's implementation.

For multi-stage business flows, work-item details, next-action clarity, toolbar hierarchy, or a request that a page is unintuitive or unattractive, also read [references/task-flow-and-hierarchy.md](references/task-flow-and-hierarchy.md). Use its per-journey ledger, step evidence and recovery/handoff guidance with the [review template](references/task-flow-review-template.md); passing spacing/overflow tests does not establish task clarity or visual quality.

When selecting or reviewing components, start at [references/business-component-patterns.md](references/business-component-patterns.md), then read only the relevant scenario guide: planning/charts, table variants, Tabs/drawers/navigation, forms/feedback, or order/approval progress. Each guide defines suitable and unsuitable uses, component combinations, state/interaction contracts and observable acceptance checks. Record the choice, host-component mapping and evidence with the [component review template](references/component-review-template.md). The linked runnable order-flow reference is one simulated example; other guides do not claim runnable implementations.

For business-detail reading or empty-state layout, read [forms and feedback](references/forms-and-feedback.md#只读详情与空状态构图) with the spatial contract. Use semantic subject/task groups, visible label/value relationships and responsive read-only fields; measure the owned empty region and block insets instead of accepting a text pile or a border-hugging message. Preserve tables, history timelines and specialist editors where their tasks require them.

For sidebar/menu icon work, read the [navigation icon rules](references/navigation-and-task-surfaces.md#导航图标专项). Inventory labels, routes, business meanings and actual glyphs across the full menu, including permission-dependent items; justify semantic reuse rather than enforcing arbitrary uniqueness.

## Execution contract

1. Resolve target, outcome, scope, and mutation authority. Ask one question only if target or outcome is missing.
2. Inspect the framework, component library, theme boundary, routes, states, assets, tests, and running UI. Product behavior outranks style.
3. Produce a **UI Blueprint** before code: identify page types, content-width strategy, page/container/text key lines, inset ownership, density, and responsive reflow. Record scenario-to-component choices, exceptions, data/selection/save scope and interaction/state checks. For each in-scope journey, record role, goal, entry, completion, real contract/source, main path and applicable recovery/handoff branches; map each step's cue, action, expected result and evidence path to the actual contract. Direct build/upgrade requests continue without another checkpoint.
4. Resolve Brand, Profile, theme and density independently through [the configuration contract](references/design-system-contract.md). Blue is the default brand, not an invariant. Select the visual Profile separately from theme and density. Enterprise is the default; Analytics is an optional dark data surface with explicit fallback. Reuse components and theme APIs, add a scoped adapter before page overrides, and add no dependency. Apply the generated token cascade and copy profile/theme/density to portals.
5. Implement the smallest working slice, then complete every approved surface/state in the [site ledger](references/site-planning.md); a first slice is not a whole-site deliverable. Controls must be real or labeled fixture-only—never invent search, notifications, SSO, tenants, metrics, or permissions.
6. Verify business-state truth, UX/task comprehension and visual composition separately. Measure rendered insets, gaps, alignment, and overflow; inspect role typography and actual rendered fonts; then inspect screenshots and walk the task in relevant Profile/theme/density combinations and responsive states. Record interruption, timeout, partial failure, draft preservation, handoff and resume evidence where the contract supports them. A heuristic or model review never implies a real-user study; record user observations only when actually observed, with unknown metrics left Not tested. Run the host's applicable checks. Do not claim pixel similarity without a reference image or user comprehension from a model review alone.
7. Report **designed**, **implemented**, **runtime-verified**, **business-E2E-verified**, **built**, and **deployed** as separate states.

## Invariants

- Preserve brand, IA, auth, RBAC, routes, data contracts, i18n, keyboard behavior, and professional work surfaces unless explicitly changed.
- Keep `brand`, `action-text`, `action-solid/on-action`, and `inverse-surface/on-inverse` distinct. Validate hover, focus, disabled, error, and dark states—not only defaults.
- Do not normalize with broad `button`, `svg`, `div`, `canvas`, or wildcard class selectors. Portals/teleports must receive the same theme intentionally.
- No routine gradients, glass, glow, oversized radii, card lift, decorative motion, or dashboard filler. A confirmed 3D brand asset is a local exception.
- Never claim visual compliance from code inspection, accessibility compliance from screenshots, or E2E readiness from a build alone.
- Treat an unknown-result submit as unresolved: verify the outcome before retrying, and do not invent an API or persistence contract to make the result look successful.
- A narrow audit covers only its declared journeys. A whole-site review uses the approved complete flow inventory and ledger; it does not turn an unapproved global inventory into a gate.
- `assets/tokens.json` is the token truth. The unique effective order is foundation → theme → supported Profile → explicit brand → density, followed by effective alias/recipe resolution; unsupported Profile/theme combinations use the declared fallback. Keep data-series colors separate from business-state colors.

## Common failure corrections

| Failure | Correction |
|---|---|
| Generic SaaS card mosaic | Start from the operator's task, use lists/tables/panels only where structurally meaningful. |
| Full rewrite of a mature app | Theme and shell first; preserve behavior with regression gates; migrate route families incrementally. |
| Pale action with white text in dark mode | Use the tested semantic foreground/background pair, then measure the actual rendered state. |
| Hidden mobile sidebar remains focusable | Remove it from keyboard interaction while closed and verify open/close/focus behavior. |
| “Looks consistent” audit | Return screenshot-linked findings, severity, exact remediation, recheck evidence, and a pass/conditional/fail verdict. |
| Tidy controls, confusing workflow | Map stage, scope, next action and blockers; inspect the populated journey, including parallel and returned work. A status badge alone is not a workflow. |
| Every utility looks equally important | Separate task commands, query controls and view utilities; keep commands recognizable while reducing auxiliary visual weight. Do not invent a primary action for a read-only page. |

## Task-first copy and readable density

Apply [references/notice-economy.md](references/notice-economy.md) during design, implementation and final review: admit only necessary notices, assign one owner for each fact in context, and retire stale messages as state changes. Record these decisions in the Blueprint and verify the observable NOTICE checks.

For business-friendly wording, terminology cleanup, or application-wide copy review, read [references/business-copy.md](references/business-copy.md). Cover child pages, Tabs, dialogs, workflows and dynamic feedback through an explicit inventory; preserve business-state meaning and report untested branches. Keyword replacement is not acceptance.

For enterprise workbenches, do not add explanatory copy by default. Show business data, current state and actions. Remove slogans, page-purpose subtitles, repeated metric definitions, click instructions and implementation terminology (server-side, snapshots, internal codes) from the normal reading path. Do not fill empty space with prose.

- Every persistent sentence must change the user's current decision or action. If removing it changes neither, delete it.
- Use precise labels first. Put a necessary metric definition, audit identifier or background explanation behind a keyboard-accessible help/disclosure control. Do not replace every deleted sentence with an info icon.
- Preserve contextual validation, failure recovery, missing prerequisites, real uncertainty and consequential-action warnings. Show them at the relevant field or decision, only when applicable; do not blanket-hide warnings.
- Dashboard metrics default to label + value + unit. Use a meaningful trend only when real data exists. Empty states use one short state sentence and an optional real action.
- Separate document/version headers, action/download toolbars, metadata, coverage tables and readable body content. Use the spatial contract for section/group gaps; readable document prose may use 1.6–1.8 line height. Keep status with its title; wrap action groups on narrow screens. Move long IDs into details, retain access.
- Acceptance: walk every in-scope tab/dialog, reject repeated explanations, verify help can be reached by keyboard, and inspect populated long-content layouts at desktop and narrow widths. Confirm no action, error, evidence or data was lost.

## Recognizable actions

Actions must be recognizable before hover. Use the existing component library's primary/secondary hierarchy for commands; repetitive row actions may use its recognizable action-button style with action color and visible focus. Do not promote every row command to a filled primary button or render it as muted body text. Reserve navigation links for navigation and keep their link cue. Hover and pointer cursor alone are insufficient.

Keep actions for one record in a compact group with 8px gaps; align the group as a unit, never distribute individual buttons across the row with space-between. Wrap on narrow screens. Maintain visible keyboard focus and distinct disabled states in light and dark themes. Clickable metrics or rows need a persistent directional or link cue. Do not add explanatory text to compensate for unclear affordance.

Walk the dashboard, every tab, populated record actions and dialogs; check default, hover, focus, disabled and narrow-layout states. Report browser verification separately from source inspection and tests.

For existing project-specific action conventions, see [references/project-exceptions.md](references/project-exceptions.md) only when that project is in scope; do not copy them into new products.

## Maintain the reusable source

After editing JSON tokens, run `python3 scripts/generate_tokens.py`, then `python3 scripts/generate_tokens.py --check` and `python3 -m unittest discover -s tests -v` from this Skill directory. Existing v1.0 token values remain compatible; role typography, Profile semantics and new spatial rules are additive. These checks validate token emission and invariants, not visual quality or business behavior. The runnable references are simulated fixtures, not host application acceptance.
