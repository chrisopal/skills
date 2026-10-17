---
name: enterprise-ui-design
description: Create, upgrade, or audit enterprise admin and workbench frontends, including page layouts, padding, alignment, grouping, density, themes, and responsive components. Preserve the host product and component library. Not for marketing pages, native-mobile-only UI, or backend-only work.
---

# Enterprise UI Design

Build from product truth and apply one visual grammar. Do not invent alternatives unless requested.

## Route the request

| Observable request | Mode | Required reference |
|---|---|---|
| New/empty project, create/build/generate UI | **Create** | [references/create-new.md](references/create-new.md) |
| Existing application, replace/upgrade/migrate/redesign | **Upgrade** | [references/upgrade-existing.md](references/upgrade-existing.md) |
| Audit/review/check/adjust/fix noncompliant UI | **Audit** | [references/audit-and-refine.md](references/audit-and-refine.md) |

If audit and implementation are both requested, capture the baseline, then fix it through Upgrade. Plan/review/audit-only requests remain read-only.

Always read [references/style-standard.md](references/style-standard.md). Before completion, apply [references/checklist.md](references/checklist.md). Use [assets/tokens.json](assets/tokens.json) as token truth and [assets/tokens.css](assets/tokens.css) only as a starter.

For page layout, padding, alignment, grouping, or density work, also read [references/spatial-system.md](references/spatial-system.md). It defines the shared spatial contract for all three modes. Its linked runnable reference uses simulation data; it is a pattern, not a host application's implementation.

## Execution contract

1. Resolve target, outcome, scope, and mutation authority. Ask one question only if target or outcome is missing.
2. Inspect the framework, component library, theme boundary, routes, states, assets, tests, and running UI. Product behavior outranks style.
3. Produce a **UI Blueprint** before code: identify page types, content-width strategy, page/container/text key lines, inset ownership, density, and responsive reflow. Direct build/upgrade requests continue without another checkpoint.
4. Reuse components and theme APIs. Add a scoped adapter before page overrides; add no dependency.
5. Implement the smallest working slice. Controls must be real or labeled fixture-only—never invent search, notifications, SSO, tenants, metrics, or permissions.
6. Verify behavior and visuals separately. Measure rendered insets, gaps, alignment, and overflow, then inspect screenshots in relevant themes/densities and responsive states; run the host's applicable checks. Do not claim pixel similarity without a reference image.
7. Report **designed**, **implemented**, **runtime-verified**, **business-E2E-verified**, **built**, and **deployed** as separate states.

## Invariants

- Preserve brand, IA, auth, RBAC, routes, data contracts, i18n, keyboard behavior, and professional work surfaces unless explicitly changed.
- Keep `brand`, `action-text`, `action-solid/on-action`, and `inverse-surface/on-inverse` distinct. Validate hover, focus, disabled, error, and dark states—not only defaults.
- Do not normalize with broad `button`, `svg`, `div`, `canvas`, or wildcard class selectors. Portals/teleports must receive the same theme intentionally.
- No routine gradients, glass, glow, oversized radii, card lift, decorative motion, or dashboard filler. A confirmed 3D brand asset is a local exception.
- Never claim visual compliance from code inspection, accessibility compliance from screenshots, or E2E readiness from a build alone.

## Common failure corrections

| Failure | Correction |
|---|---|
| Generic SaaS card mosaic | Start from the operator's task, use lists/tables/panels only where structurally meaningful. |
| Full rewrite of a mature app | Theme and shell first; preserve behavior with regression gates; migrate route families incrementally. |
| Pale action with white text in dark mode | Use the tested semantic foreground/background pair, then measure the actual rendered state. |
| Hidden mobile sidebar remains focusable | Remove it from keyboard interaction while closed and verify open/close/focus behavior. |
| “Looks consistent” audit | Return screenshot-linked findings, severity, exact remediation, recheck evidence, and a pass/conditional/fail verdict. |

## Task-first copy and readable density

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

After editing JSON tokens, run `python3 scripts/generate_tokens.py`, then `python3 scripts/generate_tokens.py --check` and `python3 -m unittest discover -s tests -v` from this Skill directory. Existing v1.0 token values remain compatible; new spatial rules use additive semantic tokens. These checks validate token emission and invariants, not visual quality or business behavior.
