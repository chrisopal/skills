---
deck_id: huixin_consulting_strategy
kind: deck
category: brand
summary: 慧新咨询汇报、战略规划、智能制造诊断、数字化转型蓝图、治理决策与管理层汇报模板.
keywords: [huixin, consulting, strategy, transformation, board-report, diagnosis, governance]
primary_color: "#0097BA"
canvas_format: ppt169
canvas_width: 1280
canvas_height: 720
canvas_viewbox: "0 0 1280 720"
native_structure_mode: legacy-flat
replication_mode: standard
page_count: 26
placeholders:
  01_cover: ["{{TITLE}}", "{{SUBTITLE}}", "{{DATE}}", "{{AUTHOR}}"]
  02_agenda: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}"]
  02_executive_summary: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  03_diagnosis_issue_tree: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  04_strategy_matrix: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  05_capability_framework: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  06_roadmap: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  07_value_case: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  08_ending: ["{{TITLE}}", "{{SUBTITLE}}"]
  section_divider: ["{{SECTION_NO}}", "{{SECTION_TITLE}}", "{{SECTION_MESSAGE}}"]
  business_context: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{FACT_1}}", "{{QUESTION_1}}", "{{ANSWER_1}}", "{{CONTENT_AREA}}"]
  key_questions: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CORE_QUESTION}}", "{{QUESTION_1}}", "{{HYPOTHESIS_1}}"]
  diagnosis_summary: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{FINDING_1}}", "{{EVIDENCE_1}}", "{{IMPACT_1}}", "{{CONTENT_AREA}}"]
  maturity_assessment: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{SCORE_STRATEGY}}", "{{CURRENT_LEVEL}}", "{{TARGET_LEVEL}}"]
  capability_heatmap: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{CONTENT_AREA}}"]
  value_chain_analysis: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{SALES_BREAK}}", "{{VALUE_BREAKPOINT}}", "{{ROOT_CAUSE}}"]
  as_is_to_be_gap: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{ASIS_1}}", "{{GAP_1}}", "{{TOBE_1}}", "{{ACTION_1}}"]
  target_blueprint: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{BUSINESS_CAP_1}}", "{{CAPABILITY_1}}", "{{DATA_DOMAIN_1}}", "{{GOVERNANCE_THEME}}"]
  initiative_portfolio: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{INITIATIVE_QW}}", "{{INITIATIVE_SB}}", "{{PORTFOLIO_DECISION}}"]
  priority_matrix: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{DO_NOW}}", "{{STRATEGIC_BET}}", "{{PRIORITY_DECISION}}"]
  value_waterfall: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{BASELINE}}", "{{REVENUE_UP}}", "{{TARGET_VALUE}}", "{{ROI}}"]
  governance_model: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{BUSINESS_ROLE}}", "{{IT_ROLE}}", "{{VENDOR_ROLE}}", "{{CHANGE_ROLE}}"]
  raci_matrix: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{TASK_1}}", "{{TASK_2}}", "{{TASK_3}}"]
  risk_mitigation_matrix: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{RISK_1}}", "{{MITIGATION_1}}", "{{OWNER_1}}"]
  change_management: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{TRAINING_AUDIENCE}}", "{{COMM_MESSAGE}}", "{{CHANGE_SUCCESS_CRITERIA}}"]
  decision_ask: ["{{PAGE_TITLE}}", "{{KEY_MESSAGE}}", "{{DECISION_1}}", "{{RECOMMENDATION}}", "{{BUDGET}}", "{{NEXT_STEP}}"]
---

# Huixin Consulting Strategy - Design Specification

## I. Template Overview

- Use cases: 慧新战略规划、智能制造咨询、数字化转型蓝图、项目启动会、现状诊断、TO-BE 规划、实施治理、管理决策、路线图、领导汇报、董事会汇报。
- Design tone: Structured, restrained, analytical, executive-level, management-consulting style.
- Theme mode: Light consulting report with white and blue-gray backgrounds.
- Visual identity: Thin blue rules, crisp section numbering, large conclusion line, MECE frameworks, high whitespace, and restrained green insight accents.

## II. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| Technology Blue | `#0097BA` | Titles, key conclusions, section numbers, chart primary color, process spine |
| Vitality Green | `#83C410` | Insight tags, growth metrics, opportunity points, recommendations |
| Light Gray | `#D0CECE` | Dividers, table strokes, weak information, structure lines |
| Wordmark Black | `#000000` | Official Huixin wordmark on light backgrounds |
| Deep Gray | `#4B5563` | Body text, footnotes, secondary labels |
| Light Blue Gray | `#F5F6F7` | Background panels, table fills, neutral analysis areas |
| Dark Blue Gray | `#111111` | Cover accent, executive titles, high-emphasis text |
| White | `#FFFFFF` | Page background and card surfaces |

## III. Typography

- Primary font: `"MiSans, Microsoft YaHei, Arial, sans-serif"`.
- SVG font: `"MiSans, Microsoft YaHei, Arial, sans-serif"`; use MiSans first with Microsoft YaHei / Arial fallback.
- Titles are bold and concise. Body text should stay short, structured, and conclusion-oriented.
- Cover titles should fit the left safe region; prefer a short title under 14 Chinese characters and move qualifiers into `{{SUBTITLE}}`.

### Latest Light Template Baseline

This deck follows the official `慧新全智PPT模板_浅色版本.pptx` baseline (source SHA-256: `0b700b898693c99b6ef50a4a00db5ad3c81ba9bb02fe46bec712d545841a1906`). Use the latest Huixin Quanzhi lockup, `#0097BA` blue, `#83C410` green, `#D0CECE` gray, MiSans, and white / very-light-gray consulting surfaces. Covers use the industrial mosaic; chapter pages may use the teal chapter background; standard evidence pages use the lower-left logo and blue-green footer ribbon. A compact top-right logo is allowed on dense consulting frameworks when it preserves evidence space.

## IV. Signature Design Elements

- Executive header: small section label, page number, thin blue top rule, and compact official Huixin lockup.
- Consulting conclusion bar: every analysis page starts with a one-line key message beneath the title.
- Framework language: agenda, section divider, issue tree, diagnosis summary, maturity assessment, heatmap, value chain, AS-IS / TO-BE gap, target blueprint, initiative portfolio, priority matrix, value waterfall, governance model, RACI, risk mitigation matrix, change management, decision ask, pyramid capability model, phased roadmap, and value case table.
- Geometry: flat rectangles, fine rules, slanted-bar brand tabs derived from the official Huixin logo, no heavy shadow, no complex texture.
- Accent usage: green appears only for insight, opportunity, value uplift, or recommendation emphasis.

## V. Logo and Brand Mark

- Official lockup: embedded from the official Huixin logo assets; use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields.
- Light pages use the black wordmark. Dark cover/ending accents may use the white wordmark for contrast.
- Do not use the older two-diamond shorthand; preserve the horizontal logo lockup and slanted-bar proportions.

## VI. Template Adaptation Rules

1. Prefer the reusable SVG page type / master when it matches the consulting question, evidence structure, and executive decision path.
2. If the real analysis needs a different framework, more dimensions, more evidence rows, additional initiatives, or a richer target blueprint than the base page supports, derive a custom page instead of weakening the argument.
3. Custom pages must preserve Huixin's palette, white / light-gray or deep blue-gray background style, top-right logo discipline, slanted-bar brand geometry, and the consulting narrative of question -> conclusion -> evidence -> implication -> recommendation -> decision.
4. Do not reduce root-cause logic, maturity evidence, value assumptions, governance relationships, or decision asks only to fit a predefined template layout.

## VII. Page Roster

| SVG | Page Role | Description |
| --- | --- | --- |
| `01_cover.svg` | Cover | Executive consulting cover with conclusion card, method strip, pyramid, and issue-tree visual. |
| `02_agenda.svg` | Agenda | Formal consulting report structure with chapter spine and five-part delivery logic. |
| `02_executive_summary.svg` | Executive summary | One-line conclusion, three strategic findings, and quantified implication row. |
| `03_diagnosis_issue_tree.svg` | Diagnosis issue tree | MECE issue tree for current-state diagnosis and root-cause framing. |
| `04_strategy_matrix.svg` | Strategy matrix | Four-quadrant option assessment using impact and feasibility axes. |
| `05_capability_framework.svg` | Capability framework | Pyramid / layered capability model for target-state design. |
| `06_roadmap.svg` | Roadmap | Four-phase transformation roadmap with milestones and governance checkpoints. |
| `07_value_case.svg` | Value case | KPI value case with baseline, target, uplift, and management implications. |
| `08_ending.svg` | Ending | Minimal executive closing page with next-step callout and brand mark. |
| `section_divider.svg` | Section divider | Dark executive chapter opener with section question, output, and decision perspective. |
| `business_context.svg` | Business context | Background facts, management questions, and what the report answers. |
| `key_questions.svg` | Key questions | Core question tree with analysis hypotheses and validation approach. |
| `diagnosis_summary.svg` | Diagnosis summary | Three-to-five diagnosis findings with evidence, impact, and management implications. |
| `maturity_assessment.svg` | Maturity assessment | Multi-dimension digital / intelligent manufacturing maturity scoring page. |
| `capability_heatmap.svg` | Capability heatmap | Business domain by capability matrix for maturity or issue severity. |
| `value_chain_analysis.svg` | Value chain analysis | Sales-to-service value chain with breakpoints, root causes, and improvement themes. |
| `as_is_to_be_gap.svg` | AS-IS / TO-BE gap | Current state, target state, gap, and key initiatives in one comparison table. |
| `target_blueprint.svg` | Target blueprint | Business, capability, data, and governance blueprint for consulting target-state design. |
| `initiative_portfolio.svg` | Initiative portfolio | Initiative portfolio organized by strategic value, complexity, and management principles. |
| `priority_matrix.svg` | Priority matrix | Dedicated quick wins / strategic bets / monitor / defer prioritization page. |
| `value_waterfall.svg` | Value waterfall | Consulting-style value estimation waterfall for revenue, cost, efficiency, and risk. |
| `governance_model.svg` | Governance model | Steering committee, PMO, business, IT, vendor, and change roles. |
| `raci_matrix.svg` | RACI matrix | Responsibility matrix for consulting delivery and project kickoff alignment. |
| `risk_mitigation_matrix.svg` | Risk mitigation matrix | Risk item, impact, probability, level, mitigation, and owner tracker. |
| `change_management.svg` | Change management | Training, communication, policy, performance, and organizational capability plan. |
| `decision_ask.svg` | Management ask | Management decision page covering decisions, recommendation, resource ask, and next step. |

## VIII. Placeholder Overrides

The consulting template leads with `{{KEY_MESSAGE}}` on analysis pages because management-consulting pages usually communicate the answer first, then support it with structured evidence.

On framework and roadmap pages, `{{CONTENT_AREA}}` is a compact callout label, not a paragraph. Keep it under roughly 18 Chinese characters, for example `价值场景牵引` or `第一阶段主线`.

For the expanded consulting pages, prioritize one-page-answer discipline: every page should express the management conclusion in `{{KEY_MESSAGE}}`, then support it with a structured framework. Use `business_context`, `key_questions`, and `section_divider` near the start of formal reports; use `decision_ask`, `governance_model`, `raci_matrix`, and `risk_mitigation_matrix` near the end for leadership decision packs and project kickoff materials.

## IX. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated digital transformation consulting blueprint reference | Optional reference only. Do not paste it as fixed slide content; use it to guide future project-specific visuals. Framework pages use editable SVG issue trees, matrices, pyramids, roadmaps, and value tables. |
| `images/huixin_logo_light.png` | Official Huixin logo for light pages | Use in white / light consulting pages. Preserve the official horizontal lockup. |
| `images/huixin_logo_dark.png` | Official Huixin logo for dark pages | Use in dark section divider or cover pages. Preserve the official horizontal lockup. |
| `images/huixin_light_cover_mosaic.png` | Official light-template industrial mosaic | Use for consulting covers and final decision pages. |
| `images/huixin_light_content_bg.png` | Official subtle light geometric background | Use on agenda and sparse executive pages. |
| `images/huixin_light_chapter_bg.png` | Official teal chapter background | Use for section dividers. |
| `images/huixin_light_footer_ribbon.png` | Official blue-green footer ribbon | Use on standard evidence pages with the lower-left logo. |
