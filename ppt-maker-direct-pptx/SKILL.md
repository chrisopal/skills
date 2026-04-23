---
name: ppt-maker-direct-pptx
description: Reusable confirmation-first direct PPTX generation skill. Use when Codex needs a repeatable workflow to collect complete presentation requirements, confirm audience/style/template/page-count first, generate and confirm a deck outline, generate and confirm structured per-slide page intents, compile consistent deck-level rendering briefs, and directly draw each slide as editable PowerPoint-native objects into a PPTX file.
---

# PPT Maker Direct PPTX

Use this skill as a confirmation-first workflow for generating editable PPTX decks directly from requirements, without rendering slide images first.

## Trigger Example

- `使用 $ppt-maker-direct-pptx 帮我做一套面向制造企业客户汇报的可编辑 PPT。`
- `使用 $ppt-maker-direct-pptx 先确认需求，再确认大纲和每页页面意图，最后直接绘制 pptx。`

## Workflow

Follow this sequence unless the user explicitly narrows scope:

1. Confirm the requirement input is complete.
2. Recommend and confirm a concrete template when needed.
3. Generate a deck outline and get user confirmation.
4. Generate structured per-slide page intents and compiled rendering briefs, then get user confirmation.
5. Synthesize deterministic slide specs from the confirmed page intents and deck-level master style.
6. Directly draw each slide as editable PowerPoint-native shapes and text into a `.pptx` file.

Read [references/workflow.md](./references/workflow.md) first.
Read [references/prompt-templates.md](./references/prompt-templates.md) when drafting requirement checks, template recommendation, outline prompts, and page-intent prompts.
Read [references/model-config.md](./references/model-config.md) when choosing or wiring model roles.
Read [references/template-presets.md](./references/template-presets.md) when the user asks for a named template style such as `慧新`.

## Modes

This skill supports two modes:

- Conversational mode:
  ask for missing fields, recommend a template if needed, confirm outline, confirm page intents, and only then draw the deck.
- `job.json` mode:
  the script workflow keeps the same confirmation gates through explicit flags and structured artifacts.

## Required Inputs

For multi-slide generation, the workflow must not continue until all of these are complete:

- `topic`
- `target_audience`
- `purpose`
- `style`
- `page_count`

The first version also requires:

- `requirement_confirmed = true`
- a confirmed template selection through `template_id/template_name`, or a style value that exactly matches a known preset

If no concrete template is selected, the skill may recommend one, but it must stop and wait for confirmation.

## Structured Page Intents

The default editable per-slide object is a structured page intent, not a freeform final prompt.

Each slide should be represented using:

- `page_no`
- `title`
- `subtitle`
- `page_goal`
- `layout_type`
- `key_blocks`
- `visual_focus`
- `detail_notes`
- `compiled_prompt`

Users should mainly edit the structured fields. The system recompiles `compiled_prompt` from:

- template preset
- deck-level master style brief
- page intent

The final drawing stage does not use image generation. It uses:

- `master_style.json`
- `slide_prompts.json`
- `slide_specs.json`

to directly render native PowerPoint objects.

## Direct PPT Rendering Rules

- Draw slides as editable PowerPoint-native text boxes, rounded rectangles, lines, connectors, KPI cards, matrices, timelines, and architecture bands.
- Keep the output consistent in aspect ratio, typography scale, and layout rhythm.
- Avoid stray microcopy, random corner labels, template names, page numbers, and decorative edge text unless explicitly requested.
- Prefer a few large content modules over many tiny fragments.
- Treat `page_goal`, `visual_focus`, and `detail_notes` as invisible guidance, not visible slide copy.

## PPTX Assembly

For the end-to-end semi-automatic run, use:

- `python scripts/run_ppt_job.py path/to/job.json`

This script writes intermediate files for review:

- `master_style.json`
- `outline.json`
- `slide_prompts.json`
- `slide_specs.json`

The script must stop at these confirmation gates unless explicitly approved:

- requirement confirmation
- template confirmation
- outline confirmation
- slide prompt confirmation

If you manually edit intermediate files and want to sync them back into `job.json`, use:

- `python scripts/sync_job_artifacts.py path/to/job.json --approve-outline --approve-prompts`

If you want to regenerate only one slide after feedback, use:

- `python scripts/regenerate_single_slide.py path/to/job.json --page-no 3 --instruction "把这一页做得更像双栏对照"`

If you want to inspect the current stage, missing artifacts, and recommended next command, use:

- `python scripts/review_job_status.py path/to/job.json`

If you want to generate a single-slide PPT directly from one prompt, use:

- `python scripts/render_single_slide_ppt.py --prompt "这里写单页PPT提示词" --template-id huixin --title "单页方案页"`

Single-slide mode remains a fast path, but when a template is specified it still injects the corresponding template prompt block and master style constraints before direct rendering.

If you prefer a structured single-slide task file, use:

- `python scripts/render_single_slide_ppt.py --job assets/single_slide_job_template.json`

For direct PPTX assembly from generated specs, use:

- `python scripts/assemble_pptx.py --slide-specs slide_specs.json --master-style master_style.json --output output.pptx`

If the job needs validation before running, use:

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
- strong template recommendation before outline generation
- stable deck-wide visual consistency
- structured page-intent editing before rendering
- deterministic compiled prompt generation from master style
- deterministic slide-spec synthesis from page intents
- deterministic direct PPTX rendering with editable native objects
