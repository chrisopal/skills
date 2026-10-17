# Audit Mode — Review and Refine

Use for design review, UI audit, consistency checks, noncompliant components, or targeted visual repair.

## Authority boundary

- **Audit/review/check:** read-only report.
- **Fix/adjust/refine/upgrade:** capture the baseline first, then implement authorized corrections.
- An audit does not authorize new product features, replatforming, deployment, publishing, or changing business data.

## Evidence set

Identify the surface and user task. Capture the actual UI at the relevant viewport and theme, inspect each accepted screenshot, and connect it to the component/theme source. Cover the states implicated by the request: default, hover/focus/disabled/error/loading, dark, portal, mobile, empty/populated, or unauthorized.

Reject blank, loading, stale, cropped, wrong-window, or blocked captures. If only source is available, say which visual claims remain unverified. Screenshots can reveal visual/accessibility risk but cannot prove semantic structure, keyboard order, assistive-technology behavior, or full compliance.

## Finding contract

Each finding includes:

- `P0` — unusable/broken flow, hidden required action, unreadable content, focus trap, destructive ambiguity, or release blocker.
- `P1` — visible violation of the selected design system, semantic color/state error, inconsistent shared component, portal/theme mismatch, or responsive defect.
- `P2` — non-blocking polish that improves consistency without changing the workflow.
- Evidence: screenshot/state plus exact file/component/token.
- Remediation: one concrete shared-layer or local fix and its verification condition.

Audit these lenses: task clarity, information hierarchy, density, token roles, typography/spacing, components/states, forms, tables, dialogs/portals, responsive scroll ownership, keyboard/focus, language expansion, and specialist-surface boundaries.

For layout, padding, alignment or grouping audits, apply [spatial-system.md](spatial-system.md): inspect inset ownership at each container level, content-width strategy, outer versus text key lines, repeated padding, first/last table cells, label/error alignment and wrapped action groups. Record computed styles and bounding boxes where these establish the finding. Distinguish an intentional inset or optical adjustment from an actual defect; a raw pixel value differing from a default is not automatically a violation. Use screenshot review to judge hierarchy and rhythm. Without a supplied/accepted reference image, report conformance to the contract, not a similarity score.

Measure actual color pairs for normal, hover, disabled, feedback, and dark states. Inspect computed styles when cascade/specificity matters. Verify that visually hidden mobile navigation is not keyboard reachable and that dialogs restore focus.

## Fix loop

When fixes are authorized:

1. Turn each P0/P1 into an observable regression or visual comparison.
2. Prefer token/shared-component repair; use a local override only when the component is an intentional exception.
3. Render the same state and viewport again.
4. Re-evaluate only against the accepted target plus regression evidence.
5. Continue until no P0/P1 remains in scope or a named blocker prevents verification.

Do not “clean up nearby UI” outside the report scope. A fix that changes route behavior, form payload, permissions, or data state is a functional change and requires its own authorization and tests.

## Report shape

1. Target and user task.
2. Overall verdict: Pass / Conditional / Not ready.
3. Strengths worth preserving.
4. P0, P1, P2 findings with evidence and exact remediation.
5. Implemented fixes, when authorized.
6. Recheck screenshots/states and command results.
7. Evidence limits, untested states, and remaining exceptions.

A passing audit requires accepted rendered evidence for every in-scope state, no open P0/P1, and explicit limits. A green build or screenshot count alone cannot produce Pass.
