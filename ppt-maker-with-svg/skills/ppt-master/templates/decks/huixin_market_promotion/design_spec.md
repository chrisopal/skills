---
deck_id: huixin_market_promotion
kind: deck
summary: 慧新品牌市场宣传、产品推广、渠道招商、客户活动、三坐标推广材料.
canvas_format: ppt169
page_count: 8
primary_color: "#4295B6"
---

# Huixin Market Promotion - Design Specification

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | huixin_market_promotion |
| **Display Name** | 慧新市场宣传模板 |
| **Use Cases** | 慧新品牌市场宣传、产品推广、渠道招商、客户活动、三坐标推广材料 |
| **Design Tone** | High-impact, brand-forward, technology-led, sales-conversion oriented |
| **Theme Mode** | Marketing and brand communication theme based on Huixin logo colors |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Safe Margins** | 64px left/right, 44px top, 40px bottom |
| **Primary Content Area** | x: 72-1208, y: 138-640 |

## III. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| **Technology Blue** | `#4295B6` | Primary brand visual, headers, core diagrams, campaign emphasis |
| **Vitality Green** | `#B0D776` | Value propositions, keywords, tags, growth metrics, CTA highlights |
| **Brand Gray** | `#D2D3D4` | Background layers, auxiliary shapes, card strokes, dividers |
| **Wordmark Black** | `#000000` | Official Huixin wordmark on light backgrounds |
| **Deep Blue Gray** | `#0B2F3A` | Premium dark backgrounds, cover, key visual pages, high-emphasis text |
| **White** | `#FFFFFF` | Card surfaces, negative space, reverse text |

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| **H1** | Cover title | 66px | Bold |
| **H2** | Page title | 36-46px | Bold |
| **H3** | Section / card title | 24px | Bold |
| **Body** | Primary body text | 17px | Regular |
| **Caption** | Footnote / metadata | 12px | Regular |
| **Display Number** | Impact numbers | 58px | Bold |

**Primary Font**: `"Microsoft YaHei"`

**SVG Font**: `"Microsoft YaHei"` — all SVG text uses Microsoft YaHei / 微软雅黑 as the single design font.

## V. Logo and Brand Mark

| Asset | Description |
| --- | --- |
| **Official Huixin Lockup** | Embedded from the official Huixin logo assets: use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields. |

Usage rules:

1. Keep the full lockup at the top-right on light pages.
2. Use the black wordmark on light backgrounds and the white wordmark only on dark blue-gray backgrounds.
3. Preserve the horizontal logo lockup, slanted-bar proportions, and blue underline.
4. Do not replace the official lockup with the older two-diamond shorthand.

## VI. Page Structure

### Common Layout

| Area | Description |
| --- | --- |
| **Brand Header** | Top-left section label, top-right Huixin mark, page number |
| **Title Zone** | Large left-aligned page title with concise key message |
| **Content Body** | Intentional business layouts: promotion axis, value cards, scenario proof, action plan |
| **Footer** | Thin divider with source / template attribution |

### Design DNA

1. Use the logo's slanted-bar geometry as the core brand language: slanted blocks, focus bands, tags, and motion lines.
2. Use `#4295B6` as the main visual identity and `#B0D776` as the growth / CTA signal.
3. Use `#0B2F3A` for cover, key visual pages, and closing CTA to create stronger brand memory.
4. Keep sales-facing pages clean, short, and high-contrast; prioritize slogans, keywords, metrics, and conversion messages.
5. Prefer explicit marketing logic: brand claim → pain → solution → value → proof → action.

## VII. Page Types

### 1. Cover Page (`01_cover.svg`)

- High-impact title page for campaign or product promotion.
- Includes campaign tag, title, subtitle, date, and brand mark.

### 2. Market Opportunity (`02_market_opportunity.svg`)

- Frames target market pain, growth trigger, and buying reason.
- Suitable for opening the argument before product details.

### 3. Value Proposition (`03_value_proposition.svg`)

- Three value pillars with supporting proof points.
- Suitable for business value, customer value, and technical value.

### 4. Three-Axis Promotion (`04_three_axis_promotion.svg`)

- Dedicated page for 三坐标 / three-coordinate promotion logic.
- Uses an x/y/z axis metaphor: capability, scenario, conversion.

### 5. Scenario Proof (`05_scenario_proof.svg`)

- Shows customer scenarios and proof points.
- Suitable for cases, user stories, and adoption evidence.

### 6. Campaign Plan (`06_campaign_plan.svg`)

- Converts strategy into a staged promotion plan.
- Suitable for campaign channels, rhythm, responsibilities, and KPIs.

### 7. Content Page (`07_content.svg`)

- General-purpose content page with open body region.
- Suitable for tables, diagrams, product feature detail, or customer quotes.

### 8. Ending Page (`08_ending.svg`)

- Closing call-to-action page.
- Suitable for contact, next step, QR / link placeholder, and final slogan.

## VIII. SVG Page Roster

| File | Role | Description |
|------|------|-------------|
| `01_cover.svg` | cover | Campaign title, subtitle, date, and brand promise |
| `02_market_opportunity.svg` | opportunity | Market pain / trigger / buying reason layout |
| `03_value_proposition.svg` | value | Three pillar value proposition page |
| `04_three_axis_promotion.svg` | three_axis | Dedicated 三坐标 promotion framework page |
| `05_scenario_proof.svg` | proof | Scenario proof and evidence page |
| `06_campaign_plan.svg` | plan | Channel / rhythm / KPI action plan page |
| `07_content.svg` | content | Flexible marketing content page |
| `08_ending.svg` | ending | Closing CTA and contact page |

## IX. Layout Modes

| Mode | Recommendation |
| --- | --- |
| **Campaign Story** | Use cover → opportunity → value → proof → action order |
| **Three-Axis Promotion** | Use `04_three_axis_promotion.svg` for 三坐标 themes and keep the three axes visually explicit |
| **Scenario Selling** | Use scenario cards and proof metrics; do not overload with paragraphs |
| **Executive Summary** | Use value proposition and campaign plan pages with fewer, larger messages |

## X. Spacing Specification

| Property | Value |
| --- | --- |
| **Base Unit** | 8px |
| **Module Gap** | 24px |
| **Card Gap** | 20px |
| **Title to Body** | 38px |
| **Footer Offset** | 32px from bottom |

## XI. SVG Technical Constraints

1. `viewBox` must stay `0 0 1280 720`.
2. Use plain hex colors with `fill-opacity` / `stroke-opacity`; do not use `rgba()`.
3. Do not use `<style>`, `class`, `foreignObject`, `textPath`, animation tags, or external scripts.
4. Keep all placeholder text in `{{PLACEHOLDER}}` form.
5. Use the official embedded Huixin logo asset; keep titles, metrics, and CTA editable in SVG.

## XII. Placeholder Specification

| Placeholder | Description |
| --- | --- |
| `{{TITLE}}` | Cover or page main title |
| `{{SUBTITLE}}` | Cover subtitle or page key message |
| `{{CAMPAIGN_TAG}}` | Campaign category label |
| `{{DATE}}` | Date or campaign period |
| `{{AUTHOR}}` | Presenter / team |
| `{{PAGE_TITLE}}` | Page title |
| `{{KEY_MESSAGE}}` | One-line page message |
| `{{SECTION_NAME}}` | Section label |
| `{{PAGE_NUM}}` | Page number |
| `{{SOURCE}}` | Source or attribution |
| `{{AXIS_X}}` | Three-axis promotion x-axis |
| `{{AXIS_Y}}` | Three-axis promotion y-axis |
| `{{AXIS_Z}}` | Three-axis promotion z-axis |
| `{{SCENARIO_1_TITLE}}` / `{{SCENARIO_2_TITLE}}` / `{{SCENARIO_3_TITLE}}` | Scenario card titles |
| `{{SCENARIO_1_DESC}}` / `{{SCENARIO_2_DESC}}` / `{{SCENARIO_3_DESC}}` | Scenario card descriptions |
| `{{METRIC_1}}` / `{{METRIC_2}}` / `{{METRIC_3}}` | Large proof metrics for scenario cards |
| `{{SCENARIO_1_PROOF}}` / `{{SCENARIO_2_PROOF}}` / `{{SCENARIO_3_PROOF}}` | Proof-point captions under scenario metrics |
| `{{CONTENT_AREA}}` | Flexible content placeholder |
| `{{CTA}}` | Closing call to action |
| `{{CONTACT}}` | Contact information |

## XIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated MES marketing visual reference | Optional reference only. Do not paste it as fixed slide content; use it to guide custom project imagery when a real MES product screenshot or campaign visual is available. |

The default template pages must remain editable SVG. Keep business messages, metrics, CTA, logo geometry, MES dashboards, and page structure as SVG text and shapes.
