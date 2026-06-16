---
deck_id: huixin_management_report
kind: deck
summary: 慧新公司经营汇报、季度经营分析、部门工作汇报、项目进展汇报、高层管理会议模板；包含财务分析、事业部/产品线业绩、销售月报、经营复盘、销售漏斗、商机管理、人员变化、Excel数据概览、销售预测、人员月度组合图、人员类型饼图和决策事项页.
canvas_format: ppt169
page_count: 25
primary_color: "#4295B6"
keywords: [huixin, management-report, business-review, kpi, executive-meeting, finance, sales, opportunity, staffing, excel, forecast, chart]
---

# Huixin Management Report - Design Specification

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | huixin_management_report |
| **Display Name** | 慧新公司经营汇报模板 |
| **Use Cases** | 年度汇报、季度经营分析、部门工作汇报、项目进展汇报、高层管理会议、销售月报、财务分析、商机复盘、组织人力汇报、Excel数据汇总、销售预测、人员统计图表、转型推进汇报 |
| **Design Tone** | Steady, clear, formal, trustworthy, management-closed-loop oriented |
| **Theme Mode** | White / light gray business reporting theme based on Huixin logo colors |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 x 720 px |
| **viewBox** | `0 0 1280 720` |
| **Safe Margins** | 64px left/right, 44px top, 40px bottom |
| **Primary Content Area** | x: 72-1208, y: 132-642 |

## III. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| **Logo Blue** | `#4295B6` | Cover, title bars, key data, chart main color, KPI progress |
| **Logo Green** | `#B0D776` | Growth, achieved status, highlights, next actions |
| **Logo Gray** | `#D2D3D4` | Tables, separators, organizational lines, process support |
| **Deep Blue Gray** | `#0B2F3A` | High-emphasis titles, footer bars, executive conclusion blocks |
| **Text Gray** | `#4B5563` | Body text, notes, secondary labels |
| **Light Blue Gray** | `#F3F7FA` | Page panels, table headers, neutral backgrounds |
| **White** | `#FFFFFF` | Page background and report cards |
| **Wordmark Black** | `#000000` | Official Huixin wordmark on light backgrounds |

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| **H1** | Cover title | 54px | Bold |
| **H2** | Page title | 34-38px | Bold |
| **H3** | Section / card title | 18-24px | Bold |
| **Body** | Management explanation | 14-17px | Regular |
| **Caption** | Source / metadata | 11-13px | Regular |
| **Metric** | KPI and business numbers | 38-52px | Bold |

**Primary Font**: `"Microsoft YaHei"`

**SVG Font**: `"Microsoft YaHei"` — all SVG text uses Microsoft YaHei / 微软雅黑 as the single design font.

## V. Logo and Brand Mark

| Asset | Description |
| --- | --- |
| **Official Huixin Lockup** | Embedded from the official Huixin logo assets: use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields. |

Usage rules:

1. Use the black wordmark on light pages and the white wordmark only on deep blue-gray cover areas.
2. Preserve the horizontal lockup, slanted-bar proportions, and blue underline.
3. Keep the mark compact in the top-right on working pages.

## VI. Page Structure

### Common Layout

| Area | Description |
| --- | --- |
| **Brand Header** | Thin blue top rule, optional green achievement segment, section label, top-right Huixin lockup |
| **Title Zone** | Left-aligned title with a concise management conclusion |
| **Content Body** | KPI cards, charts, dense tables, kanban lanes, project lists, timelines, organization maps, risk matrices, decision tables |
| **Footer** | Source / owner / page number with restrained divider |

### Design DNA

1. Prioritize conclusion, number, responsible owner, deadline, and action item.
2. Use blue for management structure and primary data; green for achieved / growth / next action.
3. Keep pages white or light gray, with restrained panels and fine rules.
4. Avoid marketing slogans, heavy decoration, glowing effects, and complex gradients.
5. Express management closure through goal -> status -> issue -> countermeasure -> owner -> deadline.
6. Keep narrow-card placeholders short: `{{WORK_DONE}}`, `{{STATUS}}`, and `{{ACTION_1}}`-`{{ACTION_3}}` are label fields, not sentence fields. Put long explanations into the note fields or speaker notes.
7. For finance, sales, opportunity, staffing, and decision pages, prefer table-first reporting: place numbers, stage, owner, deadline, and latest progress in visible cells.
8. Long Chinese text must be shortened or split across multiple placeholder lines before rendering; do not let table text cross cell boundaries.
9. Use charts only when they support a management question: budget variance, funnel conversion, business-unit comparison, product-line mix, headcount change, or roadmap progress.
10. Excel-driven report pages must keep the source sheet, calculation basis, visible table, and management conclusion traceable on the slide.
11. For sales forecast and staffing statistics, combine dense tables with one readable chart; do not replace source numbers with chart-only visuals.
12. When using workbook data, normalize sheet names and metric names before rendering; use `{{SHEET_*}}`, `{{MONTH_*}}`, `{{TYPE_*}}`, and `{{STAGE_*}}` placeholders for reusable templates.

## VII. Page Types

### 1. Cover Page (`01_cover.svg`)
- Formal report cover for annual, quarterly, departmental, and project management meetings.

### 2. Executive Overview (`02_executive_overview.svg`)
- One-page summary of goals, business results, key work, risks, and next actions.
- `{{PAGE_TITLE}}` must be filled with a real page title; do not leave generic fallback text such as "Page Title".
- Top-row metric cards use short values only: `{{WORK_DONE}}` should be around 4-8 Chinese characters; `{{STATUS}}` should be around 3-6 Chinese characters; action chips should be concise labels.
- `{{TARGET_RATE}}` is the numeric percentage value only, for example `107`; the percent sign is drawn as a separate unit to avoid PPT text-frame wrapping.

### 3. KPI Dashboard (`03_kpi_dashboard.svg`)
- KPI cards, progress bars, and target-vs-actual status for management review.

### 4. Work Progress Kanban (`04_progress_kanban.svg`)
- Workstream progress board organized by status and accountability.

### 5. Issues and Countermeasures (`05_issue_action.svg`)
- Problem, root cause, countermeasure, owner, and deadline table.

### 6. Key Project List (`06_project_portfolio.svg`)
- Project portfolio table with stage, milestone, owner, risk, and status.

### 7. Operating Timeline (`07_operating_timeline.svg`)
- Quarterly / monthly milestone timeline for business execution rhythm.

### 8. Organization Structure (`08_org_structure.svg`)
- Organization, responsibility, and support structure for management reporting.

### 9. Monthly Plan Table (`09_monthly_plan.svg`)
- Month-level plan, deliverables, accountable owners, and check mechanism.

### 10. Risk Matrix (`10_risk_matrix.svg`)
- Risk level matrix with mitigation actions and management asks.

### 11. Financial Analysis (`11_financial_analysis.svg`)
- Finance page with revenue, gross margin, expense ratio, net profit, profit waterfall, and budget variance table.
- Use for monthly/quarterly finance review and management decision meetings.

### 12. Business Unit Performance (`12_business_unit_performance.svg`)
- Business-unit performance comparison with revenue, contract, gross margin, delivery status, risks, and management actions.
- Suitable for各事业部经营业绩复盘.

### 13. Product Line Performance (`13_product_line_performance.svg`)
- Product-line operating performance with product mix, key indicators, margin contribution, and follow-up actions.
- Suitable for计量装备、智能工厂、智慧矿山、智慧城市、平台产品等产品线.

### 14. Sales Monthly Report (`14_sales_monthly_report.svg`)
- Sales monthly report with opportunity source table, stage distribution, signed project list, and delivery-follow-up table.
- Dense-table layout inspired by internal sales reporting, but kept in Huixin brand style.

### 15. Operating Review (`15_operating_review.svg`)
- Management review page organized as target -> result -> gap -> action.
- Use for经营复盘 and monthly closed-loop management.

### 16. Sales Funnel (`16_sales_funnel.svg`)
- Sales funnel conversion page with lead, qualified, quote, and contract stages plus stage actions.
- Use for sales业务管理、漏斗健康、关键卡点 and commit forecast.

### 17. Opportunity Management (`17_opportunity_management.svg`)
- Detailed opportunity progress table with customer, opportunity id, business line, stage, amount, scene, and latest progress.
- Use when the user provides CRM data or asks for重点售前商机进度.

### 18. Staffing Changes (`18_staffing_changes.svg`)
- People and organization change page with headcount cards, team distribution chart, and staffing action table.
- Use for人员变化、关键岗位缺口、招聘补位 and组织能力建设.

### 19. Transformation Report (`19_transformation_report.svg`)
- Transformation progress page with phased roadmap, business/data/organization metrics, and next-stage focus.
- Use for数字化转型、经营转型、组织变革 and management roadmap review.

### 20. Decision Items (`20_decision_items.svg`)
- Management decision page with decision count, resource ask, recommendation, risks, and decision-status table.
- Use for高层会议决策事项、资源申请、预算审批 and会后闭环.

### 21. Excel Data Overview (`21_excel_data_overview.svg`)
- Workbook intake and data-quality page showing source sheets, row counts, calculation chain, summary metrics, and validation status.
- Use when the user provides Excel / CSV / CRM exports and wants traceable management reporting from raw data.

### 22. Sales Forecast Table (`22_sales_forecast_table.svg`)
- Sales forecast page with yearly target, forecast total, gap, monthly target/actual/forecast table, and trend chart.
- Use for销售预测、回款预测、年度目标达成预测 and月度经营预测.

### 23. Opportunity Pipeline Stats (`23_opportunity_pipeline_stats.svg`)
- Opportunity pipeline statistics page with stage amount bars, weighted pipeline KPIs, stage table, and key opportunity list.
- Use for商机管理、销售漏斗健康、重点客户跟进 and commit forecast.

### 24. Staffing Monthly Combo (`24_staffing_monthly_combo.svg`)
- Monthly staffing page with joiner/leaver bars, headcount line, staffing summary cards, and management focus.
- Use for各月份人员变化、净增趋势、关键岗位补位 and组织容量管理.

### 25. Staff Type Pie (`25_staff_type_pie.svg`)
- Personnel type distribution page with editable pie chart, type table, ratios, and staffing action notes.
- Use for人员类型占比、团队结构分析、研发/交付/销售/产品/职能结构汇报.

## VIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated quarterly operations report dashboard reference | Optional reference only. Do not paste it as fixed slide content; use it to guide future project-specific dashboard visuals. KPI cards, project lists, risk matrices, timelines, and action tables remain editable SVG structures. |
| `images/huixin_logo_light.png` | Official Huixin light-background logo | Use on white and light gray pages. |
| `images/huixin_logo_dark.png` | Official Huixin dark-background logo | Use only on deep blue-gray or black backgrounds. |
