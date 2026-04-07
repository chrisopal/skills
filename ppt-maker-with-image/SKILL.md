---
name: ppt-maker-with-image
description: Reusable image-first PPTX generation skill. Use when Codex needs a repeatable workflow to collect complete presentation requirements, confirm style and audience, generate a deck outline with an LLM, generate per-slide image prompts for review, call an image model to render slides, and assemble the final images into a PPTX file.
---

# PPT Maker With Image

Use this skill as a generic five-step workflow for generating PPTX decks from requirements plus image-rendered slides.

## Trigger Example

- `使用 $ppt-maker-with-image 帮我做一套面向制造企业客户汇报的图片化 PPT。`
- `使用 $ppt-maker-with-image 先确认需求，再生成大纲、逐页提示词和最终 pptx。`

## Workflow

Follow this sequence unless the user explicitly narrows scope:

1. Confirm the requirement input is complete.
2. Generate a deck outline and get user confirmation.
3. Generate per-slide prompts and allow user edits.
4. Call an image model to generate slide images.
5. Assemble the generated images into a `.pptx` file and save it.

Read [references/workflow.md](./references/workflow.md) first.
Read [references/prompt-templates.md](./references/prompt-templates.md) when drafting requirement checks, outline prompts, and slide prompts.
Read [references/model-config.md](./references/model-config.md) when choosing or wiring model roles.
Read [references/template-presets.md](./references/template-presets.md) when the user asks for a named template style such as `慧新`.

## Inputs To Confirm

Never jump straight to slide generation if these inputs are still ambiguous:

- topic
- target audience
- purpose or usage scenario
- visual style
- page count
- key points or must-cover sections
- any hard constraints such as brand colors, logo usage, language, or deadline

If some fields are missing, ask only for the minimum missing information needed to produce a stable deck.

## Outline Rules

- Generate the whole deck outline in one pass.
- Make the outline coherent, ordered, and suitable for the requested audience.
- Keep page count aligned to the user request.
- Present the outline for confirmation before generating per-slide prompts.

## Slide Prompt Rules

- Generate prompts for all slides in one pass to keep consistency.
- Each slide prompt must reflect:
  - the global style
  - the deck narrative role of the slide
  - the slide-specific content blocks
- Let the user review and adjust prompts before image generation.
- When regenerating a single slide, preserve the same deck-level style constraints.
- If the user selects a named preset template, inject the preset's style block into every slide prompt.

## Image Generation Rules

- Generate full-slide images, not backgrounds only.
- Keep the output consistent in aspect ratio, typography scale, and layout rhythm.
- Avoid stray microcopy, extra page furniture, or random corner labels unless explicitly requested.
- Prefer a few large content modules over many tiny visual fragments.

## PPTX Assembly

For the end-to-end semi-automatic run, use:

- `python scripts/run_ppt_job.py path/to/job.json`

This script writes intermediate files for review:

- `master_style.json`
- `outline.json`
- `slide_prompts.json`
- `images/*.png`

By default it stops after outline generation and prompt generation so the user can review and edit.
Use `outline_approved` and `prompts_approved` in `job.json`, or pass `--auto-approve-outline` and `--auto-approve-prompts`, to continue.

If you manually edit intermediate files and want to sync them back into `job.json`, use:

- `python scripts/sync_job_artifacts.py path/to/job.json --approve-outline --approve-prompts`

If you want to regenerate only one slide after feedback, use:

- `python scripts/regenerate_single_slide.py path/to/job.json --page-no 3 --instruction "把这一页做得更像双栏对照" `

If you want to inspect the current stage, missing artifacts, and recommended next command, use:

- `python scripts/review_job_status.py path/to/job.json`

If you want to generate a single-slide PPT directly from one prompt, use:

- `python scripts/render_single_slide_ppt.py --prompt "这里写单页PPT提示词" --template-id huixin --title "单页方案页"`

If you prefer a structured single-slide task file, use:

- `python scripts/render_single_slide_ppt.py --job assets/single_slide_job_template.json`

For direct PPTX assembly, use:

- `python scripts/assemble_pptx.py --images slide1.png slide2.png --output output.pptx`

If the images need preprocessing or naming validation, use:

- `python scripts/validate_job.py path/to/job.json`

The job template, model config, template preset, and Python dependency list live in:

- `assets/ppt_job_template.json`
- `assets/single_slide_job_template.json`
- `assets/model_config.yaml`
- `assets/huixin_master_style_brief.json`
- `assets/python_requirements.txt`

## Output Expectations

Optimize for:

- complete upfront requirement confirmation
- coherent outline
- stable deck-wide visual consistency
- editable prompt-review step before rendering
- deterministic PPTX assembly from rendered images
