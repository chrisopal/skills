# ppt-maker-direct-pptx Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement 8 design themes from `2026-04-25-ppt-direct-pptx-optimization-design.md` so the skill produces stylistically-coherent, layout-reliable PPTX decks with image-on-demand, customizable styles, page-level locking, and automated quality gates.

**Architecture:**
The implementation extends the existing `ppt-maker-direct-pptx` skill with a 7-gate confirmation flow, three new state machines (image lifecycle, outline/intent/image per page), a 12-pattern layout library, a multi-input style system (preset / NL generation / reference extraction), a 4-category lint pipeline embedded at gates, and a two-tier preview system (pattern catalog + per-page wireframes). Existing artifacts are kept backward-compatible via `--legacy-4-gates` and default fallbacks.

**Tech Stack:**
- Python 3.10+ (existing skill scripts)
- Node.js + PptxGenJS (existing slide renderer)
- LibreOffice headless (new optional dep, for catalog PNG rendering)
- OpenRouter / `text_model` and `vision_model` (existing model wiring)
- pytest for tests (introduce if not present)
- jsonschema for schema validation

**Source design doc:** `docs/plans/2026-04-25-ppt-direct-pptx-optimization-design.md`

---

## Phase Map

| Phase | Title | Depends on | Output |
|---|---|---|---|
| 1 | Foundations: schemas + state-field migration | — | New schemas + status fields on existing artifacts |
| 2 | Pattern library | Phase 1 | 12 pattern JSON + loader + validator |
| 3 | Style system (preset / NL / reference) | Phase 1 | `master_style.json` + 3 input scripts |
| 4 | Preview system (catalog + wireframe) | Phase 2, 3 | Catalog PNG generator + SVG wireframe |
| 5 | Lint pipeline (4 categories + auto-fix) | Phase 1, 2 | 6 lint scripts + lint_report.json |
| 6 | Page state machine + dashboard | Phase 1, 5 | dashboard / lock / reset / regenerate-image scripts |
| 7 | 7-gate orchestration + renderer rewrite | Phases 1-6 | `run_ppt_job.py` v2 + `assemble_pptx.py` v2 |

Each phase ends in a tagged commit so progress is durable.

---

## Phase 1: Foundations — Schemas + Status Field Migration

**Goal:** Land the new JSON schemas and add status fields to existing artifacts so downstream phases have a stable contract.

### Task 1.1: Add pytest infrastructure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `assets/python_requirements.txt` (add `pytest>=7`, `jsonschema>=4`)
- Create: `tests/fixtures/sample_legacy_job.json` (a copy of an existing valid `job.json` for migration tests)

**Step 1:** Add deps to `python_requirements.txt`.

**Step 2:** `pip install -r assets/python_requirements.txt` — verify install passes.

**Step 3:** Create `tests/conftest.py` exposing `tests/fixtures/` paths.

**Step 4:** Run `pytest tests/ -v` — expected: 0 tests collected, no errors.

**Step 5:** Commit.
```bash
git add tests/ assets/python_requirements.txt
git commit -m "chore: bootstrap pytest infrastructure for skill"
```

### Task 1.2: Write `master_style.schema.json`

**Files:**
- Create: `assets/schemas/master_style.schema.json`
- Create: `tests/test_master_style_schema.py`

**Schema fields (per design §2):**
- existing fields from `huixin_master_style_brief.json`
- new: `source` (enum: preset | nl_generated | reference_extracted | hybrid)
- new: `parent_template_id` (string | null)
- new: `lock_fields` (array of dotted paths)
- new: `pattern_palette` (object with optional `card_shadow`, `connector_weight`, `icon_style`)
- new: `confidence` (object: field path → 0-1 number, optional)

**Step 1:** Write a failing test that loads `assets/huixin_master_style_brief.json` and validates it against the new schema (must pass after we extend the existing brief with `source: "preset"`).

**Step 2:** Run test — expect schema-not-found error.

**Step 3:** Write the schema.

**Step 4:** Update each existing `*_master_style_brief.json` in `assets/` to add `source: "preset"`, `parent_template_id: null`.

**Step 5:** Run tests — expect pass.

**Step 6:** Commit.

### Task 1.3: Write `pattern.schema.json`

**Files:**
- Create: `assets/schemas/pattern.schema.json`
- Create: `tests/test_pattern_schema.py`
- Create: `tests/fixtures/pattern_minimal.json` (minimal valid pattern doc)

**Schema fields (per design §3):**
- `pattern_id`, `slots[]` (each with `name, required, max_chars?, min_chars?, accepts_image?`), `layout_regions` (`title`, `content`, `images?`), `style_hooks{}`, `wireframe_template` (string SVG template), `js_renderer` (relative path)

**TDD steps as in 1.2.**

### Task 1.4: Write `lint_report.schema.json`

**Files:**
- Create: `assets/schemas/lint_report.schema.json`
- Create: `tests/test_lint_report_schema.py`

**Schema fields (per design §6):**
- `ts`, `gate`, `results[]` (each: `page_no?`, `category` enum, `rule`, `severity` enum, `detail`, `auto_fixable`), `deck_level[]`, `overrides[]?`

**TDD steps as in 1.2.**

### Task 1.5: Extend `outline.schema.json` and `slide_prompts.schema.json` with status fields

**Files:**
- Modify: `assets/schemas/outline.schema.json` — add `slides[].outline_status` (enum)
- Modify: `assets/schemas/slide_prompts.schema.json` — add `slides[].intent_status` and `slides[].pattern_id?`, `slides[].layout_mode` (enum: pattern | custom), `slides[].slots?`
- Modify: `assets/schemas/slide_specs.schema.json` — add `slides[].image_placeholders[].status`, `slides[].image_placeholders[].history?`
- Create: `tests/test_status_field_migration.py`

**Test cases:**
- legacy artifact with no status fields validates successfully (default values applied by loader)
- new artifact with full status fields validates
- invalid status value rejected

**Step 1:** Write tests covering all three cases.

**Step 2:** Run tests — expect all to fail.

**Step 3:** Update schemas to add fields with `default` values:
  - `outline_status`: default `"draft"`
  - `intent_status`: default `"draft"`
  - `image_placeholders[].status`: default `"placeholder"`
  - `layout_mode`: default `"custom"` (so legacy slides keep working)

**Step 4:** Run tests — expect pass.

**Step 5:** Commit.

### Task 1.6: Migration helper

**Files:**
- Create: `scripts/migrate_legacy_artifacts.py`
- Create: `tests/test_migrate_legacy_artifacts.py`

**Behavior:**
- Reads `outline.json`, `slide_prompts.json`, `slide_specs.json`
- Adds default status fields if missing
- Writes back in place (with `--dry-run` option to preview)

**TDD:**
- Test: load `tests/fixtures/sample_legacy_job.json` artifacts, run migrator, assert all status fields present with defaults
- Test: idempotent — running twice doesn't change state

**Phase 1 final commit:** `feat(phase-1): foundation schemas + status field migration`

---

## Phase 2: Pattern Library

**Goal:** Define and load all 12 patterns so downstream phases can reference them by id.

### Task 2.1: Pattern loader + validator

**Files:**
- Create: `scripts/lib/pattern_registry.py`
- Create: `tests/test_pattern_registry.py`

**API:**
```python
class PatternRegistry:
    def __init__(self, patterns_dir: Path): ...
    def get(self, pattern_id: str) -> Pattern: ...
    def list_ids(self) -> list[str]: ...
    def validate_slots(self, pattern_id: str, slots: dict) -> list[ValidationError]: ...
```

**Tests:**
- Loading a valid pattern dir succeeds
- Loading a dir with one invalid pattern raises `PatternSchemaError`
- `validate_slots` reports missing required slots
- `validate_slots` reports `max_chars` violations

**TDD steps standard.**

### Task 2.2: Author 12 pattern JSON files

**Files:**
- Create: `assets/patterns/cover.json`
- Create: `assets/patterns/section_divider.json`
- Create: `assets/patterns/conclusion_top_modules.json`
- Create: `assets/patterns/two_column_compare.json`
- Create: `assets/patterns/four_card_matrix.json`
- Create: `assets/patterns/three_stage_path.json`
- Create: `assets/patterns/kpi_strip.json`
- Create: `assets/patterns/architecture_layers.json`
- Create: `assets/patterns/before_after.json`
- Create: `assets/patterns/evidence_grid.json`
- Create: `assets/patterns/summary_takeaways.json`
- Create: `assets/patterns/freeform.json`
- Create: `tests/test_pattern_authoring.py`

**Per pattern, supply (per design §3):**
- `pattern_id`, `slots[]`, `layout_regions`, `style_hooks`, `wireframe_template` (SVG with `{slot_name}` placeholders), `js_renderer` (e.g., `slides/renderers/four_card_matrix.js`)

**Test:** load every pattern via `PatternRegistry`, assert `len(list_ids()) == 12` and each passes the schema.

**Step 1:** Write the test.
**Step 2:** Run — expect failure (patterns don't exist yet).
**Step 3:** Author all 12 patterns one by one, committing in groups of 3-4 to avoid massive commits.
**Step 4:** Run — expect pass.
**Step 5:** Phase commit: `feat(phase-2): pattern library with 12 layouts`

### Task 2.3: Pattern → JS renderer function stubs

**Files:**
- Create: `slides/renderers/<pattern_id>.js` (12 files, one per pattern, with `createSlide(pres, theme, slots, regions)` signature)
- Create: `tests/test_renderer_stubs.js` (Node test asserting each renderer is requireable and exports `createSlide`)

**Note:** Stubs return a placeholder layout with a labeled grid (e.g., for `four_card_matrix`, draws 4 grey cells with cell name labels). Real renderer implementation is Phase 7.

**TDD via Node + a small test runner; tests assert exportability and basic call signature.**

---

## Phase 3: Style System (Preset / NL / Reference)

**Goal:** Three style input paths all producing valid `master_style.json`.

### Task 3.1: Preset inheritance helper

**Files:**
- Create: `scripts/lib/style_inherit.py`
- Create: `tests/test_style_inherit.py`

**API:**
```python
def inherit_preset(preset_id: str, overrides: dict) -> dict:
    """Load preset, apply overrides, return master_style dict.
    Records `source: "hybrid"`, `parent_template_id: preset_id`."""
```

**Tests:**
- Inherit huixin with `{color_strategy: {primary_green: "#1A237E"}}` → result has new color, all other fields preserved
- Inherit dark-english with `{language: "zh-CN"}` → result has new language
- Override a field listed in `lock_fields` of preset → raises `LockedFieldError`

### Task 3.2: NL → master_style script

**Files:**
- Create: `scripts/style_from_nl.py`
- Create: `tests/test_style_from_nl.py` (uses mocked LLM client)

**Behavior:**
- Input: free-text style description
- Calls `text_model` with a prompt that instructs JSON output matching `master_style.schema.json`
- Validates result against schema
- Sets `source: "nl_generated"`, `confidence` populated by model self-rating
- Writes to `artifacts/master_style.json`

**Tests:**
- Mock LLM returns valid JSON → output validates and has `source: "nl_generated"`
- Mock LLM returns invalid JSON → script retries up to 3 times, then errors clearly
- Mock LLM returns partially-valid JSON → script reports which fields failed

**Step 1-5:** Standard TDD. Use `unittest.mock.patch` on the model client.

### Task 3.3: Reference-image → master_style script

**Files:**
- Create: `scripts/style_from_reference.py`
- Create: `scripts/lib/palette_extraction.py` (pure-Python: `colorthief` or k-means on image)
- Create: `tests/test_style_from_reference.py`
- Create: `tests/fixtures/sample_reference.png` (a small PPT screenshot)

**Behavior:**
- Input: image path or PPT path (PPT → first slide → PNG via LibreOffice)
- Step A: extract 5-7 dominant colors via `palette_extraction.py` (deterministic, no LLM)
- Step B: call `vision_model` with the image + extracted palette to fill in `typography`, `module_layout_patterns` hints, `forbidden_elements`
- Step C: assemble master_style with `source: "reference_extracted"`, low-confidence fields flagged

**Tests:**
- `palette_extraction.extract(image)` returns 5+ hex colors deterministically (snapshot test on fixture image)
- Mocked vision model + real palette → produces valid master_style
- PPT input is converted via LibreOffice (skip test if libreoffice not on PATH)

### Task 3.4: Style entry-point CLI

**Files:**
- Create: `scripts/define_style.py` (dispatcher)
- Create: `tests/test_define_style.py`

**CLI:**
```
python scripts/define_style.py preset --id huixin [--override 'color_strategy.primary_green=#1A237E']
python scripts/define_style.py nl --description "深蓝紫色赛博朋克"
python scripts/define_style.py reference --file path/to/ref.png
```

All write to `artifacts/master_style.json` and print where it was saved.

**Phase commit:** `feat(phase-3): multi-input style system (preset/nl/reference)`

---

## Phase 4: Preview System

**Goal:** Pattern catalog PNGs + per-page SVG wireframes.

### Task 4.1: Pattern catalog renderer

**Files:**
- Create: `scripts/render_pattern_catalog.py`
- Create: `slides/catalog_runner.js` (Node script: take pattern_id + master_style + sample data, output single-slide PPTX)
- Create: `tests/test_render_pattern_catalog.py`

**Pipeline:**
1. For each pattern, load lorem-ipsum sample slots from `assets/patterns/<id>.sample.json`
2. Run `node slides/catalog_runner.js --pattern X --style Y --out tmp.pptx`
3. Convert tmp.pptx → PNG via `libreoffice --headless --convert-to png`
4. Save to `artifacts/pattern_catalog/<style_hash>/<pattern_id>.png`
5. Cache by style hash; skip regen if cached

**Sample data files (12 new):**
- `assets/patterns/cover.sample.json` (and one per pattern)

**Tests:**
- Cache hit: re-running with same style hash returns cached path, doesn't invoke LibreOffice
- Cache miss: invokes pipeline, produces PNG, stores under correct hash dir
- LibreOffice unavailable: falls back to SVG wireframe output and prints warning

### Task 4.2: Per-page wireframe renderer (SVG)

**Files:**
- Create: `scripts/render_wireframe.py`
- Create: `tests/test_render_wireframe.py`

**Behavior:**
- Input: `page_intent` dict (with `pattern_id` + `slots`)
- Loads `pattern.wireframe_template` (SVG string with `{slot_name}` placeholders)
- Substitutes truncated slot text (max_chars-bound) into template
- Saves to `artifacts/wireframes/page-<NN>.svg`
- Pure string templating, no Node, no LibreOffice — must run in <50ms per page

**Tests:**
- Wireframe for `four_card_matrix` with 4 cells produces SVG with all 4 cell labels
- Slot text exceeding `max_chars` is truncated with ellipsis
- Missing required slot raises `IncompleteIntentError` (also fed back to lint)

### Task 4.3: Preview dashboard aggregator

**Files:**
- Create: `scripts/preview_dashboard.py`
- Create: `tests/test_preview_dashboard.py`

**Output:** A markdown / HTML page that embeds all wireframe SVGs in deck order (used at gate 5).

**Phase commit:** `feat(phase-4): preview system (catalog + wireframe)`

---

## Phase 5: Lint Pipeline

**Goal:** Six lint scripts + orchestrator + auto-fix.

### Task 5.1: Schema lint

**Files:**
- Create: `scripts/lint_schema.py`
- Create: `tests/test_lint_schema.py`

**Checks:** all 4 schemas + page_count match + duplicate page_no detection.

**TDD:** test with synthetic valid/invalid artifacts; assert lint_report.json output matches expected severities.

### Task 5.2: Geometry lint

**Files:**
- Create: `scripts/lint_geometry.py`
- Create: `scripts/lib/geometry.py` (rect-overlap, in-bounds checks)
- Create: `tests/test_lint_geometry.py`

**Checks:**
- `layout_regions.title` ∩ `layout_regions.content` = ∅
- `layout_regions.images` ∩ `layout_regions.content` = ∅
- All regions ⊆ [0, 13.333] × [0, 7.5] inches (16:9 inches)
- Card height ≥ 1.0 inch when card contains bullet list
- Font size ∈ [master_style.typography.body_text size range]

**TDD:** synthetic specs trigger each rule individually.

### Task 5.3: Style consistency lint

**Files:**
- Create: `scripts/lint_style.py`
- Create: `tests/test_lint_style.py`

**Checks (deck-level):**
- Title font size: same value across all `intent_status=locked` slides
- Color palette compliance: all hex colors used in slide_specs ⊆ master_style.color_strategy.* values
- forbidden_elements not present (regex over slide_specs JSON)

**TDD:** spec where one page uses non-palette color → flag that page; spec where all comply → pass.

### Task 5.4: Content quality lint (LLM judge)

**Files:**
- Create: `scripts/lint_content.py`
- Create: `tests/test_lint_content.py`

**Checks (LLM-judged):**
- Each page has exactly one `core_message`
- Cross-page duplicate `core_message` (similarity > 0.8)
- Audience fit: prompt LLM to rate 0-1; <0.6 → warn

**Flags:**
- `--skip-content-judge` for cost-saving runs

**TDD:** mock LLM responses; verify report assembly.

### Task 5.5: Lint orchestrator

**Files:**
- Create: `scripts/run_all_lints.py`
- Create: `tests/test_run_all_lints.py`

**Behavior:**
- Args: `--gate gate_5 | gate_7`
- Runs the lint scripts appropriate for that gate (per design §6 table)
- Aggregates into single `artifacts/lint_report.json`
- Sets exit code 0 (pass), 1 (warn-only), 2 (fail)
- Updates page-level state machine: any `severity=fail` flips that page's status to `needs_rework`

### Task 5.6: Auto-fix runner

**Files:**
- Create: `scripts/auto_fix_lint.py`
- Create: `tests/test_auto_fix_lint.py`

**Behavior:**
- Loads `lint_report.json`, finds all `auto_fixable=true fail` entries
- Applies known fixers: shrink overlapping regions, clamp out-of-range font sizes, snap to nearest palette color
- Each fix records a diff in `lint_report.json.fixes_applied`
- Sets affected pages' status to `pending_review` (not `locked`) so user must re-confirm

**Phase commit:** `feat(phase-5): lint pipeline + auto-fix`

---

## Phase 6: Page State Machine + Dashboard

**Goal:** Make per-page status the unifying API for all interactive ops.

### Task 6.1: Page state machine library

**Files:**
- Create: `scripts/lib/page_state.py`
- Create: `tests/test_page_state.py`

**API:**
```python
class PageStateMachine:
    LAYERS = ("outline_status", "intent_status", "image_status")
    STATES = ("draft", "pending_review", "locked", "needs_rework")

    def transition(self, page_no: int, layer: str, to_state: str, reason: str): ...
    def can_transition(self, page_no: int, layer: str, to_state: str) -> bool: ...
    def aggregate_image_status(self, page_no: int) -> str: ...
    def history(self, page_no: int) -> list[dict]: ...
```

**Tests:**
- Valid transitions per the state diagram in §5
- Invalid transitions raise `IllegalTransitionError`
- `intent_status: pending_review` only allowed if `outline_status: locked`
- `aggregate_image_status` reflects child placeholder states correctly

### Task 6.2: Dashboard

**Files:**
- Create: `scripts/dashboard.py`
- Create: `tests/test_dashboard.py`

**Behavior:** loads job artifacts + lint_report, prints the table from design §5. Supports `--json` for machine-readable output.

### Task 6.3: lock / reset / regenerate-image

**Files:**
- Create: `scripts/lock_pages.py`
- Create: `scripts/reset_pages.py`
- Create: `scripts/regenerate_image.py`
- Create: `tests/test_lock_reset.py`
- Create: `tests/test_regenerate_image.py`

**Each:** thin CLI wrapping `PageStateMachine` + `assemble_pptx.py` patches.

**Phase commit:** `feat(phase-6): page state machine + dashboard`

---

## Phase 7: 7-Gate Orchestration + Renderer Rewrite

**Goal:** Wire all subsystems into the new flow.

### Task 7.1: Update `generate_image_assets.py` to state-machine-aware

**Files:**
- Modify: `scripts/generate_image_assets.py`
- Create: `tests/test_generate_image_assets_state.py`

**Changes:**
- Default scan: `status == "pending"` placeholders
- Add `--ids id1,id2` flag for targeted runs
- On success: status → `generated`, save path
- On failure: status → `placeholder`, write `fallback_reason`
- Don't process `skipped` or `generated`

### Task 7.2: Update `assemble_pptx.py` for status-driven rendering

**Files:**
- Modify: `scripts/assemble_pptx.py`
- Create: `tests/test_assemble_pptx_status.py`

**Changes:**
- For each placeholder, branch on `status` (per design §4 table)
- `skipped` placeholders trigger `layout_regions` recompute (content absorbs image area)
- `placeholder` status renders styled placeholder shape (grey fill + primary stroke + center icon + prompt watermark)
- `generated` calls `addImage`

### Task 7.3: Update `regenerate_single_slide.py` and `sync_job_artifacts.py`

**Files:**
- Modify: `scripts/regenerate_single_slide.py` — sets target page state to `needs_rework` first, then regenerates and sets to `pending_review`
- Modify: `scripts/sync_job_artifacts.py` — preserves status fields when syncing edits

**TDD:** lifecycle test (initial → regen → review → lock).

### Task 7.4: Rewrite `run_ppt_job.py` with 7-gate orchestration

**Files:**
- Modify: `scripts/run_ppt_job.py`
- Create: `tests/test_run_ppt_job_gates.py`

**New flow (per design §1):**
- Gate 1 requirement: explicit per-field confirmation; fails if missing fields or ambiguous "yes"
- Gate 2 template/style: dispatch to `define_style.py`
- Gate 3 style preview: invoke `render_pattern_catalog.py` + sample render; loop until `style_confirmed=true`
- Gate 4 outline: generate, then per-page `outline_status` lock loop
- Gate 5 page intents: generate, run schema+content lint, render wireframes, per-page `intent_status` lock loop
- Gate 6 image plan: per-page placeholder status decision
- Gate 7 pre-render: run geometry+style lint, show dashboard, require `--override-lint` for warns
- Render: `assemble_pptx.py`

**Backward-compat flags:**
- `--legacy-4-gates`: skip gates 3, 6, 7
- `--lint-mode loose`: downgrade fails to warns

**Tests:**
- Each gate refuses to advance without explicit approval flag
- Lint fail at gate 5 blocks gate 6 entry
- `--legacy-4-gates` runs the old flow successfully

### Task 7.5: Documentation update

**Files:**
- Modify: `SKILL.md` — add 7-gate workflow + new scripts
- Modify: `references/workflow.md` — document new step sequence
- Modify: `references/conversational-mode.md` — add explicit confirmation phrasing for each new gate
- Create: `references/state-machines.md` — document image lifecycle + page state machine
- Create: `references/lint-rules.md` — enumerate every rule + severity + auto-fixability

### Task 7.6: End-to-end smoke test

**Files:**
- Create: `tests/test_e2e_smoke.py`

**Steps:**
- Build a tiny 3-page job spec (cover + matrix + summary)
- Drive through all 7 gates with auto-approve flags
- Assert: final `.pptx` exists, has 3 slides, lint_report.json has 0 fails

**Phase commit:** `feat(phase-7): 7-gate orchestration + state-driven renderer`

**Tag final release:** `git tag direct-pptx-v2.0.0`

---

## Per-Phase Acceptance Criteria

A phase is "done" only when:
- All tasks committed
- All tests pass: `pytest tests/ -v`
- New schemas validate against existing fixture data
- No regressions: `python scripts/validate_job.py assets/ppt_job_template.json` still passes
- Phase commit tagged

---

## Risks and Pre-Mitigations

| Risk | Pre-mitigation |
|---|---|
| LibreOffice not installed in user envs | Fallback to SVG wireframe-only previews, print warning |
| Vision model cost on reference extraction | `--no-vision` flag falls back to palette-only extraction |
| LLM JSON malformedness in NL style gen | 3-retry loop + schema validation; clear error if all retries fail |
| Backward compatibility breakage | All status fields default; `--legacy-4-gates` flag keeps old flow alive |
| Pattern library too restrictive for novel slides | `freeform` pattern remains available; `layout_mode: custom` respected |
| 12 patterns too few in practice | Author 8-12 in this plan; add new ones in Phase 2 follow-ups without breaking changes |

---

## Out of Scope (deferred, document for v2.1)

- Live thumbnail streaming during JS generation (theme 5 option d)
- Web-UI for the dashboard (CLI-only for v2.0)
- Mid-deck pattern library overrides per slide
- Cross-deck style libraries (organization-level palette inheritance)
- Audio/video embedding
