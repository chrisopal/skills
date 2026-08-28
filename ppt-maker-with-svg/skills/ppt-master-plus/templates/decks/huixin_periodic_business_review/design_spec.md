---
deck_id: huixin_periodic_business_review
kind: deck
category: scenario
summary: 慧新事业部月度与季度经营汇报模板，以工作梳理、工作成果、工作亮点、工作规划形成管理闭环并支持决策。
keywords: [月度汇报, 季度汇报, 工作复盘, 经营分析, 工作规划]
primary_color: "#0097BA"
canvas_format: ppt169
canvas_width: 1280
canvas_height: 720
canvas_viewbox: "0 0 1280 720"
source_canvas_width: 1280
source_canvas_height: 720
source_viewbox: "0 0 1280 720"
replication_mode: standard
native_structure_mode: structured
page_count: 25
---

# Huixin Monthly and Quarterly Business Review — Design Specification

## I. Template Overview

| Application context | Definition |
| --- | --- |
| Recurring presentation family | 事业部、业务单元、产品线、项目群的月度工作汇报、季度经营复盘和下一周期规划 |
| Intended audiences and outcomes | 总经理、经营班子、事业部负责人和跨部门协同方；形成事实回顾、目标对标、价值判断、计划决策与资源支持闭环 |
| Delivery and reading assumptions | 会议汇报与会后精读并重；首页和章节页适合讲述，成果、计划、风险页适合会后追踪 |
| Representative narrative/page roles | 封面、汇报逻辑、经营摘要、工作梳理、工作清单、进度状态、成果对标、成果分类、重点成果、工作亮点、公司价值、下一周期目标、重点任务、实施路线、风险与支持、结束页 |

- Core narrative: `工作梳理 → 工作成果 → 工作亮点 → 工作规划`.
- Monthly mode emphasizes the current-period work inventory, actual status,
  key result, and next-month task list.
- Quarterly mode expands target-vs-actual evidence, result classification,
  company-level value, phased roadmap, risks, and management decisions.
- The four narrative phases are stable. Prototype selection and page count are
  adapted to the real evidence density; do not create empty pages merely to
  reproduce the full roster.
- This Deck is light-only. Section dividers, highlight containers, charts, and
  working pages all use white/light-gray surfaces; do not introduce a dark
  theme or mix dark and light page systems in one periodic report.
- Chart pages are first-class evidence pages. Use trend, variance, completion,
  composition, small-multiple, and delivery-stage charts only when their
  source data uses a consistent and disclosed basis.
- Shared visual authority:
  [`../huixin_visual_system_0826.md`](../huixin_visual_system_0826.md).

## II. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| Technology Blue | `#0097BA` | Page titles, workstream structure, system/process spine, primary metrics |
| Vitality Green | `#A4D968` | Exceeded target, achieved result, highlight value, next action |
| Brand Chrome Green | `#83C410` | Official logo-derived double-bar and footer chrome only |
| Quality Gray | `#4B5563` | Body text, neutral conclusions, status explanation |
| Divider Gray | `#D9D9D9` | Tables, borders, separators, timeline rails |
| Light Surface | `#F7F8FA` | Secondary panels and neutral working areas |
| Alert Red | `#D8665B` | Under-target result or critical risk only |
| White | `#FFFFFF` | Main light canvas, cards, reverse text |

Do not color every status. Use blue for structure, green for achieved value,
gray for neutral/ongoing information, and red only where management attention
is required.

## III. Typography

- Primary font: `Microsoft YaHei, Arial, sans-serif`.
- Content-page title: 34-38px, bold; section title: 52-56px, bold.
- Section support text: 22px for section number, question, and supporting message.
- Body: 14-17px; compact table labels: 11-13px; metrics: 36-48px.
- Keep one concise conclusion under the page title. Long evidence belongs in
  tables, notes, or an appendix rather than in a large subtitle.

## IV. Signature Design Elements

- Light pages use the 0826 green/blue double vertical rule at top-left, a
  compact top-right Huixin lockup, left-aligned title, restrained top rule,
  and official blue-green footer ribbon.
- Covers and endings use the latest industrial mosaic with a quiet editable
  title area on the left.
- Section dividers stay in the same light system: white canvas, subtle
  light-blue/light-green geometry, black title, blue section number, gray
  support copy, and a four-phase progress rail.
- Management pages are table-first and conclusion-first. Every result or plan
  should expose an owner, deadline, status, evidence, or decision implication
  where the source supports it.
- Result classification uses three restrained states: exceeded/important
  completion, normal/ongoing, and under-target/needs correction.
- Planning pages connect goal → task → owner → milestone → risk/support. Avoid
  decorative roadmap arrows that do not encode execution responsibility.

### Native Structure

- Master key: `huixin-periodic-master`; picker name: `慧新月度季度汇报`.
- Layout key: `periodic-blank`; picker name: `慧新月度季度通用页`.
- The layout intentionally has zero native slots. Each prototype is a
  complete editable SVG example whose placeholder text and geometry are
  adapted by the downstream generator while preserving the selected layout
  identity.

## V. Page Roster

| SVG | Page role | Layout | Reusable structure and capacity |
| --- | --- | --- | --- |
| `01_cover.svg` | Cover | `periodic-blank` | Report title, monthly/quarterly badge, reporting period, organization, data cutoff and presenter |
| `02_report_logic.svg` | Narrative map | `periodic-blank` | Four-stage review logic with monthly/quarterly usage notes and one-line management objective |
| `03_executive_summary.svg` | Executive summary | `periodic-blank` | One conclusion, four KPI cards, four phase takeaways and management attention note |
| `04_section_work_review.svg` | Work-review divider | `periodic-blank` | Phase 01 opener with question, output and management perspective |
| `05_work_inventory.svg` | Work inventory | `periodic-blank` | Four workstreams with completed, ongoing, evidence and owner/status fields |
| `06_workstream_progress.svg` | Workstream progress | `periodic-blank` | Four-lane progress board with milestones, progress bars, dependencies and next checkpoint |
| `07_section_results.svg` | Results divider | `periodic-blank` | Phase 02 opener for target-vs-actual and result classification |
| `08_target_actual_dashboard.svg` | Target vs actual | `periodic-blank` | Four KPI target/actual/deviation/status cards plus management conclusion |
| `09_results_classification.svg` | Result classification | `periodic-blank` | Exceeded/important completion, normal/ongoing and under-target/corrective-action columns |
| `10_key_results.svg` | Key results | `periodic-blank` | Three evidence-backed result cards with output, metric, value and follow-up |
| `11_section_highlights.svg` | Highlights divider | `periodic-blank` | Phase 03 opener for key contribution and company-level value |
| `12_highlight_story.svg` | Highlight story | `periodic-blank` | One hero highlight, mechanism chain, evidence metrics and reusable capability |
| `13_company_value.svg` | Company contribution | `periodic-blank` | Business output → operating value → company contribution chain across four value dimensions |
| `14_section_plan.svg` | Planning divider | `periodic-blank` | Phase 04 opener for goals, tasks, roadmap and support decisions |
| `15_next_period_goals.svg` | Next-period goals | `periodic-blank` | Four goals with measure, baseline/target, owner and deadline |
| `16_priority_tasks.svg` | Priority tasks | `periodic-blank` | Six action cards covering task, deliverable, owner, milestone and dependency |
| `17_implementation_roadmap.svg` | Implementation roadmap | `periodic-blank` | Four-week or three-month timeline with stage output, checkpoint and decision gate |
| `18_risks_support.svg` | Risks and support | `periodic-blank` | Risk/impact/countermeasure/owner table plus cross-department support and management decisions |
| `19_ending.svg` | Ending | `periodic-blank` | Thanks, next review date, owner and contact on the 0826 industrial mosaic |
| `20_operating_trend_combo.svg` | Operating trend combo | `periodic-blank` | Editable amount bars plus quantity/rate line, four comparable periods, conclusion, drivers and actions |
| `21_target_variance_waterfall.svg` | Target variance waterfall | `periodic-blank` | Target-to-actual waterfall with positive/negative drivers, variance conclusion and corrective action |
| `22_workstream_completion_bars.svg` | Workstream completion | `periodic-blank` | Five horizontal stacked completion bars for completed, ongoing and risk/lag states |
| `23_value_contribution_donut.svg` | Value contribution mix | `periodic-blank` | Editable donut and four value cards for operating growth, delivery efficiency, platform reuse and organization capability |
| `24_quarterly_kpi_small_multiples.svg` | Quarterly KPI small multiples | `periodic-blank` | Four synchronized KPI trend panels with target lines, current value and common time window |
| `25_delivery_stage_distribution.svg` | Delivery stage distribution | `periodic-blank` | Five-stage project portfolio bars with total projects, contract amount and combination insights |

## VI. Assets

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/huixin_logo_light.png` | Official horizontal lockup for light surfaces | Use on cover and light working pages |
| `images/huixin_light_cover_mosaic.png` | Official 0826 industrial mosaic | Cover and ending background with left quiet region |
| `images/huixin_light_footer_ribbon.png` | Official blue-green footer ribbon | Standard light content footer |

## VII. Placeholder Overrides

| Placeholder | Meaning |
| --- | --- |
| `{{PERIOD_TYPE}}` | 月度汇报或季度汇报 |
| `{{REPORT_PERIOD}}` | 本次复盘周期 |
| `{{NEXT_PERIOD}}` | 下一规划周期 |
| `{{DATA_CUTOFF}}` | 数据统计截止日期与口径 |
| `{{OVERALL_CONCLUSION}}` | 一句话经营结论 |
| `{{WORKSTREAM_N}}` | 工作条线或业务域 |
| `{{TARGET_N}}` / `{{ACTUAL_N}}` | 目标值与实际值 |
| `{{RESULT_N}}` / `{{EVIDENCE_N}}` | 结果与证据 |
| `{{VALUE_N}}` | 对公司运作或经营的具体价值 |
| `{{GOAL_N}}` / `{{TASK_N}}` | 下一周期目标与重点任务 |
| `{{OWNER_N}}` / `{{DEADLINE_N}}` | 责任人与截止时间 |
| `{{RISK_N}}` / `{{SUPPORT_N}}` | 风险、跨部门支持或管理决策事项 |
| `{{PERIOD_N}}` / `{{AMOUNT_N}}` / `{{COUNT_N}}` | 经营趋势组合图的周期、金额和数量/转化率 |
| `{{WF_N_LABEL}}` / `{{WF_N}}` | 目标偏差瀑布图节点与驱动值 |
| `{{WORKSTREAM_N}}` / `{{RATE_N}}` | 工作条线完成度与状态比例 |
| `{{DONUT_VALUE_N}}` / `{{DONUT_NOTE_N}}` | 价值贡献环图的结构值与口径说明 |
| `{{KPI_SMALL_N_TITLE}}` / `{{KPI_SMALL_N_VALUE}}` | 季度KPI小多图指标名称与当前值 |
| `{{STAGE_N_LABEL}}` / `{{STAGE_N_VALUE}}` | 项目交付阶段名称与项目数量；`{{PROJECTS}}` / `{{AMOUNT}}` 表示项目总量和合同规模 |
