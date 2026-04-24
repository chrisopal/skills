# Prompt Templates

## Requirement Confirmation Prompt

Use this pattern to confirm missing inputs:

```text
You are a presentation requirements analyst.
Extract and confirm the following fields from the user's request:
- topic
- target audience
- purpose / scenario
- preferred style
- page count
- key points
- must-have sections
- hard constraints

Return JSON only:
- summary
- missing_fields
- recommended_follow_up_questions
```

## Template Recommendation Prompt

Use this pattern when requirement fields are complete but no concrete template has been confirmed:

```text
You are a presentation template recommender.
Choose the best template for the following requirement.

Requirement:
{requirement_json}

Required page count:
{page_count}

Available templates:
{templates_json}

Return JSON only:
- recommended_template_id
- recommended_template_name
- reason

Constraints:
- choose exactly one template
- prioritize consistency with purpose, audience, and stated style
- if the style clearly matches one template, choose that exact template
```

## Outline Generation Prompt

Use this pattern for outline generation:

```text
You are a senior presentation strategist.
Based on the confirmed requirement below, generate a complete PPT deck outline.

Requirement:
{requirement_json}

Return JSON only:
- storyline
- deck_structure
- slides

Each slide must contain:
- page_no
- title
- subtitle
- purpose
- layout_type
- key_blocks
- image_placeholders

Constraints:
- keep the narrative coherent
- match the audience and scenario
- avoid redundant slides
- keep language concise and presentation-ready
- make each page role clear and non-overlapping
- generate exactly the required page count
- every slide should have a distinct role in the story, not generic repeated sections
- if a slide needs a product visual, scenario illustration, architecture visual, photo-like asset, or generated diagram, include 1-2 image_placeholders
- each image_placeholders item must include id, role, purpose, prompt, placement, required
- placement should use 16:9 inches: x, y, w, h
- placement must reserve a dedicated visual zone and must not overlap the intended title, text, card, chart, timeline, or architecture regions
```

## Master Style Brief Generation Prompt

Use this pattern after the requirement is confirmed and before per-slide prompt generation:

```text
You are a senior presentation design director.
Generate a structured deck-level master style brief for this presentation.

Requirement:
{requirement_json}

Template preset:
{template_preset_json}

Return JSON only with:
- visual_positioning
- deck_voice
- color_strategy
- typography
- title_hierarchy_rules
- layout_system
- module_layout_patterns
- chart_rules
- icon_rules
- forbidden_elements
- prompt_block

Constraints:
- keep the output practical and reusable across the whole deck
- define title hierarchy, module layout rules, chart style, and forbidden elements explicitly
- align to the named template preset if one exists
```

## Per-Slide Prompt Generation Prompt

Use this pattern after the outline is confirmed:

```text
You are a presentation page-intent designer.
Given the confirmed requirement, the deck-level style brief, and the approved outline, generate structured page intents for every slide in one batch.

Requirement:
{requirement_json}

Master style:
{master_style_json}

Outline:
{outline_json}

Return JSON only:
- slides
- quality_checklist

Each slide item must contain:
- page_no
- title
- subtitle
- page_goal
- layout_type
- key_blocks
- image_placeholders
- visual_focus
- detail_notes
- page_position
- core_message
- copy_content
- layout_design
- visual_elements
- image_placeholder_advice
- chart_advice
- speaker_notes
- final_generation_prompt

`copy_content` must contain:
- main_title
- subtitle
- key_phrases
- body_notes
- data_placeholders

`image_placeholder_advice` must contain:
- needed
- note
- placeholders

Each image placeholder advice item must contain:
- image_position
- image_purpose
- image_content_description
- image_style
- image_ratio
- image_generation_prompt
- image_search_keywords

`chart_advice` must contain either:
- needed=false and note="本页不需要图表。"
or:
- needed=true
- chart_type
- data_fields
- visual_focus
- data_placeholders

`speaker_notes` must contain 2-4 short Chinese sentences.

`final_generation_prompt` must be a complete single-paragraph prompt following this pattern:
“请生成一页 16:9 的 PPT，页面标题为《...》。本页用于...，核心观点是...。整体采用...风格，版式为...。页面包含以下文案：...。视觉上使用...。如有图片，请在...放置图片占位，图片内容为...，风格为...。如有图表，请使用...展示...。整体要求信息清晰、留白充足、层级分明、适合商务演示。”

`quality_checklist` must contain:
- complete_outline_coverage
- logic_gap_check
- one_core_message_per_page
- duplicate_pages
- customer_data_or_assets_needed
- image_placeholders_executable
- charts_have_data_fields
- style_consistency
- audience_and_scenario_fit
- ready_for_ppt_generation

Constraints:
- maintain a consistent visual system across all slides
- preserve a coherent deck narrative
- make each slide specific to its outline role; avoid repeating the same 3 modules on every page
- keep structure suitable for later deterministic prompt compilation
- avoid vague filler descriptions
- write visible page content and invisible guidance separately in intent fields
- make key_blocks specific enough for direct PPT rendering, with 2-4 blocks and concrete items where possible
- use image_placeholders only for real visual needs; do not force images onto every page
- image placeholders must have concrete generation prompts and placement hints
- image placeholders must describe whether the visual belongs on the right, left, bottom band, or full-bleed background; default is a right-side reserved visual zone with the main content compressed to the left
- every page must be suitable for human review before rendering, not only suitable for direct code generation
- every page must have exactly one core_message
- if data is needed but unavailable, use explicit placeholders such as 【市场规模数据待补充】 or 【客户名称待确认】
```

## Direct Rendering Brief

Use the compiled prompt as a deck-consistent rendering brief for page-level PptxGenJS generation.
It is not a raster image prompt in this skill.

Typical contents should include:

- visible page title and subtitle
- key content modules and their hierarchy
- layout rhythm and spacing emphasis
- invisible design guidance from page_goal / visual_focus / detail_notes
- explicit prohibitions against page noise and random edge microcopy

The direct renderer consumes this brief together with:

- `master_style.json`
- structured page intent
- template preset

to synthesize `slide_specs.json`, then generate one independent `slides/slide-XX.js` module per page.

## Page-Level PptxGenJS Generation Prompt

Use this pattern when generating a single page module:

```text
You are generating one complete PptxGenJS slide module.
Return only JavaScript code. No Markdown fences.

Required contract:
- CommonJS module
- export module.exports = { createSlide, slideConfig }
- createSlide(pres, theme) is synchronous
- createSlide adds exactly one slide and returns it
- use only PptxGenJS native objects
- do not import files, use remote assets, async code, eval, fs, or child_process
- do not use `require()` or `import`; compile.js provides the `pres` object
- use shape type strings such as `'rect'`, `'roundRect'`, `'line'`, `'ellipse'`, and `'parallelogram'`; never use `PptxGenJS.ShapeType`, `pptxgen.ShapeType`, or `pres.ShapeType`
- if image_assets contains local paths, embed them with slide.addImage at their placement
- if image_placeholders exist without image_assets, draw clean editable placeholder frames
- if layout_regions.images is not empty, slideConfig must include contentRegion and images copied from layout_regions_json

Input:
- visible_content_json
- visible_content_json may include image_placeholders and image_assets
- layout_regions_json with content and image reserved zones
- invisible_guidance_json
- master_style_json
- template_rendering_recipe
- theme_json
- page_no / total_slides

Hard rules:
- render only visible content
- do not render field names or raw internal values: layout_family, page_goal, visual_focus, detail_notes, template_name, template_id
- do not add page numbers, 16:9 labels, watermarks, random corner labels, or template names
- create page-specific layouts from content; avoid repeated generic three-card pages
- use Chinese Microsoft YaHei, readable sizes, and keep text inside shapes
- every card must have a separated title zone and body zone; body text starts below the title zone
- do not place bullet lists inside tiny chips or cards below 1.0 inch high
- if a slide has 4 or more content blocks, prefer a grid/matrix layout instead of a split layout with squeezed extra cards
- keep all non-title text, cards, charts, timelines, and architecture rows inside layout_regions.content
- keep all image assets/placeholders inside layout_regions.images
- never place generated images on top of text boxes, cards, KPI strips, module titles, or connectors
```

## PptxGenJS Repair Prompt

Use this pattern if a generated page module fails validation:

```text
You are repairing one PptxGenJS slide module.
Return only corrected JavaScript code. No Markdown fences.

Validation error:
{error}

Original slide spec:
{slide_spec_json}

Master style:
{master_style_json}

Previous JavaScript:
{previous_js}

Keep the same required module contract and remove any forbidden internal strings.
```

## Single Slide Prompt Regeneration Prompt

Use this pattern only when a future flow needs the model to rewrite page-intent fields. The default v1 implementation recompiles deterministically instead of relying on this prompt.

```text
You are a presentation page-intent editor.
Refine the current slide intent while preserving deck-level consistency.

Requirement:
{requirement_json}

Master style:
{master_style_json}

Whole outline:
{outline_json}

Current slide:
{slide_json}

Existing slide prompt:
{existing_prompt_json}

Additional instruction:
{regeneration_instruction}

Return JSON only with:
- page_no
- title
- subtitle
- page_goal
- layout_type
- key_blocks
- visual_focus
- detail_notes
```
