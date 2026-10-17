# Upgrade Mode — Existing Frontend

Use when the target already has routes, components, theme code, business behavior, users, or an upstream update stream.

## Baseline before edits

Inspect the actual runtime and source. Capture representative light/dark states for authentication, shell, dashboard/list, form/dialog, empty/error/unauthorized, mobile navigation, and a professional work surface. Record the branch/base revision and pre-existing failures. If runtime capture is blocked, label the result source-only; do not call it a visual audit.

Return a keep / adapt / retire map:

- **Keep:** behavior, business IA, brand assets, mature components, professional work surfaces, and intentional exceptions.
- **Adapt:** theme tokens, component-library provider, shell, page hierarchy, shared patterns, portal host, focus and responsive behavior.
- **Retire:** conflicting palette roles, routine gradients/glass/glow, oversized radii/shadows, card filler, decorative motion, and inaccessible hidden UI.

For spatial updates, read [spatial-system.md](spatial-system.md). Trace actual shell → page → section → component padding before edits, including component-library defaults. Record which layer owns each inset, which key lines align outer boxes versus text, and how content width changes with navigation/panels. Keep existing spacing tokens working; adopt the new semantic contract one page family at a time rather than globally resetting margins or padding.

## Migration architecture

Prefer one scoped adapter/profile using the target project's own token namespace and theme API. Keep an original-theme rollback during migration. For component-scoped CSS, use an explicit root profile plus stable semantic classes; use `!important` only when verified third-party specificity requires it.

Portals/teleports mounted under `body` must inherit or receive the same theme. Do not fix that with global wildcard selectors. Keep canvas, editor, chart, markdown, generated content, and media internals outside broad normalization.

Protect functional seams before changing structure: auth submission, RBAC/guards, route/deep-link behavior, cached views, form payloads, API state, i18n, workspace/tenant context, keyboard focus, and mobile navigation. Add or run behavioral regression checks at the seam touched by the UI change.

## Delivery slices

1. Semantic tokens and component-library bridge, no page restructuring.
2. Shell and page-frame normalization.
3. One authentication surface and one representative operating page.
4. Shared list/table/form/dialog/status patterns.
5. One route family per reviewable change; document specialist exceptions.

Keep visual-only changes separate from new business features. For a project that tracks upstream, minimize edits to upstream-owned templates, identify stable integration seams, and record the update/reapplication gate. When upstream adds a page, shared tokens should make it acceptable before any page-specific patch.

## Verification loop

Render the same states and viewports before/after. After each slice, compare screenshots, verify focus/scroll/portal behavior, and run the relevant behavior tests. A screenshot delta is accepted only when it follows the blueprint and does not hide information or controls.

For spacing/density changes, record computed insets/gaps and key-line geometry, then inspect the whole composition. Verify long labels, populated tables, multi-line filters, empty results and low-height dialogs in the selected density. Compact must not shrink body type, erase group hierarchy or become the automatic mobile setting. Preserve focused controls/drafts through reflow.

Completion means the accepted route scope is upgraded and verified. It does not mean every page is migrated unless every route/state was explicitly covered. Report remaining route families and rollback instructions.
