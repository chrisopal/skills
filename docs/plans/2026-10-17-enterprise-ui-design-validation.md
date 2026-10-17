# Enterprise UI Design v1.1 validation

Date: 2026-10-17. Scope: the reusable Skill, additive spatial tokens and one local simulation reference. Approved design and implementation scope: [spatial update plan](2026-10-17-enterprise-ui-design-spatial-update.md).

## Delivered

- Imported the installed v1.0 source into `enterprise-ui-design/`; updated the entrypoint and all three modes to consume one shared spatial reference.
- Defined shell/page/section/component inset ownership, outer-box versus text key lines, content-width strategies, semantic grouping, standard/compact density and responsive reflow. Defaults respect explicit user/project scope.
- Added 15 common spatial/density tokens and five compact overrides. All 40 v1.0 common values and both 28-value palettes remain unchanged. Existing consumers continue working; no downstream app or bundled token copy was migrated.
- Added a deterministic stdlib CSS emitter with a read-only `--check`. A frozen test fixture protects all 96 existing common/light/dark values.
- Moved the MateClaw action convention into an optional named-project compatibility reference, instead of imposing filled row buttons on every product. Removed repeated spacing prose and clarified action hierarchy.
- Reusable source under `assets/reference-workbench/` implements a simulated work-order list, filters, pagination and detail/edit dialog with local storage. It consumes shared tokens directly; it is not generated HTML output or a backend integration.

## Verification evidence

| Check | Result |
|---|---|
| System `quick_validate.py`, using existing Python3.13/PyYAML | Pass; default Python3.11 lacks PyYAML, no dependency installed |
| `python3 scripts/generate_tokens.py --check` | Pass; checked-in CSS exactly reproduces JSON |
| `python3 -m unittest discover -s tests -v` | 7 pass: full legacy contract, CSS parity, palette scope, density independence, variable resolution, contrast pairs, stale-output rejection |
| Markdown references | 17 local links resolve |
| Python AST and `node --check .../workbench.js` | Pass; standalone source has no app build/typecheck pipeline |
| Real Chromium through Playwright CLI | 320 assertions pass, 28 layout combinations; no runtime/console errors |
| Layout matrix | 390/768/1023/1024/1366/1440/1920 × light/dark × standard/compact |
| Actual geometry | Page inset16px narrow /32px desktop; panel20px standard /16px compact; controls34px /28px; cells12px /8px block; body14px unchanged; page/title and filter/first-cell key lines within the reference's1px rounding allowance |
| Interaction | Query/no result/reset, status/priority filtering, pagination, invalid-field draft preservation, simulated storage failure, actual save/reload, theme/density persistence, Escape/focus restoration, closed mobile-nav inertness and low-height submit reachability pass |
| Reading/reflow | Long Chinese owner and mixed Chinese/English note retained; actual viewport reflow and equivalent narrow width for200% desktop view checked. This is not a native browser zoom-engine test |

## Visual review

Inspected actual desktop light, desktop dark/compact, narrow light and dark, and desktop/narrow dialog screenshots. Fixed unintentional40px browser `dd` indent, empty feedback gaps, density controls blocked by fixed padding, an inappropriate overview max-width on the fluid list, and initial focus scrolling long narrow details past their first label. Waited for actual rendering/transition completion before final captures.

Final visual conclusion: the reference conforms to the approved spatial contract in the inspected states. No accepted reference image was supplied, so image-similarity/pixel-fidelity scoring is not applicable. Geometry assertions and visual judgment are separate evidence; neither establishes business acceptance.

An independent read-only verifier passed entrypoint/link/token/scoping checks and forward-applied the Skill to an existing Vue/Element Plus spacing scenario. Its two findings—partial legacy freeze and a blanket viewport gate—were remedied with the full96-value fixture and explicit task-scope precedence. Fresh direct checks confirm the corrections; no claim of a second independent review.

## Local artifacts and installation

Generated evidence stays in `projects/enterprise-ui-design-20261017/`: `browser-results.json`, `browser-run.log`, reusable-check execution input and screenshots under `evidence/`. Visual review state stays in `.omx/state/enterprise-ui-design/ralph-progress.json`; no similarity score is fabricated. These outputs are not committed.

The original installation is preserved locally in `projects/enterprise-ui-design-20261017/baseline/`. Synchronization into `~/.codex/skills/enterprise-ui-design/` requires an unchanged-baseline check, then source/installed SHA256 parity; the install receipt stays local. Reusable source, plan, this record and STATUS are included in the scoped Lore commit on the configured feature branch; final commit and remote equality are reported after push.

## Limits

No existing application was visually migrated; no live API, production data, deployment or customer/business acceptance was exercised. Other rendering engines, screen readers, production component libraries and fresh-session automatic Skill routing remain unverified. The local demo does not establish those claims. Existing unrelated WIP is preserved.
