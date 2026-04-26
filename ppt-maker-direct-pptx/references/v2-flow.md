# v2 Direct-PPTX Flow

The v2 flow extends the original 4-gate workflow with three new gates, a
multi-input style system, a 12-pattern layout library, two state machines,
and an automated lint pipeline.

Use `python scripts/run_ppt_job_v2.py path/to/job.json --auto-approve` to
walk a job through every gate, or `--gate <name>` / `--next` to advance one
gate at a time. Per-gate state is persisted in `job["v2_gates"]`.

## The 7 Gates

| # | Gate id                | Driver script                     | Output artifact                 |
|---|------------------------|-----------------------------------|---------------------------------|
| 1 | `gate_1_requirement`   | (built into orchestrator)         | requirement fields validated    |
| 2 | `gate_2_style`         | `define_style.py`                 | `artifacts/master_style.json`   |
| 3 | `gate_3_style_preview` | `render_pattern_catalog.py`       | `artifacts/pattern_catalog/<hash>/*.svg` + `manifest.json` |
| 4 | `gate_4_outline`       | `run_all_lints.py --gate gate_4`  | `artifacts/lint_report.json`    |
| 5 | `gate_5_intent`        | `run_all_lints.py --gate gate_5` + `render_wireframe.py` | wireframes + lint report |
| 6 | `gate_6_image_plan`    | (counts placeholder status)       | image plan summary              |
| 7 | `gate_7_pre_render`    | `run_all_lints.py --gate gate_7` + `dashboard.py` | full lint + dashboard |

Each per-page `*_status` field follows the page state machine
(see `state-machines.md`).

## New Scripts (Phases 3–7)

### Style system

- `define_style.py {preset|nl|reference}` — three input paths converging on
  `artifacts/master_style.json`.
- `scripts/lib/style_inherit.py` — preset + override helper.
- `style_from_nl.py`, `style_from_reference.py` — LLM- and image-driven
  generators (callers injectable for offline tests).

### Pattern + preview

- `scripts/lib/pattern_registry.py` — load `assets/patterns/*.json` and
  validate slot data.
- `render_pattern_catalog.py` — per-pattern SVG previews with
  master_style colors substituted.
- `render_wireframe.py` — per-page SVG wireframe for gate-5 review.
- `preview_dashboard.py` — aggregate wireframes into HTML or markdown.

### State and dashboard

- `scripts/lib/page_state.py` — `PageStateMachine` with three layers per
  page (outline / intent / image).
- `dashboard.py` — printable / JSON deck dashboard joining state +
  lint report.
- `lock_pages.py`, `reset_pages.py`, `regenerate_image.py` — thin CLIs
  over the state machine.

### Lint pipeline

- `lint_schema.py`, `lint_geometry.py`, `lint_style.py`, `lint_content.py`
  (see `lint-rules.md`) — produce per-page and deck-level results.
- `run_all_lints.py --gate <name>` — orchestrator that aggregates into
  `lint_report.json` and optionally flips fail-tagged pages to
  `needs_rework`.
- `auto_fix_lint.py` — applies known fixers to `auto_fixable=true` failures
  and resets affected pages to `pending_review`.

## Backward compatibility

- Existing `run_ppt_job.py` is untouched; v2 lives alongside it.
- Legacy artifacts without status fields validate and run via the
  `migrate_legacy_artifacts.py` helper (Phase 1).
- All shipped presets carry `source: "preset"`. Custom styles emit
  `source: "nl_generated"` or `"reference_extracted"`; preset-with-overrides
  emits `"hybrid"` and records `parent_template_id`.
