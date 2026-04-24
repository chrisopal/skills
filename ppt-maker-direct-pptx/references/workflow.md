# Workflow

## Step 1: Confirm Input Completeness

Collect or confirm:

- topic
- audience
- purpose or scenario
- style direction
- page count
- key messages
- must-have sections
- branding constraints

Do not proceed until the deck can be outlined with confidence.
In the first version, `topic / target_audience / purpose / style / page_count` are all mandatory.

## Step 2: Recommend And Confirm Template

If the user did not explicitly select a concrete template, recommend one based on:

- purpose
- audience
- style direction
- topic context

Do not continue until the template is confirmed.

## Step 3: Generate Deck Outline

Generate the whole deck outline in one pass.

Expected output:

- storyline summary
- page-by-page outline
- each slide's purpose
- suggested layout type

Show the outline to the user and allow adjustments.
Do not continue until `outline_approved=true`.

## Step 4: Generate Structured Page Intents

Generate structured per-slide page intents for every slide in one pass.

Each slide should include:

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

The `slide_prompts.json` artifact must also include a `quality_checklist` that checks outline coverage, logic gaps, duplicate pages, missing customer data/assets, image placeholders, chart data fields, style consistency, audience fit, and readiness for PPT generation.

Then deterministically compile the final direct-rendering brief from:

- template preset
- deck-level master style brief
- page intent

Show the result to the user and allow adjustments.
Do not continue until `prompts_approved=true`.

## Step 5: Build Slide Specs

Transform the confirmed page intents into deterministic slide specs.

Each slide spec should contain:

- layout family
- visible content modules
- image placeholders and generated image assets
- `layout_regions.content` for text/cards/charts and `layout_regions.images` for reserved visual zones
- section hierarchy
- emphasis roles
- any KPI / roadmap / matrix / architecture layer structure

## Step 6: Generate Optional Image Assets

When `image_placeholders` exist, run the image asset tool before final rendering:

- `scripts/generate_image_assets.py`

The tool writes local PNG files, `image_manifest.json`, and updates `slide_specs.json` with `image_assets`.
Use `--dry-run` for placeholder PNGs during layout testing.
Image assets must inherit the reserved `layout_regions.images` coordinates instead of being placed as free-floating overlays.

## Step 7: Generate Page-Level JS And Draw PPTX

Generate one independent PptxGenJS module per slide:

- `slides/slide-01.js`
- `slides/slide-02.js`
- `slides/compile.js`

Each slide module must export a synchronous `createSlide(pres, theme)` function and draw one slide with native PowerPoint objects.
Prefer editable text boxes, rounded rectangles, cards, dividers, connectors, KPI strips, timelines, and architecture layers.
For image-aware pages, the module must expose `slideConfig.contentRegion` and `slideConfig.images`; text and cards stay in the content region while images stay in image regions.
Validate every module before compiling the final deck.
Save the resulting `.pptx` file to the requested output path.
