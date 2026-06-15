---
deck_id: huixin_consulting_strategy
kind: deck
category: brand
summary: 慧新咨询汇报、战略规划、智能制造诊断、数字化转型蓝图、董事会汇报模板.
keywords: [huixin, consulting, strategy, transformation, board-report]
primary_color: "#4295B6"
canvas_format: ppt169
replication_mode: standard
page_count: 8
placeholders:
  01_cover: ["{{TITLE}}", "{{SUBTITLE}}", "{{DATE}}", "{{AUTHOR}}"]
  02_executive_summary: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  03_diagnosis_issue_tree: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  04_strategy_matrix: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  05_capability_framework: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  06_roadmap: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  07_value_case: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  08_ending: ["{{TITLE}}", "{{SUBTITLE}}"]
---

# Huixin Consulting Strategy - Design Specification

## I. Template Overview

- Use cases: 慧新战略规划、智能制造咨询、数字化转型蓝图、项目启动会、现状诊断、TO-BE 规划、路线图、领导汇报、董事会汇报。
- Design tone: Structured, restrained, analytical, executive-level, management-consulting style.
- Theme mode: Light consulting report with white and blue-gray backgrounds.
- Visual identity: Thin blue rules, crisp section numbering, large conclusion line, MECE frameworks, high whitespace, and restrained green insight accents.

## II. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| Technology Blue | `#4295B6` | Titles, key conclusions, section numbers, chart primary color, process spine |
| Vitality Green | `#B0D776` | Insight tags, growth metrics, opportunity points, recommendations |
| Light Gray | `#D2D3D4` | Dividers, table strokes, weak information, structure lines |
| Wordmark Black | `#000000` | Official Huixin wordmark on light backgrounds |
| Deep Gray | `#4B5563` | Body text, footnotes, secondary labels |
| Light Blue Gray | `#F3F7FA` | Background panels, table fills, neutral analysis areas |
| Dark Blue Gray | `#0B2F3A` | Cover accent, executive titles, high-emphasis text |
| White | `#FFFFFF` | Page background and card surfaces |

## III. Typography

- Primary font: `"Microsoft YaHei"`.
- SVG font: `"Microsoft YaHei"`; all SVG text uses Microsoft YaHei / 微软雅黑 as the single design font.
- Titles are bold and concise. Body text should stay short, structured, and conclusion-oriented.
- Cover titles should fit the left safe region; prefer a short title under 14 Chinese characters and move qualifiers into `{{SUBTITLE}}`.

## IV. Signature Design Elements

- Executive header: small section label, page number, thin blue top rule, and compact official Huixin lockup.
- Consulting conclusion bar: every analysis page starts with a one-line key message beneath the title.
- Framework language: issue tree, four-quadrant matrix, pyramid capability model, phased roadmap, and value case table.
- Geometry: flat rectangles, fine rules, slanted-bar brand tabs derived from the official Huixin logo, no heavy shadow, no complex texture.
- Accent usage: green appears only for insight, opportunity, value uplift, or recommendation emphasis.

## V. Logo and Brand Mark

- Official lockup: embedded from the official Huixin logo assets; use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields.
- Light pages use the black wordmark. Dark cover/ending accents may use the white wordmark for contrast.
- Do not use the older two-diamond shorthand; preserve the horizontal logo lockup and slanted-bar proportions.

## VI. Page Roster

| SVG | Page Role | Description |
| --- | --- | --- |
| `01_cover.svg` | Cover | Executive consulting cover with conclusion card, method strip, pyramid, and issue-tree visual. |
| `02_executive_summary.svg` | Executive summary | One-line conclusion, three strategic findings, and quantified implication row. |
| `03_diagnosis_issue_tree.svg` | Diagnosis issue tree | MECE issue tree for current-state diagnosis and root-cause framing. |
| `04_strategy_matrix.svg` | Strategy matrix | Four-quadrant option assessment using impact and feasibility axes. |
| `05_capability_framework.svg` | Capability framework | Pyramid / layered capability model for target-state design. |
| `06_roadmap.svg` | Roadmap | Four-phase transformation roadmap with milestones and governance checkpoints. |
| `07_value_case.svg` | Value case | KPI value case with baseline, target, uplift, and management implications. |
| `08_ending.svg` | Ending | Minimal executive closing page with next-step callout and brand mark. |

## VII. Placeholder Overrides

The consulting template leads with `{{KEY_MESSAGE}}` on analysis pages because management-consulting pages usually communicate the answer first, then support it with structured evidence.

On framework and roadmap pages, `{{CONTENT_AREA}}` is a compact callout label, not a paragraph. Keep it under roughly 18 Chinese characters, for example `价值场景牵引` or `第一阶段主线`.

## VIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated digital transformation consulting blueprint reference | Optional reference only. Do not paste it as fixed slide content; use it to guide future project-specific visuals. Framework pages use editable SVG issue trees, matrices, pyramids, roadmaps, and value tables. |
