---
deck_id: huixin_management_report
kind: deck
summary: 慧新公司经营汇报、季度经营分析、部门工作汇报、项目进展汇报、高层管理会议模板.
canvas_format: ppt169
page_count: 10
primary_color: "#4295B6"
keywords: [huixin, management-report, business-review, kpi, executive-meeting]
---

# Huixin Management Report - Design Specification

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | huixin_management_report |
| **Display Name** | 慧新公司经营汇报模板 |
| **Use Cases** | 年度汇报、季度经营分析、部门工作汇报、项目进展汇报、高层管理会议 |
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
| **Content Body** | Tables, KPI cards, kanban lanes, project lists, timelines, organization and risk matrices |
| **Footer** | Source / owner / page number with restrained divider |

### Design DNA

1. Prioritize conclusion, number, responsible owner, deadline, and action item.
2. Use blue for management structure and primary data; green for achieved / growth / next action.
3. Keep pages white or light gray, with restrained panels and fine rules.
4. Avoid marketing slogans, heavy decoration, glowing effects, and complex gradients.
5. Express management closure through goal -> status -> issue -> countermeasure -> owner -> deadline.
6. Keep narrow-card placeholders short: `{{WORK_DONE}}`, `{{STATUS}}`, and `{{ACTION_1}}`-`{{ACTION_3}}` are label fields, not sentence fields. Put long explanations into the note fields or speaker notes.

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

## VIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated quarterly operations report dashboard reference | Optional reference only. Do not paste it as fixed slide content; use it to guide future project-specific dashboard visuals. KPI cards, project lists, risk matrices, timelines, and action tables remain editable SVG structures. |
