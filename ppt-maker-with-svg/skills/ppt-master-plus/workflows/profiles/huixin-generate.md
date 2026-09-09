---
description: Default low-context Huixin generation with selective template reuse and verified editable PPTX export.
---

# Huixin Generate

Generate one source-grounded presentation using one Huixin theme. This profile
owns ordinary Huixin generation; it reuses the engine's lockless exporter,
not the full Quick or Default workflow documents.

## 1. Boundary

| Request | Behavior |
|---|---|
| New Huixin deck, including monthly reports and complex architectures | Use this profile regardless of page count or information density |
| Multiple alternative designs, staged confirmation, interactive preview, spec refinement, or reusable native Master/Layout/placeholder output | Route to full `generate-pptx.md` before authoring |
| Supplied non-Huixin workspace or explicit non-Huixin/free design | Use `quick-generate.md`, unless full planning is requested |
| Preserve an existing PPTX 1:1, reconstruct images, fill native slides, or enhance a finished deck | Keep the dedicated route from `routing.md` |

**Hard rule**: do not read Strategist, Confirm UI, full Quick/Default, mode/style
catalogs, or image-rendering catalogs during ordinary Huixin generation. Do not
create root `design_spec.md`, `spec_lock.md`, three alternatives, or simulated
role handoffs. Notes, animation, narration, and web/AI images are off unless the
user requests them or the selected template/content requires that capability.
Brand logos and backgrounds do not trigger image acquisition or image planning.

## 2. Prepare Once

Use one Python 3.10+ interpreter for the entire run. Execute:

```bash
python3 ${SKILL_DIR}/scripts/huixin_runtime.py preflight
```

On failure, install only the reported missing base requirements in that same
environment, then retry once. Do not install optional provider SDKs or launch
a browser server for a plain deck. Additional import/render dependencies are
checked only for the actual input or feature. Never change installed Skill code
to work around an error during generation; use CLI help and the first relevant
diagnostic, then report an unresolved blocker.

Read source content once. For XLSX, DOCX, PDF, or PPTX, use the matching
`scripts/source_to_md/` converter's `--help` and its output, not both raw content
and full sidecars. Preserve Excel values, units, dates, missing values, and
formula-result limitations. Do not invent metrics. Research only missing facts
that affect the requested claims; load `stages/topic-research.md` only then.

Select a Deck by explicit registered id/alias first, otherwise by this table.
Read `templates/decks/decks_index.json` only when the choice is ambiguous; do
not scan template directories or read all six specifications.

| Primary job | Deck id |
|---|---|
| Monthly/quarterly work review: review, results, highlights, next plan | `huixin_periodic_business_review` |
| Sales forecast, opportunities, finance, staffing, KPI dashboard | `huixin_management_report` |
| Product, system integration, layered/domain architecture | `huixin_product_solution` |
| Diagnosis, strategy, AI transformation, governance decisions | `huixin_consulting_strategy` |
| Training, SOP, exercises, enablement | `huixin_training_enablement` |
| Promotion, product launch, customer event | `huixin_market_promotion` |

Create a fresh project outside the installed Skill and install one theme:

```bash
python3 ${SKILL_DIR}/scripts/huixin_runtime.py prepare \
  --deck <deck_id> --name <project_name> --base-dir <absolute_output_parent>
```

Read the returned project-local template spec once. It owns the current logo,
background assets, font roles, colors, page catalog, and narrative rules. Open
only prototypes selected for actual pages. Copying assets is not a request to
read images or SVG source into context. Keep source assets external to prompts;
never print base64 data, whole icon catalogs, or the installed file tree.

## 3. Author Adaptively

Resolve one page roster and theme in active context. For long runs, save only a
short `brief.md` with source paths, selected deck, page titles/prototypes, factual
constraints and completed filenames; no chain of reasoning or duplicate source
content. After context loss, read that brief and inspect only unfinished/changed
pages. Never restart a completed deck merely because context was compacted.

**Template precedence**: reuse a prototype when its role and capacity fit.
Deterministic XML placeholder replacement and copying unchanged brand chrome
are allowed; validate text fit after replacement. Use XML escaping, never raw
unescaped user text. Do not regenerate unchanged logos, backgrounds, or pages.
If no prototype fits, author a custom editable SVG preserving the selected
Huixin font roles, logo, colors, background rhythm and narrative logic. Complex
multi-layer/domain diagrams need real secondary functions and relationships,
not artificially empty five-row shells or text shrunk to fit a rigid template.

Read `references/shared-standards-core.md` and `references/semantic-svg.md`
once before authoring. Then load only what is actually used:

| Feature | Additional reference |
|---|---|
| Relationship/architecture/process geometry | `references/executor-structure.md` |
| Office presets, Boolean paths, special native shape treatment | `references/native-shape-authoring.md` |
| Gradients, shadows, patterns, masks | `references/svg-effects.md` |
| Quantitative chart | `references/executor-chart.md`, then `workflows/stages/verify-charts.md` before final check |
| Row/column table | `references/executor-table.md` |
| Native editable chart/table payload | `references/native-data-interface.md` |
| Image embedding, including unchanged brand assets | `references/svg-image-embedding.md` |
| New photographic/illustrative composition | `references/executor-image.md`; acquisition references only for the selected source |
| Explicit notes, animation, audio, or visual review | Corresponding existing reference/stage only |

Use one concrete installed font family compatible with the template, one
canvas (normally 1280x720), and zero-padded page names. Name any required font
substitution. Preserve source content and required page count. Reflow, reorganize,
or split only where permitted; never hide overflow with tiny text.

**Flat export**: every SVG in `svg_output/` must contain the complete visible
page, including brand chrome. Preserve semantic groups and bounds. Set root
`data-pptx-page-role`; remove copied Master/Layout/placeholder ownership metadata
when adapting structured prototypes. This exports editable slide objects, not
reusable native template masters. Reference project-local assets with paths,
not inline base64. Do not place unused prototypes in `svg_output/`.

## 4. Verify and Deliver

Check the first authored page visually as the theme anchor without a confirmation
stop. Continue the roster, then inspect a contact sheet and the densest chart,
table, or architecture pages at readable resolution. Verify factual coverage,
logo/font consistency, overlap, cropping, and text fit. A machine pass alone
does not prove visual quality. Use the host renderer; do not install multiple
renderers or repeatedly inspect every unchanged page.

Run chart-coordinate verification when applicable. For a plain deck execute:

```bash
python3 ${SKILL_DIR}/scripts/huixin_runtime.py export <project_path>
```

This serially runs the full final SVG checker, native editable export with
`--quick-generate --no-notes`, and PPTX delivery audit. It saves full logs locally
and returns a compact summary. Any failing stage stops delivery. Repair only
affected SVGs/resources; rerun export so the final whole-deck gate is fresh.
Warnings are advisory to inspect, not a reason for endless cosmetic rewrites.

For explicitly requested notes, create/split them through `executor-notes.md`
and `total_md_split.py`, then use `export <project_path> --with-notes`. For other
optional production behavior, use its owning stage and documented exporter
flags, and audit the resulting PPTX; never silently drop requested capabilities.

Report the PPTX path, page count, and material verification limitations only.
Do not print all rules, logs, source data, or a per-tool progress checklist.
