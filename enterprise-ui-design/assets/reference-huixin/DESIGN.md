# Huixin workbench UI Blueprint

Approved scope: a local simulated laboratory workbench with three routes. Profile `huixin`, brand `huixin|indigo|violet`, light/dark, standard density. All combinations use the shared EnterpriseDesign runtime; framework and component styles contain no color constants. Supplied Huixin Glass is a scoped, explicitly selected profile exception to the Enterprise default material.

## Shell and layout

A 232px navigation and 70px header frame a fluid workspace. A single page owns 28px desktop inset and 16px narrow inset. Cards own 24px inset, 16px radius; controls are 40px/8px. Page title is 28px, body 14px, table heading 13px. Data rows have 56px minimum; compact resource rows use 44px minimum. Two-column panels align top/bottom. Below 900px all page groups reflow, below 760px navigation becomes a keyboard-safe dialog. Horizontal scroll belongs only to named table regions. No fixed viewport canvas or whole-page scale.

## Page and journey ledger

| Route | Role and completion | Composition and components | State/recovery contract |
| --- | --- | --- | --- |
| #overview | Operator identifies a receipt task and opens it | Four derived metrics, fixture-data SVG chart with accessible table, actionable task table and filter | Search filters actual fixture rows; no matches has reset; receipt link preserves all form data |
| #resources | Technician reads methods/resources for GEO-LEN and OD | Object identity; semantic description grid; compact equipment table; expandable record history; independently owned template empty region | Method tabs switch only their panels; full record remains in disclosure; empty template has no fake action |
| #receipt | Receiver records quantity/condition and confirms a local receipt | Read-only identity; grouped two-column entry; dependent discrepancy group; clear draft and confirm actions; native body-mounted confirmation dialog | Quantity is integer 0–8; receiver/date required; discrepancy reason required when count differs from 8 or condition is damaged; hidden reason retained as draft but excluded from effective receipt when not applicable; draft save/reload; simulated first confirmation failure preserves data and allows retry |

## Data, configuration and providers

`fixture-contract.json` is independent expected behavior and fixture truth, written before implementation. Fixture only: no server, auth, customer acceptance or production receipt implied. Show that scope once in the header. Business draft has its own localStorage key. Configuration storage uses the public adapter; demo startup explicitly selects Huixin profile/standard density, accepts only one of the three supported persisted brands, and validates light/dark. Switching palette/theme mutates token variables and button state only; it never replaces business DOM, chart data, filters, inputs, focus, scroll, selected method or dialog. Native SVG series consume shared roles. Body-mounted native dialogs inherit root tokens and intentionally include the scoped hx-ui root.

## Interaction, errors and notice ownership

Navigation links have current state, mobile menu native modal traps focus and restores trigger. Method tabs have roving arrow/Home/End behavior. Native confirmation dialog supports Escape, focus containment and return. Initial empty fields have no premature errors. Submit builds a focusable error summary with field links and clears corrected errors. The confirmation dialog owns failure and recovery; no duplicate background error. Success updates receipt status and closes dialog; local receipt remains distinct from draft. Storage failure shows a persistent actionable message, never false success. Theme controls announce pressed/current state. No decorative notification counter or permissions fiction.

## Acceptance boundaries

Source syntax/token/link checks and actual browser interactions are separate. Target viewport matrix: 390,683,1366,1440,1600,1920; the 683×384 case approximates the content space of a 1366×768 window at 200%, without claiming actual browser zoom or screen-reader testing. Validate all three brands and both themes, geometry, local-only storage, dependent validation, failure→retry, keyboard navigation/modal and state preservation across switches. Browser evidence must be recorded by the executing verifier; this Blueprint is not evidence of execution.
