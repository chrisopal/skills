# Workflow

## Step 1: Confirm Input Completeness

Collect or confirm:

- topic
- audience
- scenario or purpose
- style direction
- page count
- key messages
- must-have sections
- branding constraints

Do not proceed until the deck can be outlined with confidence.

## Step 2: Generate Deck Outline

Generate the whole deck outline in one pass.

Expected output:

- storyline summary
- page-by-page outline
- each slide's purpose
- suggested layout type

Show the outline to the user and allow adjustments.

## Step 3: Generate Per-Slide Prompts

Generate prompts for every slide in one pass.

Each slide prompt should combine:

- deck-level style
- slide role in the storyline
- slide-specific blocks and emphasis

Let the user edit prompts before rendering.

## Step 4: Render Slide Images

Call the chosen image model to render one image per slide.

Keep these fixed across the deck:

- 16:9 aspect ratio
- target resolution
- style family
- hierarchy and spacing rhythm

## Step 5: Assemble PPTX

Take the rendered images and place each image on its own slide.
Use a deterministic slide size and full-slide placement.
Save the resulting `.pptx` file to the requested output path.
