# Audit Mode — Review and Refine

Use for design review, UI audit, consistency checks, noncompliant components, or targeted visual repair.

Read [product-polish.md](product-polish.md) for hierarchy and state composition. Read [typography.md](typography.md) for rendered-font evidence. If the surface uses the optional dark Analytics Profile, read [analytics-style.md](analytics-style.md) and test its declared fallback.

## Authority boundary

- **Audit/review/check:** read-only report.
- **Fix/adjust/refine/upgrade:** capture the baseline first, then implement authorized corrections.
- An audit does not authorize new product features, replatforming, deployment, publishing, or changing business data.

## Evidence set

Identify the surface and user task. Capture the actual UI at the relevant viewport and theme, inspect each accepted screenshot, and connect it to the component/theme source. Cover the states implicated by the request: default, hover/focus/disabled/error/loading, dark, portal, mobile, empty/populated, or unauthorized.

Reject blank, stale, wrong-window, or unintentionally blocked captures. A loading capture proves only that loading state. User-supplied crops can establish local findings; label missing context, viewport, DPR and capture time as unknown, and never use them to pass a whole page or journey. If only source is available, say which visual claims remain unverified. Screenshots can reveal visual/accessibility risk but cannot prove semantic structure, keyboard order, assistive-technology behavior, or full compliance.

## Finding contract

Each finding includes:

- `P0` — unusable/broken flow, hidden required action, unreadable content, focus trap, destructive ambiguity, or release blocker.
- `P1` — visible violation of the selected design system, semantic color/state error, inconsistent shared component, portal/theme mismatch, or responsive defect.
- `P2` — non-blocking polish that improves consistency without changing the workflow.
- Evidence: screenshot/state plus exact file/component/token.
- Remediation: one concrete shared-layer or local fix and its verification condition.

For notice clutter, redundancy or explanatory copy, apply [notice-economy.md](notice-economy.md). Record necessity, semantic duplicate group, owning surface and show/clear conditions; check asynchronous terminal states and read-only/preview branches. Misleading current-state or impossible-action guidance is P1; ordinary non-blocking repetition is P2. Source findings remain source-only until actually reproduced.

Audit these lenses: task clarity, information hierarchy, density, token roles, typography/spacing, components/states, forms, tables, dialogs/portals, responsive scroll ownership, keyboard/focus, language expansion, and specialist-surface boundaries.

For component suitability and interaction audits, use the [business scenario catalog](business-component-patterns.md), its relevant specialist guide and [component review template](component-review-template.md). Test the actual choice and scope: Gantt versus calendar, tree versus grouped table, Tabs versus a stepper, inline versus modal drawer, and persistent errors versus transient feedback. Record applicable check IDs and evidence; a component library name does not prove the composition is appropriate.

For workflow, work-item, toolbar or aesthetic complaints, apply [task-flow-and-hierarchy.md](task-flow-and-hierarchy.md) and its [review template](task-flow-review-template.md). Trace the actual journey, not just isolated pages. Record business-state truth, unaided task walk-through and visual composition separately. A materially misleading stage, unclear object scope or detached current-task action is P1 unless evidence establishes a P0 blocker. Do not invent a missing primary action on read-only/waiting pages or infer CSS sizes from screenshot pixels.

For layout, padding, alignment or grouping audits, apply [spatial-system.md](spatial-system.md): inspect inset ownership at each container level, content-width strategy, outer versus text key lines, repeated padding, first/last table cells, label/error alignment and wrapped action groups. Record computed styles and bounding boxes where these establish the finding. Distinguish an intentional inset or optical adjustment from an actual defect; a raw pixel value differing from a default is not automatically a violation. Use screenshot review to judge hierarchy and rhythm. Without a supplied/accepted reference image, report conformance to the contract, not a similarity score.

Measure actual color pairs for normal, hover, focus, disabled, feedback, and dark states. Inspect computed styles when cascade/specificity matters, including foundation → theme → supported Profile → explicit brand → density and portal inheritance. Verify that visually hidden mobile navigation is not keyboard reachable and that dialogs restore focus.

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

## Site scope and resolved configuration

Apply [site planning](site-planning.md) within this mode: Discover → Blueprint → Resolve Design System → Implement → Technical Audit → Visual/Task Review → Polish → Recheck. Use one existing DESIGN.md, a real route/surface/state ledger, and the [configuration/migration contract](design-system-contract.md). Cover approved child routes, Tabs, overlays, permissions and important states. A first slice is not whole-site completion. Brand, Profile, light/dark and density are independent; preserve legacy defaults until explicitly migrated. Run the executable registry/coverage checks and report technical, visual/task and behavior conclusions separately. Audit-only remains read-only.
