---
deck_id: huixin_product_solution
kind: deck
summary: 慧新产品解决方案、软件平台、AI平台、智能制造、数字化系统能力展示.
canvas_format: ppt169
page_count: 10
primary_color: "#4295B6"
---

# Huixin Product Solution - Design Specification

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | huixin_product_solution |
| **Display Name** | 慧新产品解决方案模板 |
| **Use Cases** | 软件产品、数字化平台、智能制造解决方案、AI平台、行业应用方案展示 |
| **Design Tone** | Clean, modular, enterprise software, platform-oriented |
| **Theme Mode** | Product solution theme based on Huixin logo colors |

## II. Canvas Specification

| Property | Value |
| --- | --- |
| **Format** | Standard 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Safe Margins** | 64px left/right, 44px top, 40px bottom |
| **Primary Content Area** | x: 72-1208, y: 132-642 |

## III. Color Scheme

| Role | Color Value | Usage |
| --- | --- | --- |
| **Technology Blue** | `#4295B6` | Platform architecture, system modules, navigation, process lines |
| **Vitality Green** | `#B0D776` | AI capabilities, value points, highlights, product advantages, metrics |
| **Brand Gray** | `#D2D3D4` | Module borders, structural partitions, connection lines, auxiliary notes |
| **Wordmark Black** | `#000000` | Official Huixin wordmark on light backgrounds |
| **Deep Blue Gray** | `#0B2F3A` | Titles, body text, premium background blocks, technical base layer |
| **White** | `#FFFFFF` | Page background, card surfaces, reverse text |

## IV. Typography System

| Level | Usage | Size | Weight |
| --- | --- | --- | --- |
| **H1** | Cover title | 56px | Bold |
| **H2** | Page title | 34-40px | Bold |
| **H3** | Module / card title | 20-24px | Bold |
| **Body** | Product explanation | 15-17px | Regular |
| **Caption** | Note / footer | 11-13px | Regular |
| **Metric** | Business value number | 42-52px | Bold |

**Primary Font**: `"Microsoft YaHei"`

**SVG Font**: `"Microsoft YaHei"` — all SVG text uses Microsoft YaHei / 微软雅黑 as the single design font.

## V. Logo and Brand Mark

| Asset | Description |
| --- | --- |
| **Official Huixin Lockup** | Embedded from the official Huixin logo assets: use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields. |

Usage rules:

1. Use the slanted-bar logo geometry as the core product visual language.
2. Keep the mark in the top-right on light technical pages.
3. Use the black wordmark on light backgrounds and the white wordmark only on deep blue-gray backgrounds.
4. Preserve the horizontal logo lockup, slanted-bar proportions, and blue underline.
5. Do not add cyberpunk glow, unnecessary 3D, or complex gradients.

## VI. Page Structure

### Common Layout

| Area | Description |
| --- | --- |
| **Brand Header** | Thin blue top rule, optional green segment, section label, top-right Huixin mark |
| **Title Zone** | Left-aligned title and short technical key message |
| **Content Body** | Modular product diagrams: layers, modules, flows, scenarios, deployment topology |
| **Footer** | Source and page number with restrained divider |

### Design DNA

1. Communicate enterprise software maturity through clean modules and clear hierarchy.
2. Use blue for system structure and green for AI / value / innovation signals.
3. Favor architecture clarity over decorative intensity.
4. Keep information density moderate: enough for product selling, not overloaded consulting pages.
5. Express platformization through layers, reusable components, flows, and scalable deployment options.

### Architecture Density Contract

Product architecture pages must feel like mature enterprise software architecture, not a simple three-row stack. When a page uses `04_product_architecture.svg` or an architecture/chart layout:

1. Show at least five visible architecture strata: user/application, business process, platform services, data/AI, and integration/foundation.
2. Fill the body with 12-18 editable module nodes distributed across the strata; avoid empty bands, oversized labels, or only 3-4 broad rectangles.
3. Include a right-side output or value column with 3-4 short deliverables such as dashboards, evidence packages, risk alerts, or APIs.
4. Draw at least two cross-layer arrows or data-flow cues so the page reads as a system, not a static list.
5. Keep the architecture visually full but readable: use compact 13-15px module labels, short noun phrases, and move long explanation into the speaker notes.
6. Do not paste an architecture screenshot as the main content. AI images may be used only as faint blueprint backgrounds; architecture modules, labels, connectors, and layer boundaries remain editable SVG/PPT geometry.

## VII. Page Types

### 1. Cover Page (`01_cover.svg`)
- Product solution title page with platform architecture motif.

### 2. Business Pain (`02_business_pain.svg`)
- Frames current operational pain points and transformation pressure.

### 3. Solution Overview (`03_solution_overview.svg`)
- Shows the solution as a central platform with scenario, data, AI, and business value connections.

### 4. Product Architecture (`04_product_architecture.svg`)
- Dense multi-layer product architecture for software platform and digital solution presentations.
- Must preserve the Architecture Density Contract: five strata, 12-18 module nodes, right-side output column, integration base, and cross-layer flow cues.

### 5. Core Capabilities (`05_core_capabilities.svg`)
- Six modular capability cards for product features and system modules.

### 6. Application Scenarios (`06_application_scenarios.svg`)
- Scenario cards for industry applications and business landing paths.

### 7. Technical Route (`07_technical_route.svg`)
- Data-to-application route and technical flow.

### 8. Deployment Architecture (`08_deployment_architecture.svg`)
- Cloud / edge / on-prem deployment topology and security connection model.

### 9. Customer Value (`09_customer_value.svg`)
- Business value metrics and customer outcome mapping.

### 10. Implementation Path (`10_implementation_path.svg`)
- Phased rollout and delivery path.

## VIII. SVG Page Roster

| File | Role | Description |
|------|------|-------------|
| `01_cover.svg` | cover | Product solution cover and platform motif |
| `02_business_pain.svg` | pain | Business pain and transformation drivers |
| `03_solution_overview.svg` | overview | Solution overview and platform hub |
| `04_product_architecture.svg` | architecture | Layered product architecture |
| `05_core_capabilities.svg` | capability | Core system capabilities |
| `06_application_scenarios.svg` | scenario | Industry application scenarios |
| `07_technical_route.svg` | route | Technical route and data flow |
| `08_deployment_architecture.svg` | deployment | Deployment architecture and topology |
| `09_customer_value.svg` | value | Customer value and measurable outcomes |
| `10_implementation_path.svg` | implementation | Rollout and implementation path |

## IX. Layout Modes

| Mode | Recommendation |
| --- | --- |
| **Solution Pitch** | cover → pain → overview → architecture → value |
| **Product Deep Dive** | overview → architecture → capabilities → technical route → deployment |
| **Industry Proposal** | pain → scenario → solution overview → customer value → implementation |
| **Sales Enablement** | core capabilities and customer value pages with shorter copy and larger metrics |

## X. Spacing Specification

| Property | Value |
| --- | --- |
| **Base Unit** | 8px |
| **Module Gap** | 20-24px |
| **Card Radius** | 14-20px |
| **Title to Body** | 34-42px |
| **Footer Offset** | 32px from bottom |

## XI. SVG Technical Constraints

1. `viewBox` must stay `0 0 1280 720`.
2. Use plain hex colors with `fill-opacity` / `stroke-opacity`; do not use `rgba()`.
3. Do not use `<style>`, `class`, `foreignObject`, `textPath`, animation tags, masks, or scripts.
4. Keep all placeholder text in `{{PLACEHOLDER}}` form.
5. Keep product diagrams as editable SVG geometry, not screenshots.

## XII. Placeholder Specification

| Placeholder | Description |
| --- | --- |
| `{{TITLE}}` | Cover or page main title |
| `{{SUBTITLE}}` | Cover subtitle or page key message |
| `{{PRODUCT_TAG}}` | Product or solution category |
| `{{PAGE_TITLE}}` | Page title |
| `{{KEY_MESSAGE}}` | One-line message |
| `{{SECTION_NAME}}` | Section label |
| `{{SOURCE}}` | Source or attribution |
| `{{PAGE_NUM}}` | Page number |
| `{{MODULE_*}}` | Product modules or architecture layers |
| `{{CAPABILITY_*}}` | Capability titles and descriptions |
| `{{SCENARIO_*}}` | Scenario names and landing descriptions |
| `{{KPI_*}}` | Short numeric metrics for pain and customer value pages |
| `{{PHASE_*}}` | Implementation phase names and actions |

## XIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated smart mine / intelligent manufacturing platform architecture reference | Optional reference only. Do not paste it as fixed slide content; use it to guide custom industry visuals when real project screenshots or scenario images are supplied. |

The bitmap reference should not replace architecture content. Keep product diagrams, deployment topologies, capability maps, and implementation paths as editable SVG geometry unless the project explicitly supplies real product screenshots.
