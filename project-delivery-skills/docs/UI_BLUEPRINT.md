# Delivery review workbench UI blueprint

## Purpose

`render_review.py` produces a standalone local HTML review surface for one delivery project. It is a read-only view of the runtime snapshot, so reviewers can inspect the current project state, trace artifact content, and compare revision/evidence metadata without mistaking the page for an approval or export workflow.

## Information architecture

- **Header**: project ID, purpose, generated view, and a prominent `SIMULATION` label when `purpose=simulation`.
- **Left navigation**: stage groups derived from artifact kinds, followed by artifact IDs and registered template IDs. Links jump to real local sections in the same document.
- **Main content**: a compact project status row, then artifact sections in snapshot order. Each artifact separates title/identity, status and revision metadata, evidence/revision references, and the full business data.
- **Internal-only section**: internal cost summary, alerts, and gate reasons are rendered only for `--view internal`.
- **Customer view**: only an explicit public business-kind allowlist with `visibility=customer` is rendered. The page receives no raw internal snapshot, path, cost, alert, or private artifact data.
- **Search**: one real local text filter over artifact/template records. Navigation and search are keyboard reachable and work without a server.

## Visual grammar

The page uses the Enterprise UI Design blue token set: flat white/light-gray surfaces, blue action text and indicators, 4px controls, 6px panels, 14px body text, and visible borders. Layout relies on aligned sections and tables rather than a card mosaic. Long content wraps in the main column; tables scroll inside their own container on narrow screens. A `prefers-color-scheme: dark` block maps the same semantic tokens to the prescribed dark palette.

## States and behavior

- Empty artifact/template collections show a short factual state message.
- `draft`, `ready`, and `blocked` remain visible as text labels; status is never expressed by color alone.
- Chinese business labels are primary. Version/health/path/hash metadata and nested evidence open in disclosure sections; a newer candidate is never marked effective by artifact ID alone.
- Search hides unmatched records and empty groups and reports the result count using an `aria-live` region. Clicking navigation clears the filter before jumping.
- No approval, customer confirmation, export, upload, or other mutating control is presented. The only interactive elements are the search field and document anchors.

## Acceptance checks

- Customer HTML contains no internal artifact records, cost summary values, alerts, or hidden raw snapshot JSON.
- Internal HTML includes costs/alerts/gates and the complete snapshot-backed artifact data.
- Chinese paragraphs, nested records, lists, and tabular business data remain readable and searchable.
- HTML opens from a local file with no external CSS, JavaScript, font, server, or application dependency.
- Keyboard focus is visible; the layout remains usable at desktop and narrow widths without page-level horizontal overflow.
