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
| **Use Cases** | 慧新品牌市场宣传、产品推广、解决方案推广、渠道招商、客户活动、展会路演、销售赋能材料 |
| **Design Tone** | High-impact, brand-forward, technology-led, sales-conversion oriented |
| **Theme Mode** | Marketing and brand communication theme based on Huixin logo colors |

### Huixin Business Portfolio Context

When this template is used without more specific source material, assume Huixin's market-facing portfolio covers:

1. **Metrology and inspection equipment**: 三坐标, 影像仪, 自动化检测产线装备, inspection automation, quality measurement scenarios.
2. **Smart factory and industrial software**: MES / MOM, QMS, WMS, EAM, industrial AI, IoT platform, integrated factory platform.
3. **Smart mine solutions**: mine safety, production dispatch, equipment monitoring, digital twin mine visualization, integrated command.
4. **Smart city scenarios**: smart park, emergency response, water conservancy, urban lifeline, city operation management.
5. **Common platform products**: integrated low-code / industrial application platform, IoT platform, digital twin GIS platform, data / AI middle platform.

The deck should translate these businesses into customer-facing value language: scene, pain, capability, proof, ROI, next action.

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

### Existing Editable SVG Base Pages

These are the current reusable SVG bases. Use them directly when they match the output story; otherwise derive new pages from the same Huixin visual language.

#### 1. Cover Page (`01_cover.svg`)

- High-impact title page for campaign or product promotion.
- Includes campaign tag, title, subtitle, date, and brand mark.

#### 2. Market Opportunity (`02_market_opportunity.svg`)

- Frames target market pain, growth trigger, and buying reason.
- Suitable for opening the argument before product details.

#### 3. Value Proposition (`03_value_proposition.svg`)

- Three value pillars with supporting proof points.
- Suitable for business value, customer value, and technical value.

#### 4. Three-Axis Promotion (`04_three_axis_promotion.svg`)

- Dedicated page for 三坐标 / three-coordinate promotion logic.
- Uses an x/y/z axis metaphor: capability, scenario, conversion.

#### 5. Scenario Proof (`05_scenario_proof.svg`)

- Shows customer scenarios and proof points.
- Suitable for cases, user stories, and adoption evidence.

#### 6. Campaign Plan (`06_campaign_plan.svg`)

- Converts strategy into a staged promotion plan.
- Suitable for campaign channels, rhythm, responsibilities, and KPIs.

#### 7. Content Page (`07_content.svg`)

- General-purpose content page with open body region.
- Suitable for tables, diagrams, product feature detail, or customer quotes.

#### 8. Ending Page (`08_ending.svg`)

- Closing call-to-action page.
- Suitable for contact, next step, QR / link placeholder, and final slogan.

### Extended Marketing Page Archetype Catalog

Use this catalog as the primary reference when planning Huixin market decks. Do not force every archetype into one deck; select the subset that supports the campaign goal, page count, audience, and source material.

| Category | Archetypes | Recommended Use |
| --- | --- | --- |
| **A. Brand and Cover** | 品牌主视觉封面, 产品宣传封面, 行业解决方案封面, 活动路演封面, 品牌 Slogan 页 | Open with brand memory, campaign theme, and the main conversion promise. Use large image treatment and slanted Huixin geometry. |
| **B. Value Proposition** | 一句话产品定位页, 核心价值主张页, 客户收益总览页, Before / After 价值对比页, 痛点到价值转化页 | Turn product capabilities into customer value. Prefer short claims, proof metrics, and high-contrast value cards. |
| **C. Pain and Scenario** | 行业挑战页, 客户痛点页, 业务场景痛点地图, 角色痛点页, 流程堵点页, 风险场景页 | Make the customer recognize the problem. Use scenario maps, role cards, process bottlenecks, and risk callouts. |
| **D. Product and Solution** | 产品总览页, 产品功能架构页, 核心模块页, 单功能亮点页, 产品界面展示页, 平台能力页, AI 能力页, 设备 / 硬件展示页, 系统集成能力页, 端到端解决方案页 | Explain what Huixin offers. Use product screenshots, UI mockups, equipment photos, module cards, and simple architecture visuals. |
| **E. Scenario Applications** | 单场景解决方案页, 多场景应用矩阵页, 业务流程闭环页, 现场到管理闭环页, 行业应用地图页, 客户角色视角页, 试点场景页 | Show how the offer lands in real work. Use left/right scene images, workflow loops, and application matrices. |
| **F. Selling Points and Differentiation** | 三大核心卖点页, 四大能力亮点页, 差异化优势页, 技术领先性页, 体验优势页, 交付优势页, 生态优势页 | Help sales teams answer "why Huixin". Use comparison blocks, capability badges, and concise proof evidence. |
| **G. Data and Case Proof** | 关键成果数据页, ROI 收益页, 使用前后效果对比页, 客户案例总览页, 单客户案例页, 标杆案例故事页, 客户 Logo 墙页, 荣誉资质页 | Build trust and decision confidence. Use large numbers, Before/After, case story structure, logos, and certificate tiles. |
| **H. Conversion and Closing** | 合作路径页, 下一步行动 / 联系我们页 | End with a clear next step: demo, pilot, site visit, diagnostic workshop, quotation, or contact. |

### Page Selection Guidance

1. **Equipment promotion decks** should prioritize: product宣传封面, 行业挑战, 单功能亮点, 设备/硬件展示, 使用前后效果对比, ROI收益, 合作路径.
2. **Smart factory / smart mine solution decks** should prioritize: 行业解决方案封面, 业务场景痛点地图, 产品总览, 平台能力, 业务流程闭环, 多场景应用矩阵, 标杆案例故事.
3. **Smart city / park / emergency / water decks** should prioritize: 行业应用地图, 风险场景, 现场到管理闭环, 数字孪生 GIS 平台, 客户角色视角, 试点场景.
4. **Common platform decks** should prioritize: 一句话产品定位, 平台能力, AI能力, 系统集成能力, 端到端解决方案, 生态优势.
5. **Event / roadshow decks** should prioritize: 活动路演封面, 品牌 Slogan, 核心价值主张, 三大核心卖点, 客户案例总览, 下一步行动.

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
| **Image-Led Marketing** | Every main page must include a meaningful image slot or generated image asset; image must support the value claim instead of acting as decoration |
| **Sales Enablement** | Use product-overview, objection-handling, differentiation, case proof, and next-action archetypes |

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

## XII. Mandatory Image Policy

This market promotion deck is image-led. Images are **required**, not optional, unless the page is a pure agenda / legal appendix / contact-only utility page.

### Image Requirement

1. Every cover, value, pain, product, scenario, proof, case, and CTA page must include at least one relevant image region.
2. If the user provides real product photos, UI screenshots, customer site photos, case photos, diagrams, or brand assets, prioritize user-provided images.
3. If no suitable user image exists, Strategist must add AI-generated image rows in the Image Resource List (`Acquire Via: ai`) or explicit placeholder rows (`Acquire Via: placeholder`) for UI screenshots / customer site photos that should be replaced later.
4. Do not leave the image strategy as "optional reference only" for market decks. The Eight Confirmations item "Image usage approach" should state mandatory image use and the expected source: user / ai / placeholder / web.

### Allowed Image Types

| Image Type | Typical Huixin Use |
| --- | --- |
| **Scene photo** | factory floor, inspection room, mine dispatch center, city operation center, park command center, emergency response scene |
| **Product photo** | 三坐标, 影像仪, automated inspection line, sensors, edge devices, equipment cabinet |
| **UI screenshot** | MES / QMS / MOM dashboard, IoT platform, digital twin GIS map, smart mine cockpit, smart city command screen |
| **Data visual** | KPI dashboard, ROI chart, before/after operating metrics, quality trend |
| **Customer site photo** | implementation site, production line, control room, field inspection, project delivery moment |
| **People photo** | engineer, operator, quality manager, site manager, executive presentation, customer workshop |
| **Abstract technology visual** | digital twin grid, industrial AI data flow, platform network, geometric blue-green brand render |

### Image Position Patterns

| Position | Usage Rule |
| --- | --- |
| **Left large image** | Use for pain / scenario / case story pages where text explains the image. |
| **Right large image** | Use for product / solution / value pages where claim and bullets lead from the left. |
| **Full-screen background** | Use only on cover, section divider, slogan, CTA, or event pages with dark overlay and short text. |
| **Card images** | Use for multi-scenario matrix, customer case overview, product capability cards, or role pain cards. |
| **Top banner** | Use for event, roadshow, product launch, or industry solution opening pages. |

### Image Ratios

| Ratio | Recommended Page Use |
| --- | --- |
| **16:9** | hero images, full-width banners, product UI screenshots, command-center visuals |
| **4:3** | equipment photos, customer site photos, case evidence images |
| **1:1** | card thumbnails, product icons, scene matrix visuals |
| **Portrait** | people photos, equipment closeups, event posters, vertical phone / mobile UI mockups |

### Image Style

1. Prefer **real business photography** for customer trust and field credibility.
2. Use **3D technology rendering** for platform, AI, IoT, digital twin, and abstract capability pages.
3. Use **flat illustration** only when explaining process, roles, or concepts; keep it enterprise-grade, not cartoon-like.
4. Use **UI Mockup** for product pages: screenshot frame, browser frame, dashboard window, or device frame.
5. Use **scene compositing** for marketing hero pages: product/UI floating above factory, mine, city, or command-center backgrounds.

### Prohibited Image Treatment

1. Do not use images with long paragraphs, dense labels, or unreadable embedded text.
2. Do not use low-resolution, blurry, pixelated, watermarked, or obviously stock-like images.
3. Do not use childish cartoon styles, comic style, anime style, or inconsistent illustration languages.
4. Do not mix photography, cyberpunk glow, cartoon illustration, and flat UI in the same page unless the page is explicitly a composite with clear hierarchy.
5. Do not paste a generated full-slide image as the whole page when editable SVG text / shapes should be used. Image should support the slide, while titles, claims, metrics, and CTA remain editable SVG / PPT objects.

## XIII. Placeholder Specification

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
| `{{IMAGE_SLOT}}` | Required image placeholder for scene / product / UI / data / case image |
| `{{IMAGE_CAPTION}}` | Short caption that explains the image's business meaning |
| `{{PRODUCT_DOMAIN}}` | Huixin business domain: equipment / smart factory / smart mine / smart city / platform |

## XIV. Asset Specification

| Asset | Purpose | Usage |
| --- | --- | --- |
| `images/reference_visual.png` | Imagegen-generated MES marketing visual reference | Optional reference only. Do not paste it as fixed slide content; use it to guide custom project imagery when a real MES product screenshot or campaign visual is available. |

The default template pages must remain editable SVG. Keep business messages, metrics, CTA, logo geometry, product/UI overlays, dashboards, and page structure as SVG text and shapes. Images should be embedded into planned image slots and should never replace the whole editable slide.
