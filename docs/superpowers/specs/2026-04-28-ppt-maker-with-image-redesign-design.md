# ppt-maker-with-image Redesign — Executable Design (Approved)

Date: 2026-04-28
Author: Brainstorming session (confirmed)
Status: approved, implementation-ready

## 1) Confirmed Scope and Outcome

We confirmed the redesign direction and execution order from:

- Global visual consistency across slides
- Better content grounding via source-material-aware page intent
- Provider-universal LLM layer for text + image generation with pluggable image adapters

Accepted execution order (final):

1. Stage 1 — LLM Universalization
2. Stage 2 — Style Consistency
3. Stage 3 — Content Refinement

This order is kept to unblock dependency stabilization first, then enforce deterministic visual constraints, and finally enrich content structure.

## 2) Closed-loop Clarifications Incorporated

- **Stage numbering一致性**
  - Use one canonical naming: `Stage 1 (LLM)`, `Stage 2 (Style)`, `Stage 3 (Content)`.
- **回归兼容定义**
  - `review_mode` replaces `outline_approved` / `prompts_approved` as canonical control flags.
  - Existing fields are accepted during migration period only if present, but new logic prefers `review_mode`.
- **降级行为显式化**
  - Missing/unsupported provider features are logged in `manifest.json` with `provider_capabilities` and one-time warning behavior for each run.
  - `source_materials` can be empty; in that case numeric/content constraints are relaxed to allow illustrative generation.

## 3) Architecture (restate)

Inputs: `job.json`

Pipeline outputs on disk as JSON artifacts:

- `master_style.json`
- `outline.json`
- `page_intent.json`
- `slide_prompts.json`
- `images/slide_XX.png`
- `deck.pptx`
- `manifest.json`

New major modules:

- `scripts/llm/` (text via LiteLLM; image via per-provider adapter)
- `scripts/style/header.py` (deterministic style prompt header)
- `scripts/pipeline/*` (pure stage modules with file-based I/O)
- `scripts/run_ppt_job.py` becomes orchestrator, `review_mode`-driven

## 4) Executable Implementation Plan

### Phase A — Foundation (Stage 1): Provider Universalization

Goal: unify text calls through LiteLLM and introduce image provider adapter abstraction.

#### A.1 Files

- Add: `ppt-maker-with-image/scripts/llm/__init__.py`
- Add: `ppt-maker-with-image/scripts/llm/config.py`
- Add: `ppt-maker-with-image/scripts/llm/text.py`
- Add: `ppt-maker-with-image/scripts/llm/image/__init__.py`
- Add: `ppt-maker-with-image/scripts/llm/image/base.py`
- Add: `ppt-maker-with-image/scripts/llm/image/openrouter.py`
- Add: `ppt-maker-with-image/scripts/llm/image/openai.py`
- Add: `ppt-maker-with-image/scripts/llm/image/gemini.py`
- Add: `ppt-maker-with-image/scripts/llm/errors.py`
- Update: `ppt-maker-with-image/scripts/run_ppt_job.py`
- Update: `ppt-maker-with-image/scripts/regenerate_single_slide.py`
- Update: `ppt-maker-with-image/scripts/render_single_slide_ppt.py`
- Update: `ppt-maker-with-image/assets/model_config.yaml`
- Update: `ppt-maker-with-image/assets/python_requirements.txt`

#### A.2 Behavior

- `text_model` supports: OpenAI, Anthropic, OpenRouter, Ollama, Azure OpenAI.
- `image_model` supports: OpenRouter, OpenAI `gpt-image-2`, Gemini.
- `ImageProvider` contract remains `render(prompt, aspect_ratio, resolution, seed=None, reference_images=None)`.
- Unsupported provider features are downgraded with clear warning and non-fatal continuation.

#### A.3 Acceptance Criteria

- Running a dry-run executes all pipeline stages without external API calls.
- A real dry-run-free example succeeds with one non-OpenRouter text model and one non-OpenRouter image model by config-only change.

---

### Phase B — Visual Consistency (Stage 2)

Goal: guarantee stable deck-wide style boundaries and optional cross-slide reference stabilization.

#### B.1 Files

- Add: `ppt-maker-with-image/scripts/style/header.py`
- Add: `ppt-maker-with-image/scripts/pipeline/stage_master_style.py`
- Add: `ppt-maker-with-image/scripts/pipeline/stage_outline.py`
- Add: `ppt-maker-with-image/scripts/pipeline/stage_slide_prompts.py`
- Add: `ppt-maker-with-image/scripts/pipeline/stage_render.py`
- Add: `ppt-maker-with-image/scripts/pipeline/stage_assemble.py`
- Add: `ppt-maker-with-image/scripts/pipeline/stage_page_intent.py` (introduced in Stage 3 but placed in shared pipeline folder for ordering)
- Add: `ppt-maker-with-image/scripts/pipeline/__init__.py`
- Add: `ppt-maker-with-image/scripts/pipeline/manifest.py` for seed + capabilities logging
- Update: `ppt-maker-with-image/references/prompt-templates.md`
- Update: `ppt-maker-with-image/references/workflow.md`

#### B.2 Behavior

- `STYLE_HEADER = render(master_style)` is prepended to every slide prompt.
- `master_style` fields become authoritative constants (colors/spacing/sizing/rules).
- `consistency.use_reference_image=true` makes slide 2..N reference slide_01 image when provider supports.
- Reference is disabled for slide_1 and during any single-slide regeneration.

#### B.3 Acceptance Criteria

- For same input, slide prompts are structurally identical except page-specific content blocks.
- Generated manifests include deterministic `seed` and `provider_capabilities`.
- Drift review can be performed by one run with reference off/on and manual diff.

---

### Phase C — Content Refinement (Stage 3)

Goal: replace weak `key_blocks` prompts with `page_intent`-driven content structure.

#### C.1 Files

- Add: `ppt-maker-with-image/scripts/pipeline/stage_page_intent.py`
- Add: `ppt-maker-with-image/scripts/lib/source_materials.py` (file/text/data loader)
- Update: `ppt-maker-with-image/scripts/run_ppt_job.py` (review_mode `full/fast/auto` wiring)
- Update: `ppt-maker-with-image/scripts/sync_job_artifacts.py`
- Update: `ppt-maker-with-image/scripts/review_job_status.py`
- Update: `ppt-maker-with-image/scripts/validate_job.py`
- Update: `ppt-maker-with-image/assets/ppt_job_template.json`
- Update: `ppt-maker-with-image/assets/single_slide_job_template.json`
- Update: `ppt-maker-with-image/assets/example-job.json`

#### C.2 Behavior

- Introduce `source_materials` loader for `text|file|data` items.
- Generate `page_intent.json` after outline in `full` mode.
- Generate `slide_prompts.json` from prompt template `CONTENT_BLOCK + STYLE_HEADER`.
- `review_mode` semantics:
  - `full`: stop after outline, then after page_intent, then after slide prompts.
  - `fast`: stop only after outline.
  - `auto`: no pauses.

#### C.3 Acceptance Criteria

- If `source_materials` exists, generated `page_intent` evidence fields are non-empty and traceable.
- If `source_materials` is empty, generation still completes with no hard-fail on missing evidence.
- `review_mode` stops exactly at configured points.

---

### Phase D — Orchestration and Compatibility

#### D.1 Files

- Update: `ppt-maker-with-image/scripts/run_ppt_job.py` (orchestrator rewrite)
- Update: `ppt-maker-with-image/scripts/review_job_status.py`
- Update: `ppt-maker-with-image/README.md`
- Update: `ppt-maker-with-image/SKILL.md`
- Update: `ppt-maker-with-image/references/model-config.md`

#### D.2 Behavior

- CLI flags remain stable where possible; `--auto-approve-*` becomes optional compatibility aliases to `review_mode=auto` and should not block migration.
- `--dry-run` remains supported end-to-end with placeholders.
- New fields added in `job.json` are optional when defaults exist.

#### D.3 Acceptance Criteria

- Existing README workflow examples remain runnable.
- New docs describe env-var requirements for all supported providers.

---

## 5) Risks and Mitigations (Finalized)

1. **JSON-mode instability for some providers**
   - Mitigation: one retry + tolerant parser fallback in `scripts/llm/text.py`.
2. **Adapter response shape mismatch**
   - Mitigation: per-adapter normalization to plain prompt bytes for images.
3. **Reference-image cost/cadence**
   - Mitigation: default `use_reference_image=false`; per-job opt-in only.
4. **Schema drift across manual edits**
   - Mitigation: each stage writes explicit stage artifacts, and sync supports per-stage back-propagation.

## 6) Definition of Done

A phase is done only if:

- Its artifact files are generated correctly (or intentionally placeholder-dry-run equivalents).
- Stage stop points in `review_mode` are respected.
- Core command paths in README are verified by docs examples and manual smoke checks.
- No unresolved placeholders (`TBD`, `TODO`, ambiguous schema terms) remain in this spec.

