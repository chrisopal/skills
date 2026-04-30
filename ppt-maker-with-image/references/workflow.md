# Workflow

## Stage 0: Confirm Input Completeness

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

## Stage 1: Generate Master Style

Generate or load the deck-level master style brief first.

Expected output:

- visual positioning
- deck voice
- palette and typography rules
- reusable layout patterns
- forbidden elements
- prompt block for downstream rendering

Write the result to `artifacts/master_style.json`.
This stage can reuse `job.master_style` when it already exists.

## Stage 2: Generate Deck Outline

Generate the whole deck outline in one pass.

Expected output:

- storyline summary
- page-by-page outline
- each slide's purpose
- suggested layout type

Show the outline to the user and allow adjustments.
Write the result to `artifacts/outline.json`.
This stage can reuse the legacy `job.outline` field.
Approval flags:
- `--auto-approve-outline` (compatible mode) or set `outline_approved=true`.

## Stage 2.5: Generate Page Intent

Generate deck- and page-level intent guidance used by slide-prompt synthesis.

Expected output:

- `global_intent`
- `slides[{page_no,intent,slide_role,key_blocks}]`

Write the result to `artifacts/page_intent.json`.

## Stage 3: Generate Per-Slide Prompts

Generate prompts for every slide in one pass.

Each slide prompt should combine:

- deck-level style
- `style_header` injected by the pipeline
- page-specific intent guidance
- slide role in the storyline
- slide-specific blocks and emphasis

Let the user edit prompts before rendering.
Write the result to `artifacts/slide_prompts.json`.
This stage can reuse the legacy `job.slides` field.
Approval flags:
- `--auto-approve-prompts` (compatible mode) or set `prompts_approved=true`.

## Stage 4: Render Slide Images

Call the chosen image model to render one image per slide.
Use `--dry-run` for deterministic placeholder generation.

Keep these fixed across the deck:

- 16:9 aspect ratio
- target resolution
- style family
- hierarchy and spacing rhythm
Default outputs are `artifacts/images/slide_XX.png`.

## Stage 5: Assemble PPTX

Take the rendered images and place each image on its own slide.
Use a deterministic slide size and full-slide placement.
Save the resulting `.pptx` file to the requested output path.
Default: `artifacts/deck.pptx`.

Use `python scripts/review_job_status.py path/to/job.json` to inspect `master_style.json`, `outline.json`, `page_intent.json`, `slide_prompts.json`, `images/`, and `manifest.json` before continuing.
