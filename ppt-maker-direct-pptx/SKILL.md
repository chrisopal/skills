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
5. Synthesize page-generation specs from the confirmed page intents and deck-level master style.
6. Generate one page-level PptxGenJS module per slide, validate the modules, and compile them into a `.pptx` file.

Read [references/workflow.md](./references/workflow.md) first.
Read [references/conversational-mode.md](./references/conversational-mode.md) when running the workflow directly in chat without `job.json`.
Read [references/prompt-templates.md](./references/prompt-templates.md) when drafting requirement checks, template recommendation, outline prompts, and page-intent prompts.
Read [references/model-config.md](./references/model-config.md) when choosing or wiring model roles.
Read [references/template-presets.md](./references/template-presets.md) when the user asks for a named template style such as `慧新`.
Read [references/byo-llm-providers.md](./references/byo-llm-providers.md) when configuring the skill against any OpenAI-compatible endpoint (OpenAI / Azure / OpenRouter / Groq / Together / DeepSeek / vLLM / Ollama / LiteLLM proxy).
Read [references/v2-flow.md](./references/v2-flow.md) for the seven-gate v2 orchestration (run_ppt_job_v2.py, custom styles, pattern library, automated lint, page state machine).
Read [references/state-machines.md](./references/state-machines.md) when working with page-level status transitions or image placeholder lifecycle.
Read [references/lint-rules.md](./references/lint-rules.md) for the catalog of every lint rule, severity, and auto-fix capability.

## Modes

This skill supports two modes:

- Conversational mode:
  ask for missing fields, recommend a template if needed, confirm outline, confirm page intents, and only then draw the deck.
  Use `references/conversational-mode.md`; do not rely on `references/prompt-templates.md` script parsing sections as the only guidance.
- `job.json` mode:
  the script workflow keeps the same confirmation gates through explicit flags and structured artifacts.

## Required Inputs

For multi-slide generation, the workflow must not continue until all of these are complete:

- `topic`
- `target_audience` / 目标客户
- `purpose`
- `style`
- `page_count`
- `key_points` / 重点内容

The first version also requires:

- `requirement_confirmed = true`
- a confirmed template selection through `template_id/template_name`, or a style value that exactly matches a known preset

If no concrete template is selected, the skill may recommend one, but it must stop and wait for confirmation.

Before first live use, remind the user to configure:

- `LLM_API_KEY` (or legacy `OPENROUTER_API_KEY`)
- `LLM_BASE_URL` (or legacy `OPENROUTER_BASE_URL`); examples: `https://api.openai.com/v1`, `https://openrouter.ai/api/v1`, `https://api.groq.com/openai/v1`, `http://localhost:11434/v1`
- `assets/model_config.yaml` model ids: `text_model`, `pptx_js_model`, and optional `image_model`
- See [references/byo-llm-providers.md](./references/byo-llm-providers.md) for ready-to-paste configs per provider

Conversational mode must explicitly confirm target customer, style, page count, and key points before generating the outline.
It must explicitly ask the user to confirm the outline before slide prompts.
It must explicitly ask the user to confirm every page's content prompt/page intent before rendering.

## Structured Page Intents

The default editable per-slide object is a structured page intent, not a freeform final prompt.

Each slide should be represented using:

- `page_no`
- `title`
- `subtitle`
- `page_goal`
- `layout_type`
- `key_blocks`
- `image_placeholders`
- `visual_focus`
- `detail_notes`
- `page_position`
- `core_message`
- `copy_content`
- `layout_design`
- `visual_elements`
- `image_placeholder_advice`
- `chart_advice`
- `speaker_notes`
- `final_generation_prompt`
- `compiled_prompt`

Users should mainly edit the structured fields. The system recompiles `compiled_prompt` from:

- template preset
- deck-level master style brief
- page intent

`slide_prompts.json` must also include a top-level `quality_checklist` covering:

- outline coverage
- logic gaps
- one core message per page
- duplicate pages
- missing customer data/assets
- image placeholder executability
- chart data-field clarity
- style consistency
- audience/scenario fit
- readiness for PPT generation

The final drawing stage does not use image generation. It uses:

- `master_style.json`
- `slide_prompts.json`
- `slide_specs.json`
- `image_manifest.json` when generated image assets are used
- `slides/slide-XX.js`
- `slides/compile.js`

to directly render native PowerPoint objects.

## Direct PPT Rendering Rules

- Draw slides as editable PowerPoint-native text boxes, rounded rectangles, lines, connectors, KPI cards, matrices, timelines, and architecture bands.
- Generate page-specific PptxGenJS modules instead of using one generic layout for all pages.
- Every page module must export synchronous `createSlide(pres, theme)` and pass local validation before compile.
- Page modules must not use `require()`/`import`, `PptxGenJS.ShapeType`, `pptxgen.ShapeType`, or `pres.ShapeType`; use shape strings such as `'rect'` and `'roundRect'`.
- Validation must actually instantiate a temporary presentation and call `createSlide()` so invalid model-generated JS is repaired before final compile.
- Keep the output consistent in aspect ratio, typography scale, and layout rhythm.
- Avoid stray microcopy, random corner labels, template names, page numbers, and decorative edge text unless explicitly requested.
- Prefer a few large content modules over many tiny fragments.
- Treat `page_goal`, `visual_focus`, and `detail_notes` as invisible guidance, not visible slide copy.
- Text hierarchy has priority inside every module: reserve a distinct title zone and body zone, and never let body bullets start on top of the title.
- Do not render full bullet lists inside tiny chips or cards below 1.0 inch high; use larger cards, grid/matrix layouts, or fewer visible bullets.
- Use `image_placeholders` when a slide needs a product visual, scenario image, architecture visual, or generated diagram.
- If image assets exist, embed them with `slide.addImage`; otherwise render a clean editable placeholder frame.
- Treat every image placeholder as a reserved layout region, not a floating decoration.
- When image regions exist, constrain all non-title text, cards, charts, timelines, and architecture rows to `layout_regions.content`; place images only in `layout_regions.images`.
- Generated page modules for image-aware slides must define `slideConfig.contentRegion` and `slideConfig.images`, or validation should fail and trigger repair.

## PPTX Assembly

For the end-to-end semi-automatic run, use:

- `python scripts/run_ppt_job.py path/to/job.json`

This script writes intermediate files for review:

- `master_style.json`
- `outline.json`
- `slide_prompts.json`
- `slide_specs.json`
- `slides/slide-01.js`
- `slides/compile.js`

The script must stop at these confirmation gates unless explicitly approved:

- requirement confirmation
- template confirmation
- outline confirmation
- slide prompt confirmation

If you manually edit intermediate files and want to sync them back into `job.json`, use:

- `python scripts/sync_job_artifacts.py path/to/job.json --approve-outline --approve-prompts`

If you want to regenerate only one slide after feedback, use:

- `python scripts/regenerate_single_slide.py path/to/job.json --page-no 3 --instruction "把这一页做得更像双栏对照"`

If you want to generate images for slide placeholders and update `slide_specs.json`, use:

- `python scripts/generate_image_assets.py --slide-specs artifacts/slide_specs.json --master-style artifacts/master_style.json`

For local layout testing without calling an image model, add:

- `--dry-run`

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

If you manually edited artifacts and want schema-style validation, use:

- `python scripts/validate_job.py path/to/job.json --artifacts path/to/artifacts`

`review_job_status.py` also reports artifact schema issues.

The job template, model config, template preset, and Python dependency list live in:

- `assets/ppt_job_template.json`
- `assets/single_slide_job_template.json`
- `assets/model_config.yaml`
- `assets/template_manifest.json`
- `assets/schemas/outline.schema.json`
- `assets/schemas/slide_prompts.schema.json`
- `assets/schemas/slide_specs.schema.json`
- `assets/huixin_master_style_brief.json`
- `assets/python_requirements.txt`

Template variants are registered in `assets/template_manifest.json`. A template entry must provide `template_id`, `aliases`, `preset_asset`, and `brief_asset`.

Runtime behavior:

- scripts perform a Node/npm/model-key preflight before live runs
- JS generation failure prints a warning and falls back to deterministic editable PptxGenJS layouts
- image generation failure prints a warning, writes a local placeholder PNG, and records `fallback_reason`

## Output Expectations

Optimize for:

- complete upfront requirement confirmation
- coherent outline
- strong template recommendation before outline generation
- stable deck-wide visual consistency
- structured page-intent editing before rendering
- deterministic compiled prompt generation from master style
- deterministic slide-spec synthesis from page intents
- optional image-placeholder tooling for pages that need generated visuals
- explicit non-overlap layout regions for image assets and text modules
- deterministic direct PPTX rendering with editable native objects
