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

## Step 5: Build Slide Specs

Transform the confirmed page intents into deterministic slide specs.

Each slide spec should contain:

- layout family
- visible content modules
- section hierarchy
- emphasis roles
- any KPI / roadmap / matrix / architecture layer structure

## Step 6: Directly Draw PPTX

Use deterministic Python rendering to draw each slide directly as native PowerPoint objects.
Prefer editable text boxes, rounded rectangles, cards, dividers, connectors, KPI strips, timelines, and architecture layers.
Save the resulting `.pptx` file to the requested output path.
