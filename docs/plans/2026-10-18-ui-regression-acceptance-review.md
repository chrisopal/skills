# UI regression acceptance skill review and improvement plan

The requested scope is the installed `ui-regression-acceptance` skill: can another agent inventory and exercise each declared page/control against business, interaction, display and layout contracts? No business application migration is requested.

## Plan before edits

1. Preserve the installed baseline locally under `projects/ui-regression-acceptance-20261018/`; import its six reusable files into this repository. Preserve unrelated WIP.
2. Reproduce false-positive ledgers before modifying the checker. Add standard-library regression tests for independent scope omissions, shared dimension IDs, page-layout omissions, unknown contracts, integrity and status/count handling.
3. Make scope reconciliation executable. Use a separately frozen scope manifest with source/runtime discovery references, page/control/check identities and dimensions. Bind the ledger to its digest and build. Require the manifest for a current PASS; do not silently upgrade old ledgers.
4. Clarify source-to-runtime inventory, conditional/role/state branches, constraint boundary selection, business-flow outcomes and versioned visual standards. Use one maintained schema/reference rather than repeating field definitions.
5. Validate the checker, frontmatter, local links and syntax. Independently review and exercise realistic scenarios; explicitly separate checker verification from actual browser/business acceptance.
6. Check installed-file drift, synchronize verified reusable source back into the installed skill, read back hashes, update STATUS, commit scoped source/docs/tests with Lore trailers and push the configured branch. Keep generated evidence local.

## Baseline findings

- The checker accepts an entire-application claim based solely on a self-declared one-page inventory; it has no independent expected-scope input.
- One check can be assigned to all four dimensions and count as complete acceptance.
- The documented page-wide layout instance is not enforced by the checker.
- A missing business contract must be BLOCKED, but the checker still requires a nonempty contract reference for BLOCKED, encouraging fake references.

## Acceptance and limits

Scope omissions, missing dimensions/layout checks and missing execution evidence must prevent PASS. Known failed checks remain FAIL; unknown/missing inputs remain INCOMPLETE. Missing contracts can be reported honestly. Hash/path verification, original failure evidence and real-browser/persistence requirements remain intact. No dependencies are added. No metadata validator can prove that a scope is exhaustive, a reference is authoritative or a browser action happened; those require independent inventory review and inspection of actual execution evidence.
