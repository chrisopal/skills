---
deck_id: huixin_product_solution
kind: deck
summary: 慧新产品解决方案、软件平台、AI平台、智能制造、数字化系统能力展示；包含复杂多层分域架构、业务/功能/系统/数据/集成/技术/部署架构、多系统集成总览、流程、实施、截图和案例页.
canvas_format: ppt169
canvas_width: 1280
canvas_height: 720
canvas_viewbox: "0 0 1280 720"
native_structure_mode: legacy-flat
replication_mode: standard
page_count: 22
primary_color: "#0097BA"
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
| **Technology Blue** | `#0097BA` | Platform architecture, system modules, navigation, process lines |
| **Vitality Green** | `#83C410` | AI capabilities, value points, highlights, product advantages, metrics |
| **Brand Gray** | `#D0CECE` | Module borders, structural partitions, connection lines, auxiliary notes |
| **Wordmark Black** | `#000000` | Official Huixin wordmark on light backgrounds |
| **Deep Blue Gray** | `#111111` | Titles, body text, premium background blocks, technical base layer |
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

**Primary Font**: `"MiSans, Microsoft YaHei, Arial, sans-serif"`

**SVG Font**: `"MiSans, Microsoft YaHei, Arial, sans-serif"` — use MiSans first with Microsoft YaHei / Arial fallback.

### Latest Light Template Baseline

This deck follows the official `慧新全智PPT模板_浅色版本.pptx` visual baseline (source SHA-256: `0b700b898693c99b6ef50a4a00db5ad3c81ba9bb02fe46bec712d545841a1906`). Use the latest high-resolution Huixin Quanzhi lockup, `#0097BA` technology blue, `#83C410` vitality green, `#D0CECE` structural gray, white / very-light-gray working backgrounds, and MiSans typography. Covers use the industrial mosaic at the right; chapter pages may use the teal chapter background; standard content pages use the compact lower-left logo and blue-green footer ribbon. Existing dense architecture pages may retain a compact top-right logo when the lower footer would reduce diagram capacity.

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

### Template Adaptation Rules

1. Prefer the reusable SVG page type / master defined in this spec when it fits the source story, content density, and expected decision path.
2. Do not force source content into a template page when the real solution needs more layers, swimlanes, systems, data flows, actors, stages, or exception paths than the base page expresses.
3. Custom or recomposed pages are allowed when the content requires them, but they must preserve Huixin's palette, white / light-gray technical background style, top-right logo discipline, slanted-bar brand geometry, editable SVG structure, and product-solution narrative logic.
4. Architecture pages must communicate the actual architecture rather than the template's default layer count. If a product or integration architecture has more than five logical layers, multiple platforms, cloud / edge / device layers, AI / data / integration / security / governance layers, or complex bidirectional interfaces, redesign the diagram structure to fit the content instead of using the five-layer base unchanged.
5. When adapting an architecture page, keep domains grouped and labeled, use blue for product / system structure, green for value / flow / checkpoints, gray for neutral boundaries / infrastructure, and preserve a clear reader path from business capability -> application / system -> data / integration -> deployment / operation.

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

1. Use five visible architecture strata as the simple baseline: user/application, business process, platform services, data/AI, and integration/foundation. Extend, split, or regroup the strata when the source architecture is more complex.
2. Fill the body with 12-18 editable module nodes distributed across the strata; avoid empty bands, oversized labels, or only 3-4 broad rectangles.
3. Include a right-side output, governance, or value column with 3-4 short deliverables such as dashboards, evidence packages, risk alerts, APIs, control points, or operating views.
4. Draw at least two cross-layer arrows or data-flow cues so the page reads as a system, not a static list.
5. Keep the architecture visually full but readable: use compact 13-15px module labels, short noun phrases, and move long explanation into the speaker notes.
6. Do not paste an architecture screenshot as the main content. AI images may be used only as faint blueprint backgrounds; architecture modules, labels, connectors, and layer boundaries remain editable SVG/PPT geometry.
7. If the architecture has many systems or domains, prioritize truthful grouping and readable relationships over preserving the template's original number of bands, columns, or nodes.

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
9. **Complex multi-domain architecture (`22_complex_multi_domain_architecture.svg`)**: use this when a solution needs a high-density architecture page with central L1-L5 or equivalent layers, left/right domain swimlanes, secondary function labels, platform support blocks, and cross-domain collaboration arrows. Use it for complex smart factory, industrial internet, multi-platform AI, data + twin + security + operations architectures where ordinary five-layer architecture or single integration overview pages are too thin.

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
- Use as the default for straightforward platform architecture. For complex product architecture, preserve the Architecture Density Contract while extending or recomposing strata, module groups, output columns, and cross-layer flow cues according to the real content.

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

### 22. Complex Multi-Domain Architecture (`22_complex_multi_domain_architecture.svg`)
- High-density architecture page with a central five-layer architecture stack, left and right domain swimlanes, bottom support platforms, and cross-domain collaboration arrows.
- Use this when the content needs second-level functions and short explanations inside each layer, plus business / device / intelligent / governance domains around the central system stack.
- This is the preferred page for complex smart factory, industrial internet, AI platform, data middle platform, digital twin, cyber-physical, and security-governed architectures when a simple five-layer product architecture cannot carry the meaning.

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
| `22_complex_multi_domain_architecture.svg` | complex_multi_domain_architecture | Complex high-density multi-layer architecture with central layers, left/right domain swimlanes, support platforms, secondary functions and cross-domain collaboration |

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
| `images/huixin_logo_light.png` | Latest high-resolution Huixin Quanzhi lockup | Default logo on white and light pages. |
| `images/huixin_logo_dark.png` | Reverse Huixin lockup | Use only on dark technical fields. |
| `images/huixin_light_cover_mosaic.png` | Official light-template industrial mosaic | Use for covers and image-led closings without replacing editable titles. |
| `images/huixin_light_content_bg.png` | Official subtle light geometric background | Use at low visual weight on agenda or sparse content pages. |
| `images/huixin_light_chapter_bg.png` | Official teal chapter background | Use for chapter dividers and major solution sections. |
| `images/huixin_light_footer_ribbon.png` | Official blue-green footer ribbon | Use with the lower-left logo on standard content pages. |

The bitmap reference should not replace architecture content. Keep product diagrams, deployment topologies, capability maps, and implementation paths as editable SVG geometry unless the project explicitly supplies real product screenshots.
