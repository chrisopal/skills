# Product Polish: Composition, Density and States

Polish comes from a readable composition and trustworthy state model. Start with the operator's decision, then place the shortest path to its existing action:

1. Page header: object, scope and current state; actions grouped by task.
2. Filters: one aligned query row that explains its result scope.
3. Overview: only real metrics or queues, sized by content rather than empty grid space.
4. Work surface: table, form, timeline or specialist canvas that carries the task.
5. Supporting detail: evidence, history and metadata with a clear reading order.

Use alignment, type roles, whitespace and one or two meaningful surfaces to establish hierarchy. A panel boundary is useful when it owns a task or scroll region; do not wrap every label, metric and row in a card. A single metric should be content-driven and should keep its detail link. A populated table should read as one surface, with filters and actions aligned to the table's key line.

Keep these states distinct: zero is a valid business result, empty means no records, filtered-empty means the query matched nothing, loading means the request is unresolved, failure means recovery is needed, and unauthorized means the current principal cannot access the object. Keep status text or an icon with the semantic color. Do not invent trends, queues or explanatory filler to fill a sparse page.

Responsive polish is reflow, not uniform shrinking. Let action groups wrap, give mobile navigation a focus-safe open/close path, and keep horizontal table scroll inside its table region. Preserve 44px touch targets where the host requires them. In compact density, reduce repeated insets and row padding while retaining body type, hierarchy and keyboard focus.

Positive pattern: a page title, one status, one grouped command area, a compact real summary and one continuous work surface. Anti-pattern: equal-weight cards, nested borders around each field, a fixed-height empty dashboard, decorative shadows, or a disabled-looking action that is actually available.

For acceptance, inspect default/hover/focus/disabled/loading/error states in light and dark themes, the same data at narrow and wide viewports, and any dialog or portal after profile/theme changes. Measure the owned inset and scroll relationship before changing a token.
