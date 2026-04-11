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
- visual_focus
- detail_notes

Then deterministically compile the final image prompt from:

- template preset
- deck-level master style brief
- page intent

Show the result to the user and allow adjustments.
Do not continue until `prompts_approved=true`.

## Step 5: Render Slide Images

Call the chosen image model to render one image per slide.

Keep these fixed across the deck:

- 16:9 aspect ratio
- target resolution
- style family
- hierarchy and spacing rhythm

## Step 6: Assemble PPTX

Take the rendered images and place each image on its own slide.
Use a deterministic slide size and full-slide placement.
Save the resulting `.pptx` file to the requested output path.
