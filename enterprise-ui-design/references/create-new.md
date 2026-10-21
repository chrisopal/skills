# Create Mode — New Enterprise Frontend

Use when the user asks to create, build, generate, or scaffold a new enterprise admin, dashboard, portal, or operational workbench.

For visual hierarchy and state composition, also read [product-polish.md](product-polish.md). For mixed-script text or font evidence, read [typography.md](typography.md). Read [analytics-style.md](analytics-style.md) only when a dark data-analysis Profile is requested.

## Entry gate

Identify the product target and primary operator outcome. If either is missing, ask one targeted question. Otherwise proceed with explicit assumptions. This skill already defines the visual direction, so do not pause for three aesthetic variants unless the user requests exploration.

Inspect the workspace before selecting a stack. Reuse an existing framework, package manager, components, tokens, assets, and conventions. For an empty project, follow the user's named stack; if none is named, choose the smallest stack that supports the requested behavior and record the choice. Do not add a backend, database, authentication provider, or deployment target that the request did not authorize.

## UI Blueprint contract

Write the blueprint to the repository's design-doc location when one exists; otherwise present it inline. Include:

1. **Product truth:** real users, real capabilities, unavailable integrations, and fixture-only data.
2. **Primary task:** the operator's main decision/action and the shortest successful path.
3. **Information architecture:** business objects, navigation, page inventory, and each page's responsibility.
4. **State inventory:** loading, empty, populated, partial, error, disabled, unauthorized, and success states that actually apply.
5. **Visual mapping:** semantic tokens, selected Profile, independent theme/density, light/dark behavior, responsive rules, and intentional exceptions. For layout work, use [spatial-system.md](spatial-system.md): state content-width strategies, shell/page/panel inset ownership, outer and inner key lines, standard/compact density, and reflow when the actual workspace narrows.
6. **Interaction contract:** working navigation, filters, forms, validation, dialogs, keyboard behavior, and realistic data boundary.
7. **Acceptance evidence:** exact viewport/state screenshots plus commands proving types, tests, lint, and build.

A direct build request continues after this blueprint. A planning-only request stops after a build-ready blueprint.

For each primary task, use the [business component catalog](business-component-patterns.md) and record the selected combination, exceptions, data/selection/save scope and applicable check IDs. Read only the relevant planning/chart, table, navigation/drawer or form/feedback guide. Use the [component review template](component-review-template.md) to carry these decisions into verification.

For multi-stage tasks and work-item details, extend this blueprint with the journey/state matrix in [task-flow-and-hierarchy.md](task-flow-and-hierarchy.md): operator, object scope, parallel/returned work, next permitted action, blockers, handoff and completion evidence. Choose a wizard, stage overview, task list or history according to the real task; a stepper is not mandatory. Acceptance must include the unaided task walk-through and visual composition gates, not only layout measurements.

## Implementation order

1. Establish theme tokens and the application shell.
2. Implement the primary route end to end, including its real states.
3. Add one form/dialog path and one list/table path when the product needs them.
4. Add secondary pages only when their responsibility is stated in the blueprint.
5. Connect real APIs that exist. If the product is explicitly a prototype, fixtures may power interactions, but the UI and handoff must label them as fixtures.

Do not manufacture top-bar controls or enterprise nouns. Search, notifications, tenant/workspace selectors, SSO, approval, audit, billing, and KPIs appear only when requirements or real contracts support them. Do not fake charts with decorative CSS/SVG when the chart communicates business data; use real data/fixtures and the project's chart system, or leave the visualization out.

## Example

Request: “Create an equipment-maintenance workbench with work orders and overdue alerts.”

Correct first slice: shell → work-order list with real filters/states → work-order detail/action → validated completion dialog. Do not add tenant management, revenue KPIs, global search, notifications, or SSO unless separately required.

## Completion gate

- The primary path works in the rendered application, not just a static mock.
- Every visible core control has behavior or is explicitly marked outside the requested scope.
- Light/dark and desktop/mobile screenshots use the same states as the acceptance plan.
- No console errors or page-level overflow were introduced.
- Populated long-content states confirm measured page/text alignment, intentional nested insets and usable wrapped actions; screenshots also confirm hierarchy and spatial rhythm. A token check alone cannot establish this.
- Static checks and the production build are read back; fixture, API, deployment, and business-E2E boundaries are stated.

## Site scope and resolved configuration

Apply [site planning](site-planning.md) within this mode: Discover → Blueprint → Resolve Design System → Implement → Technical Audit → Visual/Task Review → Polish → Recheck. Use one existing DESIGN.md, a real route/surface/state ledger, and the [configuration/migration contract](design-system-contract.md). Cover approved child routes, Tabs, overlays, permissions and important states. A first slice is not whole-site completion. Brand, Profile, light/dark and density are independent; preserve legacy defaults until explicitly migrated. Run the executable registry/coverage checks and report technical, visual/task and behavior conclusions separately. Audit-only remains read-only.
