# ppt-maker-with-image Redesign Design

Date: 2026-04-27
Author: brainstorm session
Status: approved, ready for implementation

## Goals

1. **Global visual consistency** — eliminate page-to-page drift in colors, typography, spacing, and layout rhythm.
2. **Per-page content refinement** — replace shallow `key_blocks` tags with structured page intent grounded in user-supplied source materials.
3. **Provider universality** — remove the OpenRouter-only lock-in so the same workflow can run against OpenAI, Anthropic, Azure, Ollama, OpenRouter (text) and OpenAI, OpenRouter, Google Gemini (image).

Stages will land in order **3 → 1 → 2** (LLM universalization first as the foundation, then consistency, then content refinement). Each stage merges independently.

## Non-Goals

- Backwards compatibility with existing `job.json` schema. Old example files will be rewritten in place; no migration script.
- Post-render vision-LLM consistency check (Q6 option D). May land later.
- Per-page two-pass content refinement (Q8 option C). May land later.
- New named template presets beyond `huixin`.

---

## 1. Architecture Overview

```
job.json
   │
   ├─ Stage A: requirement normalization + master_style generation
   ▼
master_style.json              ← visual contract (literal hex / px / forbidden)
   │
   ├─ Stage B: outline generation (single pass)
   ▼
outline.json                   ← review stop #1 (full / fast)
   │
   ├─ Stage C: page_intent generation (grounded in source_materials)
   ▼
page_intent.json               ← review stop #2 (full only)
   │
   ├─ Stage D: image_prompt assembly = STYLE_HEADER + CONTENT_BLOCK
   ▼
slide_prompts.json             ← review stop #3 (full only)
   │
   ├─ Stage E: image rendering (deterministic prompt header + optional first-frame reference)
   ▼
images/*.png
   │
   ├─ Stage F: PPTX assembly
   ▼
deck.pptx
```

Three new abstractions:

- **`scripts/llm/`** — text via LiteLLM, image via per-provider adapters.
- **`scripts/style/header.py`** — deterministic master_style → STYLE_HEADER renderer (no LLM).
- **`scripts/pipeline/`** — six stage modules; each stage is a pure function whose I/O is a JSON file on disk, so any single stage can be re-run independently.

`run_ppt_job.py` becomes a thin orchestrator that consults `review_mode` to decide which stages stop and which auto-continue.

---

## 2. Stage 1 — LLM Universalization

### 2.1 Approach

- **Text models**: LiteLLM (`litellm.completion(model="...")`) as the unified entry. Handles OpenAI, Anthropic, OpenRouter, Ollama, Azure OpenAI without per-provider code.
- **Image models**: custom `ImageProvider` abstraction. Image API surfaces vary too much across providers to delegate.

### 2.2 First-day Provider Coverage

| Role  | Providers                                                         |
|-------|-------------------------------------------------------------------|
| Text  | OpenAI, Anthropic, OpenRouter, Ollama (local), Azure OpenAI       |
| Image | OpenRouter (existing path), OpenAI `gpt-image-2`, Google Gemini   |

### 2.3 Config Schema

`provider/model` string convention is the default. Optional `providers:` block overrides base_url, api_key env var, etc. — used only for Azure / self-hosted / non-default env var names.

```yaml
text_model: "anthropic/claude-sonnet-4-6"
image_model: "openai/gpt-image-2"

providers:                                  # optional override block
  azure:
    base_url: "https://my-azure.openai.azure.com"
    api_key_env: "AZURE_OPENAI_KEY"
    api_version: "2024-10-21"
  ollama:
    base_url: "http://localhost:11434"

aspect_ratio: "16:9"
resolution: "3840x2160"
language: "zh-CN"
font_preferences:
  cjk: "Microsoft YaHei"
  latin: "Arial"
```

### 2.4 Directory Layout

```
scripts/llm/
├─ __init__.py
├─ config.py            # parse model_config.yaml, resolve overrides
├─ text.py              # LiteLLM wrapper: call_text(model, messages, json_mode=True)
├─ image/
│  ├─ __init__.py       # ImageProvider factory keyed on provider prefix
│  ├─ base.py           # ImageProvider abstract base
│  ├─ openrouter.py     # ports the existing chat-completions image path
│  ├─ openai.py         # uses OpenAI Images API with gpt-image-2
│  └─ gemini.py         # google-genai SDK
└─ errors.py            # UnsupportedFeatureError, ProviderError
```

### 2.5 ImageProvider Contract

```python
class ImageProvider:
    def render(
        self,
        prompt: str,
        *,
        aspect_ratio: str = "16:9",
        resolution: str = "3840x2160",
        seed: int | None = None,
        reference_images: list[bytes] | None = None,
    ) -> bytes: ...
```

- Adapters not supporting `reference_images` raise `UnsupportedFeatureError`; the caller catches and downgrades to A-only with a one-time warning.
- Adapters not supporting `seed` silently ignore the kwarg (we record this in adapter metadata so logs can explain reproducibility limits).

### 2.6 Dependencies

Add to `assets/python_requirements.txt`:

- `litellm>=1.51`
- `google-genai>=0.5`

Keep existing `httpx`, `pyyaml`, `pillow`, `python-pptx`.

---

## 3. Stage 2 — Style Consistency

### 3.1 Two Mechanisms

| Mechanism                          | Default | Why                                                         |
|------------------------------------|---------|-------------------------------------------------------------|
| **A. Deterministic STYLE_HEADER**  | always  | Pins literal hex / px values; LLM never rewrites them       |
| **B. First-frame reference image** | opt-in  | Visual anchor for slides 2..N when image provider supports it |

### 3.2 STYLE_HEADER Rendering (`scripts/style/header.py`)

Pure templated render of `master_style.json`. The header preserves:

- canvas / background / primary / secondary / neutral / text colors as exact hex
- font sizes as exact ranges (e.g., `36-44px, bold`)
- corner radius / stroke / shadow as exact px
- layout patterns from `module_layout_patterns`
- explicit forbidden list (no 3D charts, no dark backgrounds, no random corner labels, etc.)

Length target: 500–800 chars. The header is identical across every slide of a deck.

### 3.3 image_prompt Assembly

```
image_prompt = STYLE_HEADER + "\n\n=== 本页内容 ===\n" + CONTENT_BLOCK
```

The text LLM is constrained by its system prompt to produce only `CONTENT_BLOCK`. It may not write color values, font sizes, or visual style — those concerns belong exclusively to the deterministic header.

### 3.4 Reference Image (B)

`job.json`:

```json
"consistency": {
  "use_reference_image": false,
  "reference_source": "first_slide",
  "seed": null
}
```

- Slide 1 always renders without a reference.
- For slide N≥2, if `use_reference_image=true`, the rendered `slide_01.png` bytes are passed via `reference_images=[...]`.
- Provider mismatch → warn once, downgrade silently to A-only.
- During single-slide regeneration, the reference is **always** slide 1 (never the previous neighbor) so that drift cannot compound.

### 3.5 Seed Handling

- If `consistency.seed` is `null` at start, generate a random 32-bit int and write it into `output_dir/manifest.json`.
- Subsequent runs (regeneration, re-render) read the manifest to keep determinism.
- Adapters that don't support seed log this fact in the manifest under `provider_capabilities`.

---

## 4. Stage 3 — Content Refinement

### 4.1 New `page_intent.json`

```json
{
  "storyline": "...",
  "slides": [
    {
      "page_no": 3,
      "slide_role": "现状诊断的核心结论",
      "headline_copy": "三大瓶颈正在拉低培训转化率",
      "subheadline_copy": "基于 Q1 内部抽样 217 名学员的反馈",
      "narrative_hook": "如果不解,半年内ROI将再降12%",
      "modules": [
        {
          "name": "课程匹配度低",
          "one_liner": "现有课程与岗位能力图谱断层",
          "bullets": ["岗位能力维度覆盖率 47%", "学员主动复训率 12%"],
          "key_number": "47%",
          "icon_hint": "target-miss",
          "evidence_ref": "src_002"
        }
      ],
      "chart_spec": {
        "type": "bar",
        "data_points": [],
        "emphasis": "Q1 数据"
      },
      "layout_pattern": "顶部结论条 + 三模块横排"
    }
  ]
}
```

### 4.2 source_materials in `job.json`

```json
"source_materials": [
  { "id": "src_001", "type": "text", "content": "..." },
  { "id": "src_002", "type": "file", "path": "./materials/q1_survey.md" },
  { "id": "src_003", "type": "data", "content": {"jan": 102, "feb": 98} }
]
```

- `text` → inlined string.
- `file` → load local file (md / txt / json) and inline its text.
- `data` → JSON-stringify and inline.

When source_materials is present, the page_intent generation prompt requires every concrete number, name, or institution in `key_number` / `bullets` to come from source_materials and to cite its source via `evidence_ref`. When empty, evidence_ref may be blank and the LLM may invent illustrative content.

### 4.3 CONTENT_BLOCK Template

The text LLM produces CONTENT_BLOCK from page_intent using a deterministic template:

```
本页角色：{slide_role}
主标题：{headline_copy}
副标题：{subheadline_copy}
版式：{layout_pattern}
模块（按从左到右、从上到下）：
  1. {name} | {one_liner} | 关键数字：{key_number} | 图标：{icon_hint}
  2. ...
图表：{chart_spec}
观众记忆点：{narrative_hook}
```

LLM responsibility shrinks from "invent slide content" to "translate page_intent fields into prompt-ready phrasing".

---

## 5. New `job.json` Schema

```json
{
  "template_id": "huixin",
  "template_name": "慧新",
  "topic": "制造企业数字化培训落地方案",
  "target_audience": "制造企业业务负责人",
  "purpose": "客户汇报",
  "style": "慧新",
  "page_count": 8,
  "key_points": ["培训目标", "阶段路径", "能力建设", "实施保障"],
  "must_have_sections": ["现状", "方案", "路线图", "收益"],
  "constraints": {
    "brand_colors": ["#A8D86B", "#0F95B6"],
    "logo_required": false,
    "language": "zh-CN"
  },

  "source_materials": [
    { "id": "src_001", "type": "file", "path": "./materials/client-brief.md" }
  ],

  "consistency": {
    "use_reference_image": true,
    "reference_source": "first_slide",
    "seed": null
  },

  "review_mode": "full",

  "output": {
    "directory": "./artifacts",
    "pptx_filename": "deck.pptx"
  }
}
```

### 5.1 review_mode

| Mode   | outline stop | page_intent stop | slide_prompts stop |
|--------|:------------:|:----------------:|:------------------:|
| `full` | ✓            | ✓                | ✓                  |
| `fast` | ✓            | ✗                | ✗                  |
| `auto` | ✗            | ✗                | ✗                  |

CLI flags `--auto-approve-outline`, `--auto-approve-page-intent`, `--auto-approve-prompts` override per-stage.

### 5.2 Removed Fields

- `outline_approved`, `prompts_approved` — replaced by `review_mode`.
- `master_style` is still accepted as a power-user override but no longer required in normal flow.

### 5.3 Artifacts Layout

```
artifacts/
├─ manifest.json          # seed, provider info, timestamps, capability log
├─ master_style.json
├─ outline.json
├─ page_intent.json       # NEW
├─ slide_prompts.json
├─ images/
│  └─ slide_NN.png
└─ deck.pptx
```

---

## 6. Code Change Inventory

### 6.1 scripts/

```
scripts/
├─ llm/                              [NEW]
│  ├─ config.py
│  ├─ text.py
│  ├─ image/{base,openrouter,openai,gemini}.py
│  └─ errors.py
├─ style/header.py                   [NEW]
├─ pipeline/
│  ├─ stage_master_style.py          [NEW, extracted from run_ppt_job]
│  ├─ stage_outline.py               [NEW]
│  ├─ stage_page_intent.py           [NEW]
│  ├─ stage_slide_prompts.py         [NEW]
│  ├─ stage_render.py                [NEW]
│  └─ stage_assemble.py              [NEW]
├─ run_ppt_job.py                    [REWRITE → orchestrator]
├─ regenerate_single_slide.py        [REWRITE → uses ImageProvider, slide-1 reference]
├─ render_single_slide_ppt.py        [REWRITE → reuses new llm layer]
├─ sync_job_artifacts.py             [REWRITE → handles page_intent]
├─ review_job_status.py              [REWRITE → recognizes new artifacts]
├─ validate_job.py                   [REWRITE → new schema]
└─ assemble_pptx.py                  [unchanged]
```

### 6.2 assets/

```
assets/
├─ model_config.yaml                 [REWRITE → providers block]
├─ example-job.json                  [REWRITE → new schema]
├─ ppt_job_template.json             [REWRITE]
├─ single_slide_job_template.json    [REWRITE]
├─ python_requirements.txt           [add litellm, google-genai]
└─ huixin_master_style_brief.json    [unchanged]
```

### 6.3 references/

```
references/
├─ workflow.md                       [REWRITE → 6 stages + review_mode]
├─ model-config.md                   [REWRITE → provider/model strings, override block]
├─ prompt-templates.md               [add page_intent prompt; CONTENT_BLOCK rules]
└─ template-presets.md               [unchanged]
```

### 6.4 Top-level

- `SKILL.md` — rewrite workflow narrative, CLI list, artifacts list.
- `README.md` — rewrite install (env vars per provider), examples (Anthropic + OpenAI image quickstart).

---

## 7. Validation Strategy

1. Each stage module exposes a CLI entry: `python -m pipeline.stage_outline path/to/job.json`. Smoke-test each in isolation.
2. `--dry-run` is preserved end-to-end. Every stage produces deterministic placeholder output so CI runs zero-cost.
3. One real-money end-to-end run with `example-job.json` using **Anthropic for text + OpenAI gpt-image-2 for image** to confirm the new provider matrix works.
4. Visual consistency acceptance: render the same `example-job.json` with `use_reference_image=false` and `=true`; eyeball drift on slides 2..N.

## 8. Risk Register

- **LiteLLM JSON mode for Anthropic** is a prompt-level emulation; occasional malformed JSON. Mitigation: in `text.py`, wrap calls with one retry and a permissive JSON parse fallback.
- **Gemini direct vs OpenRouter response shapes** differ. Mitigation: each adapter normalizes to `bytes` itself.
- **`gpt-image-2` parameter surface** may not match `gpt-image-1` (seed support, reference image format). Mitigation: adapter records `provider_capabilities` at init time; unsupported kwargs are dropped + logged, not errored.
- **Reference image cost**: passing slide_01 to every subsequent slide multiplies token/image cost. Mitigation: `use_reference_image` is opt-in and documented.

## 9. Sequencing

Implementation order matches the stage numbering chosen in brainstorming:

1. **Phase 1 (foundation)** — Stage 1: LLM layer + new model_config schema. Cuts existing OpenRouter calls over to the new abstraction without changing the pipeline shape.
2. **Phase 2 (consistency)** — Stage 2: STYLE_HEADER + reference-image + manifest seed.
3. **Phase 3 (content)** — Stage 3: `page_intent` stage + source_materials loader + 3-stop review_mode.

Each phase ends with a working `run_ppt_job.py --dry-run` that exercises the full pipeline.

---

## 10. Open Items for Implementation Plan

To be resolved in `writing-plans`:

- Detailed file-level diff per phase
- Test fixtures (sample source_materials, fake provider responses)
- Exact LiteLLM model-string examples per provider
- Fallback behavior table when API keys for a configured provider are missing
