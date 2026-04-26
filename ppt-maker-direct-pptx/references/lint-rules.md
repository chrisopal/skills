# Lint Rule Catalog

Every fail/warn produced by the v2 lint pipeline. `auto_fixable` rules are
patched by `scripts/auto_fix_lint.py`; the rest require manual edits.

## Schema (`lint_schema.py`)

| Rule                              | Severity | Auto-fix | Triggered when                                           |
|-----------------------------------|----------|----------|----------------------------------------------------------|
| `outline.schema:<path>`           | fail     | no       | outline.json fails JSON-Schema validation                |
| `slide_prompts.schema:<path>`     | fail     | no       | slide_prompts.json fails validation                      |
| `slide_specs.schema:<path>`       | fail     | no       | slide_specs.json fails validation                        |
| `<file>.duplicate_page_no`        | fail     | no       | the same page_no appears more than once in an artifact   |
| `outline.page_count_mismatch`     | fail     | no       | outline slide count != requirement.page_count            |
| `slide_prompts.unknown_pattern_id`| fail     | no       | a slide references a pattern_id not in the registry      |
| `slide_specs.invalid_image_status`| fail     | no       | image_placeholder.status is outside the 5-state enum     |

## Layout geometry (`lint_geometry.py`)

| Rule                          | Severity | Auto-fix | Triggered when                                                |
|-------------------------------|----------|----------|---------------------------------------------------------------|
| `region_outside_canvas`       | fail     | yes      | layout_regions.{title,content,images} extends past 13.333×7.5 |
| `regions_overlap`             | fail     | yes      | title vs content vs images regions intersect                  |
| `block_outside_canvas`        | fail     | yes      | a visible_content.blocks placement exceeds canvas             |
| `card_min_height`             | warn     | no       | a block carries bullets but its height is < 1.0 inch          |
| `font_size_out_of_range`      | fail     | yes      | block.font_size outside master_style.typography range         |

Auto-fix details:
- `region_outside_canvas` / `block_outside_canvas` clamp `w`/`h` into the canvas.
- `regions_overlap` shifts content.y past title.y + title.h.
- `font_size_out_of_range` clamps to the typography min..max.

## Style consistency (`lint_style.py`)

| Rule                          | Severity | Auto-fix | Triggered when                                                |
|-------------------------------|----------|----------|---------------------------------------------------------------|
| `palette_compliance`          | fail     | yes      | a slide uses a hex color outside master_style.color_strategy  |
| `title_font_scale_unified`    | warn     | no       | locked slides disagree on title font size                     |
| `forbidden_element_present`   | fail     | no       | master_style.forbidden_elements appear in slide_specs JSON    |

Auto-fix detail: `palette_compliance` snaps each off-palette hex to the
nearest palette color by RGB distance.

## Content quality (`lint_content.py`)

| Rule                          | Severity | Auto-fix | Triggered when                                                |
|-------------------------------|----------|----------|---------------------------------------------------------------|
| `missing_core_message`        | fail     | no       | a slide's `core_message` is empty                             |
| `duplicate_core_message`      | warn     | no       | two slides have core_message similarity > 0.8                 |
| `audience_fit_low`            | warn     | no       | LLM judge scores a slide < 0.6 against the stated audience    |
| `audience_judge_unavailable`  | warn     | no       | LLM returned a non-JSON or non-numeric response               |

The audience-fit check is opt-in: it only runs when `--skip-content-judge`
is absent and an audience description is supplied.

## Override semantics

- `fail` rules block the gate. The user can run `--override-lint` (only on
  rules without `auto_fixable=true`) to advance with explicit
  acknowledgement; the override is recorded in `lint_report.overrides`.
- `warn` rules surface in the dashboard but do not block.
- `pass` rules are recorded for traceability and never block.

## Severity → state machine

A `fail` result tagged with a `page_no` automatically flips that page's
`intent_status` (or `outline_status` at gate 4) to `needs_rework` when
`run_all_lints.py --update-state` is set, so the gate cannot advance until
the user reworks the page.
