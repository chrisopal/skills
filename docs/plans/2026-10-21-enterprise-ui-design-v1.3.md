# Enterprise UI Design v1.3 execution plan

Scope: incrementally update enterprise-ui-design v1.2 on the current feature checkout. Preserve unrelated WIP, frozen v1 tokens, business/component guides and existing demos. No default push, merge, deployment or LIMS mutation; no new dependencies. Keep generated evidence local.

## Baseline difference inventory

| Decision | Existing surface | Action |
|---|---|---|
| Preserve | Create/Upgrade/Audit, Blueprint, task flow, notice/copy, component guides, spatial ownership, frozen token contract | Route to existing references; retain business behavior and legacy defaults |
| Correct | Blue-only language and profile-owned action palette; old CSS cascade tests | Make blue a default brand; validated brand semantics win; preserve equivalent compatibility assertions |
| Extend | Token JSON/emitter, workbench/order-flow, typography, external references | One resolver, precision profile, teal proof preset, shared runtime/recipes, cross-page fixture, font/resource contract |
| Merge | Overlapping profile/theme/density guidance and audit checklists | One configuration contract and structured rule/coverage registry; keep short task-based entrypoint |

## Work sequence and ownership

1. Baseline tests/read-back; external source research and screenshot feature mapping.
2. Token lane: preserve frozen values; validate ownership, references/cycles/fallback and full combinations; deterministic CSS/runtime bridge generation. Parent owns runtime consumer integration.
3. Reference lane: expand existing workbench into overview/list/details/form/workflow/analytics/component/state surfaces. Reuse its existing data, dialogs, storage and order-flow link. Add shared configuration entrypoint and recipes; preserve draft/selection/filter/page/focus across switching.
4. Audit lane: executable candidate scanner, rule registry, coverage ledger and structured reports; strengthen existing mode, typography and migration documentation.
5. Recheck: all token combinations; browser default all surfaces plus risk/pairwise configurations and component combinations; 390/768/1440/1920, zoom, low-height dialog, long content, real reachable error/empty/loading/permission fixtures. Inspect before/after screenshots separately from technical and behavior conclusions. Fix findings.

## Reference mapping

| Reference feature | General rule | Implementation | Evidence |
|---|---|---|---|
| Strong heading and record values | Role hierarchy with restrained emphasis | Typography tokens and precision role/recipe rules | Computed typography + screenshot |
| Large comparable numbers, quieter units | Preserve precision, align numbers and units | Metric/number/unit roles, continuous metric rows | Values, computed numeric style, screenshot |
| Tight within-group, distinct sections | Space reflects relationships | Stack/Inline/Section/DataRegion recipes | Owned inset/gap measurement |
| Canvas/panel/overlay distinction | Few clear surface levels | Theme surface semantics + profile border/radius | All combinations + portal/computed styles |
| Recognizable selected/control state | Separate action, selection, focus and read-only values | Brand semantic pair sets | Contrast + keyboard/interaction |

Do not infer exact font/DPR/CSS size from pixels. Do not adopt purple, ads, small hit targets, bottom-nav obstruction, weak contrast or phone aspect ratio. Natural trailing whitespace is valid. No pixel-replication score.

## Completion evidence

Keep technical audit, visual/task review and behavior regression as separate results; Pass/Fail/Not tested/Not applicable with reasons. P0/P1 failures prevent overall pass. Report implemented versus observed versus untested, font evidence and host integration gaps. Do not label fixture validation as LIMS-wide acceptance.
