# Upgrade Mode — Existing Frontend

Use when the target already has routes, components, theme code, business behavior, users, or an upstream update stream.

Read [product-polish.md](product-polish.md) for composition and state density, and [typography.md](typography.md) when changing type roles or checking font claims. Use [analytics-style.md](analytics-style.md) only for the optional Analytics Profile.

## Baseline before edits

Inspect the actual runtime and source. Capture representative light/dark states for authentication, shell, dashboard/list, form/dialog, empty/error/unauthorized, mobile navigation, and a professional work surface. Record the branch/base revision and pre-existing failures. If runtime capture is blocked, label the result source-only; do not call it a visual audit.

Return a keep / adapt / retire map:

- **Keep:** behavior, business IA, brand assets, mature components, professional work surfaces, and intentional exceptions.
- **Adapt:** theme tokens, component-library provider, shell, page hierarchy, shared patterns, portal host, focus and responsive behavior.
- **Retire:** conflicting palette roles, routine gradients/glass/glow, oversized radii/shadows, card filler, decorative motion, and inaccessible hidden UI.

For spatial updates, read [spatial-system.md](spatial-system.md). Trace actual shell → page → section → component padding before edits, including component-library defaults. Record which layer owns each inset, which key lines align outer boxes versus text, and how content width changes with navigation/panels. Keep existing spacing tokens working; adopt the new semantic contract one page family at a time rather than globally resetting margins or padding.

## Migration architecture

Prefer one scoped adapter/profile using the target project's own token namespace and theme API. Keep an original-theme rollback during migration. Keep Profile, theme and density independent; use the generated cascade and make unsupported combinations fall back explicitly. For component-scoped CSS, use an explicit root profile plus stable semantic classes; use `!important` only when verified third-party specificity requires it. Portals/teleports must receive the same profile/theme/density attributes.

Portals/teleports mounted under `body` must inherit or receive the same theme. Do not fix that with global wildcard selectors. Keep canvas, editor, chart, markdown, generated content, and media internals outside broad normalization.

Protect functional seams before changing structure: auth submission, RBAC/guards, route/deep-link behavior, cached views, form payloads, API state, i18n, workspace/tenant context, keyboard focus, and mobile navigation. Add or run behavioral regression checks at the seam touched by the UI change.

For component changes, consult the [business scenario catalog](business-component-patterns.md) and relevant specialist guide. Preserve useful table, tab, drawer, calendar and professional-canvas behavior; replace a pattern only when the task or evidence justifies it. Record data/selection/save scope and observable checks in the [component review template](component-review-template.md).

## Delivery slices

1. Semantic tokens and component-library bridge, no page restructuring.
2. Shell and page-frame normalization.
3. One authentication surface and one representative operating page.
4. Shared list/table/form/dialog/status patterns.
5. One route family per reviewable change; document specialist exceptions.

Keep visual-only changes separate from new business features. For a project that tracks upstream, minimize edits to upstream-owned templates, identify stable integration seams, and record the update/reapplication gate. When upstream adds a page, shared tokens should make it acceptable before any page-specific patch.

For an unintuitive workflow, prioritize the affected task journey rather than mechanically completing every shell slice first. Apply [task-flow-and-hierarchy.md](task-flow-and-hierarchy.md): map existing business facts, separate current work from supporting detail, and reconnect actions to their object scope while preserving route, state and permission contracts. If the UI needs unavailable responsibility or progress data, record that contract gap instead of fabricating it in the frontend.

## Verification loop

Render the same states and viewports before/after. After each slice, compare screenshots, verify focus/scroll/portal behavior, and run the relevant behavior tests. A screenshot delta is accepted only when it follows the blueprint and does not hide information or controls.

For spacing/density changes, record computed insets/gaps and key-line geometry, then inspect the whole composition. Verify long labels, populated tables, multi-line filters, empty results and low-height dialogs in the selected Profile/theme/density. Compact must not shrink body type, erase group hierarchy or become the automatic mobile setting. Preserve focused controls/drafts through reflow.

Completion means the accepted route scope is upgraded and verified. It does not mean every page is migrated unless every route/state was explicitly covered. Report remaining route families and rollback instructions.

## Site scope and resolved configuration

Apply [site planning](site-planning.md) within this mode: Discover → Blueprint → Resolve Design System → Implement → Technical Audit → Visual/Task Review → Polish → Recheck. Use one existing DESIGN.md, a real route/surface/state ledger, and the [configuration/migration contract](design-system-contract.md). Cover approved child routes, Tabs, overlays, permissions and important states. A first slice is not whole-site completion. Brand, Profile, light/dark and density are independent; preserve legacy defaults until explicitly migrated. Run the executable registry/coverage checks and report technical, visual/task and behavior conclusions separately. Audit-only remains read-only.
