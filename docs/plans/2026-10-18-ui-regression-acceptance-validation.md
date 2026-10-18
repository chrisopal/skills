# UI regression acceptance review — validation record

## Verdict and changed surface

The skill can guide per-page/per-control acceptance of a declared application scope. Its former self-reported coverage gate could not substantiate completeness. The revision imports the installed skill as maintained source in `ui-regression-acceptance/`, adds an independent scope check, and clarifies how constraints and visual rules become concrete cases. It remains an agent workflow using an existing real browser, not an autonomous UI crawler or a proof of exhaustive state/input coverage.

Changed source: `SKILL.md`, `agents/openai.yaml`, the business/control/evidence references, new `references/inventory-and-cases.md`, `scripts/check_coverage.py`, and `tests/test_check_coverage.py`. No dependency or business product was changed.

## Findings and remedies

| Baseline gap | Final behavior |
|---|---|
| An entire-application claim with one page/button passes | Separate source/runtime scope manifest is compared by page/control/check identities and bound by SHA-256; missing pages/controls do not reduce the denominator |
| One click ID covers all four dimensions | Distinct dimension assertions required; one actual operation/evidence file may support multiple assertions |
| A page containing any control counts as visually covered | Each page/context needs a `kind=page` instance and an applicable page-wide layout check |
| Unsupported N/A can hide an applicable check | Applicability/reasons frozen independently, changed applicability blocks the ledger |
| Missing replay or running-version records can pass | Replay command/prerequisites, scripts/logs, expected/observed runtime version and version evidence required |
| Missing rule must be BLOCKED yet still requires a reference | Explicit `missingContracts` permits honest BLOCKED without fabricated rules |
| Duplicate PASS before FAIL can suppress the failed verdict | Known declared failures retain FAIL regardless of duplicate order; duplicate entries remain invalid |

Schema changes are explicit: scope v1 + coverage v3. Old v2 does not silently pass; projects pinning the prior checker must update their integration and re-audit evidence. SHA/version metadata checks cannot establish evidence semantics or deployment identity on their own.

## Verification

- Baseline reproducer returned PASS/100% for one declared page/button and a single check shared across four dimensions. Initial new-gate regression run failed as expected; the duplicate-order correction also had a failing regression before its fix.
- `python3 -m unittest discover -s ui-regression-acceptance/tests -v`: **25 tests pass**. Covers complete scope, omitted pages/controls/checks, distinct dimensions, page layout, N/A, missing contracts, status priority, duplicate/missing results, scope/build/version changes, replay requirements, path traversal/absolute paths/escaping symlinks, missing/empty/hash-mismatched evidence and failure-history evidence. A half-inventory ledger remains 50% coverage; one of 16 checks remains 6.25%.
- Independent reviewer reproduced original gaps, ran the suite and 174 malformed-ledger / 114 malformed-scope probes without crashes, found the duplicate-order issue, then approved the corrected result after rerunning all25 tests. These probes are not a claim of exhaustive input fuzzing.
- System skill-creator quick validator passes using the existing Python3.13 with PyYAML. All6 local Markdown references resolve; Python AST parsing/compilation and staged whitespace check pass. No standalone lint/typechecker configuration applies to this Python-only skill; no new lint/typecheck dependencies were installed.
- Independent forward-use exercise, with only raw route/component/contract files and no running app: found **4 page contexts,15 known control instances,72 planned checks**, including a dialog without its own route, an inaccessible admin feature and a conditional field. It retained58 NOT_RUN /14 BLOCKED,0% execution and INCOMPLETE; unknown admin/runtime controls remain unknown rather than omitted. This exercise verifies planning/status behavior, not browser execution.
- Separate real Chromium155 exercise against an isolated two-route fixture with simulated business data: **18 representative checks:14 PASS,3 FAIL,1 BLOCKED**. It detected a fractional quantity accepted and persisted despite an integer contract, a conditional address still visible when hidden, and a selected dropdown label clipped after blur (28px versus240px contract). Legal1/99 boundaries, invalid0/100, leading zeroes, actual POST/independent GET/reload, nonfirst selection,390/1280 layout and start/end version observations were exercised. Desktop/mobile screenshots were actually viewed. No whole-app acceptance or business deployment is claimed.
- The first browser run used unsuitable native-select keyboard operations, producing two script-induced failures; the raw result was retained, the script corrected to real native selection and response-based waiting, and the same business assertions rerun. Final three failures are fixture behavior; the unavailable settings persistence rule remains BLOCKED. The deliberately defective fixture was not repaired.

## Evidence, installation and publication

Raw baseline, logs, forward exercise, disposable browser app, executed replay file, results and screenshots remain local under `projects/ui-regression-acceptance-20261018/`; they are excluded from the commit. Relevant files include `baseline-tests.log`, `duplicate-failure-red.log`, `final-tests.log`, `forward-output/summary.json` and `browser-smoke/results.json`. The browser replay is rerunnable with the existing browser MCP's run-code tool and `browser-smoke/replay.js` after starting `python3 browser-smoke/app.py` from its parent directory; the original source defects intentionally remain.

The forward-use reviewer identified friction in representing an offline plan and unknown child controls. A short offline plan example now distinguishes known candidate counts from unknown scope, keeps inventory incomplete, and explains why missing-runtime diagnostics are expected rather than product failures.

Installation compares original installed hashes with the preserved baseline before synchronization, then reads back SHA-256 equality for all8 reusable source/test files. Existing unrelated installed files/caches and repository WIP are preserved. Scoped source/docs/STATUS changes belong to the Lore commit on `codex/enterprise-dtx-skill-suite-runtime`; remote commit equality is checked during delivery. Generated outputs are not staged.

## Remaining limits

An independent manifest still needs an honest source/runtime reconciliation; the checker cannot detect a page omitted from both inputs or tell whether a reference is authoritative. This task did not test a production application, all supported browsers/roles/branches, screen readers, or mathematical exhaustiveness. Actual project use needs its URL, matching running build, role/data setup and business/UI contracts. Missing inputs remain BLOCKED/NOT_RUN instead of UI PASS.
