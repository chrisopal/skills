# Conversational Mode Guide

Use this guide when running the skill directly in chat instead of through `run_ppt_job.py`.
These prompts are for the main agent to follow and summarize naturally; they are not parsed by scripts.

## 1. Requirement Confirmation

Collect these fields before outlining:

- topic
- target customer / target audience
- purpose or scenario
- preferred style
- page count
- key points
- must-have sections
- hard constraints such as language, brand colors, logo, data, or forbidden content

Confirm the result as a short requirement summary. Do not continue until the user confirms or corrects it.
The confirmation must explicitly name the target customer, style, page count, and key points.

## 2. Template Confirmation

Recommend one concrete template from `assets/template_manifest.json`.
Use the template `style_summary` and the user's purpose, audience, language, and style constraints.

Default recommendations:

- `huixin`: Chinese general consulting or business decks.
- `huixin-product-solution`: Chinese product, capability, architecture, or solution decks.
- `huixin-market-promo`: Chinese marketing, launch, brand, or campaign decks.
- `huixin-internal-meeting`: Chinese internal review, project sync, action tracking, or management meeting decks.
- `dark-english-business`: English, global, investor, executive, board, or dark-mode business decks.

State the template id, template name, and reason. Do not continue until the user accepts or chooses a different template.

## 3. Outline Confirmation

Generate the whole deck outline in one pass with exactly the confirmed page count.
Each slide should include:

- page number
- title
- subtitle
- purpose
- layout type
- key blocks
- image placeholders only when the slide truly needs a product visual, scenario image, architecture visual, or diagram

Show the outline in a compact page-by-page list. Do not continue until the user confirms or edits it.
Treat this as a hard gate: do not generate page prompts until the user confirms the outline.

## 4. Page Intent Confirmation

Generate structured page intents for every slide.
Each intent should include:

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

Keep visible slide copy separate from invisible design guidance.
Show the user the structured intents or a concise review table before rendering.
Treat this as a hard gate: do not render the PPTX until the user confirms every page's content prompt/page intent.
If the user edits one page, update that page and re-show the affected prompt before rendering.

## 5. Rendering And Fallback Expectations

When rendering:

- Use confirmed `master_style`, `slide_prompts`, and `slide_specs`.
- If live JS generation fails after repair attempts, the renderer falls back to deterministic editable layouts and prints a warning.
- If live image generation fails, the image tool falls back to a local placeholder PNG and records `fallback_reason` in `image_manifest.json` and `slide_specs.json`.
- Run `validate_job.py` and `review_job_status.py` when artifacts are manually edited.

Keep warnings visible in the final report so users know which pages used fallback behavior.
