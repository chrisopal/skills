---
deck_id: huixin_product_solution
kind: deck
summary: 慧新产品解决方案、软件平台、AI平台、智能制造、数字化系统能力展示.
canvas_format: ppt169
page_count: 21
primary_color: "#4295B6"
---

# Huixin Product Solution - Design Specification

## I. Template Overview

| Property | Description |
| --- | --- |
| **Template Name** | huixin_product_solution |
| **Display Name** | 慧新产品解决方案模板 |
| **Use Cases** | 软件产品、数字化平台、智能制造解决方案、AI平台、行业应用方案展示、产品功能讲解、系统架构汇报、跨系统集成方案、客户案例介绍 |
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

## V. Logo, Icon and Brand Mark

| Asset | Description |
| --- | --- |
| **Official Huixin Lockup** | Embedded from the official Huixin logo assets: use the light logo on white or light backgrounds and the dark-background logo with white wordmark on deep color fields. |
| **Huixin Brand Icon Language** | Product-solution templates MUST use Huixin's slanted-bar geometry as the default icon / pictogram language: right-leaning parallelogram bars, angled tabs, segmented arrows, module chips, and line+bar hybrids in blue/green/gray. |

Usage rules:

1. Use the slanted-bar logo geometry as the core product visual language.
2. Keep the mark in the top-right on light technical pages.
3. Use the black wordmark on light backgrounds and the white wordmark only on deep blue-gray backgrounds.
4. Preserve the horizontal logo lockup, slanted-bar proportions, and blue underline.
5. Do not add cyberpunk glow, unnecessary 3D, or complex gradients.
6. Do not default to generic third-party pictograms. Built-in icon libraries may be used only as small auxiliary symbols when the idea cannot be expressed by Huixin slanted geometry; they must not visually dominate the page.
7. For architecture, process, feature and case pages, prefer editable Huixin-style geometric pictograms over imported bitmap icons.

### Mandatory Huixin Icon / Diagram Contract

Every generated page that uses this deck should include at least one visible Huixin brand-geometry cue beyond the logo: slanted bars, angled module tabs, diagonal separators, segmented chevrons, or parallelogram highlights. These cues are not decorative extras; they are the deck's icon system and should replace generic auto-generated icons wherever possible.

## VI. Layout Structure

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
4. Keep information density moderate on ordinary content pages, but architecture and process pages should be visually full and module-rich.
5. Express platformization through layers, reusable components, flows, and scalable deployment options.
6. Product-solution decks should include more than one architecture type when the source content supports it: business architecture, functional architecture, system/technical architecture, data architecture, integration architecture, multi-system integration overview, technical route, deployment architecture, swimlane process flow, dense business process diagram, and implementation stage plan should be distinct page forms, not one repeated card grid.
7. When no real screenshots are supplied, use the `16_feature_detail_screenshot.svg` empty-screen frame rather than inventing fake UI details. The placeholder should be visually polished and clearly replaceable.

### Architecture Density Contract

Product architecture pages must feel like mature enterprise software architecture, not a simple three-row stack. When a page uses `04_product_architecture.svg` or any of the architecture templates (`11`-`15`, `17`, `19`):

1. Show at least five visible architecture strata: user/application, business process, platform services, data/AI, and integration/foundation.
2. Fill the body with 12-18 editable module nodes distributed across the strata; avoid empty bands, oversized labels, or only 3-4 broad rectangles.
3. Include a right-side output or value column with 3-4 short deliverables such as dashboards, evidence packages, risk alerts, or APIs.
4. Draw at least two cross-layer arrows or data-flow cues so the page reads as a system, not a static list.
5. Keep the architecture visually full but readable: use compact 13-15px module labels, short noun phrases, and move long explanation into the speaker notes.
6. Do not paste an architecture screenshot as the main content. AI images may be used only as faint blueprint backgrounds; architecture modules, labels, connectors, and layer boundaries remain editable SVG/PPT geometry.

### Complex Diagram Page Contract

For industrial software solution decks, use the dedicated complex diagram pages when the user asks for architecture, integration, functional map, data governance, or process flow:

1. **Technical / system architecture (`13_system_architecture.svg`)**: use 6-8 horizontal technical strata with client, access, gateway, service governance, service, data/middleware, and infrastructure rows. Include a CI/CD or operations column and a short checklist.
2. **Integration architecture (`15_integration_architecture.svg`)**: use a dark enterprise system map with ERP/PLM/SRM/WMS/WCS/RCS and platform modules connected by editable arrows. Use this for “平台集成架构”, “系统集成”, “一体化方案”.
3. **Business process swimlane (`17_business_process_flow.svg`)**: use 3-5 vertical swimlanes with staged process nodes and cross-lane handoff arrows.
4. **Business process diagram (`19_business_process_diagram.svg`)**: use this when the source describes end-to-end business flows with a main path, resource coordination, quality / review gates, exception handling, and loopback relationships. Prefer a dense but clean editable process diagram. Reference images may inform structure density only; do not copy their exact titles, nodes, colors, or screenshots.
5. **Functional architecture (`12_function_architecture.svg`)**: use module matrices and layered platform bands for application modules, API middle platform, common platform, and data acquisition.
6. **Data architecture (`14_data_architecture.svg`)**: use governance framework rows for standards, quality, security, organization, workflow, tools, portal, functions, data scope, and foundation. The page should feel like a full data-management framework, not only source-to-dashboard flow.
7. **Implementation stage plan (`20_implementation_stage_plan.svg`)**: use this when the source describes phased delivery, rollout roadmap, implementation planning, product deployment stages, or digital transformation implementation steps. Reference images may inform the four-stage planning rhythm only; keep Huixin's clean product-solution style and use product-solution content, not the reference page's text.
8. **Multi-system integration overview (`21_multi_system_integration_overview.svg`)**: use this when the source asks for an overview of two or more systems working together, such as QMS/PLM, MES/WMS, ERP/MES, SRM/PLM, or any platform-to-platform integration. Keep the page abstract at template level: upstream systems, two core systems, right-side execution / data-closed-loop groups, and bottom end-to-end process can be specialized by downstream content, but the global template must not hard-code a specific product pair.

### Default AI Image and Screenshot Policy

When using this deck, Strategist should normally include image resources unless the user explicitly asks for a pure text/SVG deck:

1. **AI-generated imagery by default**: add 1-3 `Acquire Via: ai` rows for cover / section divider / industry scene / abstract platform blueprint when the source has no real visual assets. These images are supporting ambience, not replacements for editable architecture diagrams.
2. **Product screenshots**: if real screenshots are absent, use `16_feature_detail_screenshot.svg` with a polished empty screenshot placeholder. Do not hallucinate real UI screens unless the user asks for AI-generated UI mockups.
3. **Architecture pages**: keep architecture, process, modules, data flows, labels and connectors as editable SVG geometry. AI images may appear only as low-opacity background texture or side illustration.
4. **Case pages**: `18_case_study_triptych.svg` may include placeholder image regions for customer site, product interface, or project scene. Use AI images only when the user wants illustrative case visuals and accepts generated imagery.

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

### 11. Business Architecture (`11_business_architecture.svg`)
- Value-chain or business domain architecture page for showing business stages, support capabilities, and operating model.

### 12. Function Architecture (`12_function_architecture.svg`)
- Dense product functional map with factory application module matrix, API middle platform, shared platform services, data acquisition layer, and external system column.

### 13. System Architecture (`13_system_architecture.svg`)
- Technical / system-layer architecture with client, access, gateway, service governance, services, data/middleware, infrastructure, and CI/CD operations column.

### 14. Data Architecture (`14_data_architecture.svg`)
- Data governance and management architecture covering data standards, quality, security, organization, workflows, tools, portal, functions, data scope, and foundation.

### 15. Integration Architecture (`15_integration_architecture.svg`)
- Dark enterprise integration map for ERP, PLM, SRM, WMS, WCS/RCS, production execution, warehouse, quality, equipment, and unified technical platform interactions.

### 16. Feature Detail With Screenshot (`16_feature_detail_screenshot.svg`)
- Detailed product function explanation page with a large replaceable system screenshot placeholder and side highlights.

### 17. Business Process Flow (`17_business_process_flow.svg`)
- Swimlane process flow for warehouse, production, quality, approval, service, and on-site execution processes.

### 18. Case Study Triptych (`18_case_study_triptych.svg`)
- Customer case page using the three-part narrative: customer pain, implemented solution, value gains. Includes replaceable screenshot / product / customer site placeholders.

### 19. Business Process Diagram (`19_business_process_diagram.svg`)
- Dense generic business process diagram for end-to-end process explanation across trigger, task split, resource coordination, execution, review / quality gate, exception handling, loopback, and performance recap.

### 20. Implementation Stage Plan (`20_implementation_stage_plan.svg`)
- Complex four-stage implementation planning page with phase goals, key focus items, build strategies, and deliverables. Use for roadmap, project rollout, implementation planning, and phased product deployment.

### 21. Multi-System Integration Overview (`21_multi_system_integration_overview.svg`)
- Generic high-density integration overview page for showing two or more business systems as a coordinated architecture.
- Template-level labels remain abstract: upstream system group, core system one, core system two, business collaboration, data closed loop, and end-to-end process.
- Use this page when the requested content is a cross-system integration summary rather than a single technical stack or dark enterprise system map.

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
| `11_business_architecture.svg` | business_architecture | Business value-chain / operating architecture |
| `12_function_architecture.svg` | function_architecture | Product functional architecture and capability clusters |
| `13_system_architecture.svg` | system_architecture | System architecture with access, service, data and foundation layers |
| `14_data_architecture.svg` | data_architecture | Data source, governance and service architecture |
| `15_integration_architecture.svg` | integration_architecture | Integration hub and enterprise system connections |
| `16_feature_detail_screenshot.svg` | feature_detail | Product feature detail with screenshot placeholder |
| `17_business_process_flow.svg` | process_flow | Business / implementation / data process flow |
| `18_case_study_triptych.svg` | case_study | Three-part customer case: pain, solution, value |
| `19_business_process_diagram.svg` | business_process_diagram | Dense generic business process diagram with main path, branches and loopbacks |
| `20_implementation_stage_plan.svg` | implementation_stage_plan | Complex phased implementation plan with goals, focus items, strategies and deliverables |
| `21_multi_system_integration_overview.svg` | multi_system_integration_overview | Generic two-or-more-system integration overview with upstream systems, dual core systems, execution/data loop groups and end-to-end process |

## IX. Layout Modes

| Mode | Recommendation |
| --- | --- |
| **Solution Pitch** | cover → pain → overview → architecture → value |
| **Product Deep Dive** | overview → architecture → capabilities → technical route → deployment |
| **Architecture Deep Dive** | business architecture → function architecture → system/technical architecture → data architecture → multi-system integration overview → integration architecture → deployment architecture |
| **Industry Proposal** | pain → scenario → solution overview → business architecture → case study → customer value → implementation |
| **Sales Enablement** | core capabilities and customer value pages with shorter copy and larger metrics |
| **Case Selling** | pain → solution overview → feature detail screenshot → case study triptych → value → implementation |

## X. Spacing Specification

| Property | Value |
| --- | --- |
| **Base Unit** | 8px |
| **Module Gap** | 20-24px |
| **Card Radius** | 14-20px |
| **Title to Body** | 34-42px |
| **Footer Offset** | 32px from bottom |

## XI. SVG Technical Constraints

1. `viewBox` must stay `0 0 1280 720` and the SVG root must include `width="1280"` and `height="720"`.
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
| `{{BUSINESS_*}}` | Business architecture domain, stage and support layer content |
| `{{FUNC_*}}` | Function architecture groups, feature names and descriptions |
| `{{SYSTEM_*}}` | System architecture layer and service content |
| `{{DATA_*}}` | Data source, governance, platform and service labels |
| `{{INTEGRATION_*}}` | Integration hub, connected systems, protocols and security notes |
| `{{SCREENSHOT_PLACEHOLDER}}` | Empty product screenshot / system UI placeholder label |
| `{{CASE_*}}` | Case-study title, subtitle and case facts |
| `{{PAIN_*}}` | Customer pain text blocks on case pages |
| `{{SOLUTION_*}}` | Solution actions on case pages |
| `{{VALUE_*}}` | Case value metrics and benefit descriptions |
| `{{PROCESS_*}}` | Dense process network nodes, handoffs, exception paths and loopback relationships |

## XIII. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated smart mine / intelligent manufacturing platform architecture reference | Optional reference only. Do not paste it as fixed slide content; use it to guide custom industry visuals when real project screenshots or scenario images are supplied. |

The bitmap reference should not replace architecture content. Keep product diagrams, deployment topologies, capability maps, and implementation paths as editable SVG geometry unless the project explicitly supplies real product screenshots.
