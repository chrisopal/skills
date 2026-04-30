# ppt-maker-with-image Visual Reference Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop image models from rendering layout measurement labels while adding opt-in first-slide reference image routing for stronger deck consistency.

**Architecture:** Keep visual constants in the deterministic `STYLE_HEADER`, but frame them as invisible rendering constraints and add hard negative instructions in the render wrapper. Extend the image provider contract with `seed`, `reference_images`, and capability metadata, then make `stage_render` read `job.consistency` and pass `slide_01.png` to slide 2..N only when enabled and supported.

**Tech Stack:** Python 3, pytest, Pillow, python-pptx, httpx, LiteLLM/OpenRouter image chat-completions.

---

## File Structure

- Modify: `ppt-maker-with-image/references/prompt-templates.md` — add invisible-design-constraint language to prompt generation and image render wrapper templates.
- Modify: `ppt-maker-with-image/scripts/style/header.py` — render `STYLE_HEADER` as a style contract with explicit "not visible slide copy" rules.
- Modify: `ppt-maker-with-image/scripts/pipeline/stage_slide_prompts.py` — avoid re-injecting visible style tokens when normalizing prompts.
- Modify: `ppt-maker-with-image/scripts/pipeline/stage_render.py` — read `job.consistency`, pass seed/reference bytes into `ImageRenderRequest`, and log reference fallback in manifest-compatible output.
- Modify: `ppt-maker-with-image/scripts/llm/image/base.py` — add seed/reference fields and provider capability properties.
- Modify: `ppt-maker-with-image/scripts/llm/image/openrouter.py` — support reference image payloads through multimodal chat content and keep timeout/retry behavior.
- Modify: `ppt-maker-with-image/scripts/llm/image/openai.py` — declare unsupported reference-image capability and keep existing generation path.
- Modify: `ppt-maker-with-image/scripts/llm/image/gemini.py` — declare unsupported reference-image capability for this pass unless its current adapter already accepts inline image parts.
- Modify: `ppt-maker-with-image/scripts/run_ppt_job.py` — record render-stage consistency metadata and stop before render when prompts are not approved.
- Modify: `ppt-maker-with-image/scripts/regenerate_single_slide.py` — use slide 1 as optional reference for rerendered slides when available.
- Test: `ppt-maker-with-image/tests/test_style_header.py`
- Test: `ppt-maker-with-image/tests/test_stage_render.py`
- Test: `ppt-maker-with-image/tests/test_llm_image_quality_fixes.py`
- Test: `ppt-maker-with-image/tests/test_run_ppt_job_reference_policy.py`

---

### Task 1: Lock Prompt Visibility Rules

**Files:**
- Modify: `ppt-maker-with-image/references/prompt-templates.md`
- Modify: `ppt-maker-with-image/scripts/style/header.py`
- Test: `ppt-maker-with-image/tests/test_style_header.py`

- [ ] **Step 1: Add failing tests for invisible constraints**

Append these tests to `ppt-maker-with-image/tests/test_style_header.py`:

```python
def test_build_style_header_marks_measurements_as_invisible_constraints() -> None:
    header = build_style_header(
        {
            "layout_system": {"margins": "左右 56-72px，上下 40-56px", "module_spacing": "20-28px"},
            "typography": {"caption": "12-14px, gray", "page_title": "36-44px, bold"},
        }
    )

    assert "不可见设计约束" in header
    assert "不要把" in header
    assert "px" in header
    assert "Caption" not in header


def test_build_style_header_forbids_visible_design_annotations() -> None:
    header = build_style_header({"prompt_block": "白底，绿色主色。"})

    assert "禁止渲染尺寸标注" in header
    assert "红色标注框" in header
    assert "设计稿标尺" in header
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_style_header.py -q
```

Expected: at least one failure because `build_style_header()` does not yet include invisible-constraint language.

- [ ] **Step 3: Update `build_style_header()` to separate visible copy from invisible style rules**

In `ppt-maker-with-image/scripts/style/header.py`, add this helper near `_format_items`:

```python
def _format_dict_items(items: dict[str, Any]) -> str:
    parts: list[str] = []
    for key, value in items.items():
        text = _safe_int(value)
        if text:
            parts.append(f"{key}: {text}")
    return "; ".join(parts)
```

Then replace the beginning of `build_style_header()` after `page_intent = page_intent or {}` with:

```python
    lines.append("【不可见设计约束】以下规则只用于控制版式、层级、间距、字体和视觉一致性，不是幻灯片可见文案。")
    lines.append("【禁止渲染尺寸标注】不要把 px、pt、R=、stroke、shadow、margin、spacing、caption 字号、红色标注框、设计稿标尺、对齐辅助线、线框注释或任何提示词/schema文字画到页面上。")
```

Then replace the dict formatting branch:

```python
        elif isinstance(value, dict):
            text = _format_dict_items(value)
```

- [ ] **Step 4: Update render wrapper template with hard negative instruction**

In `ppt-maker-with-image/references/prompt-templates.md`, update `Image Rendering Wrapper Prompt` constraints to include:

```text
Visible slide copy must only include presentation content.
Treat all style measurements, font sizes, spacing values, radius values, stroke values, and shadow values as invisible design instructions.
Never render measurement labels or design annotations such as "40-56px", "20-28px", "56-72px", "Caption: 12-14px", "R=14px", "stroke=1pt", red boxes, rulers, alignment guides, wireframes, or prompt/schema text.
```

- [ ] **Step 5: Update per-slide prompt template to forbid restating style tokens**

In `ppt-maker-with-image/references/prompt-templates.md`, add this constraint under `Per-Slide Prompt Generation Prompt`:

```text
- image_prompt must contain page-specific visible content and layout intent only; do not restate font-size ranges, spacing values, margin values, radius values, stroke values, shadow values, or caption-size labels.
```

- [ ] **Step 6: Run targeted prompt tests**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_style_header.py -q
```

Expected: all tests in `test_style_header.py` pass.

- [ ] **Step 7: Commit Task 1**

Run:

```bash
cd /Users/guojiexie/Development/skills
git add ppt-maker-with-image/references/prompt-templates.md ppt-maker-with-image/scripts/style/header.py ppt-maker-with-image/tests/test_style_header.py
git commit -m "Keep slide design measurements invisible" -m "Style headers still carry exact layout and typography constraints, but they now explicitly frame those values as non-visible rendering instructions so image models do not draw px labels, caption-size text, red measurement boxes, or prompt artifacts." -m "Constraint: Approved redesign keeps deterministic STYLE_HEADER as the source of visual constants" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python3 -m pytest ppt-maker-with-image/tests/test_style_header.py -q"
```

---

### Task 2: Extend Image Provider Contract

**Files:**
- Modify: `ppt-maker-with-image/scripts/llm/image/base.py`
- Modify: `ppt-maker-with-image/scripts/llm/image/openrouter.py`
- Modify: `ppt-maker-with-image/scripts/llm/image/openai.py`
- Modify: `ppt-maker-with-image/scripts/llm/image/gemini.py`
- Test: `ppt-maker-with-image/tests/test_llm_image_quality_fixes.py`

- [ ] **Step 1: Add failing tests for reference payload routing**

Append this test to `ppt-maker-with-image/tests/test_llm_image_quality_fixes.py`:

```python
def test_openrouter_sends_reference_images_as_multimodal_content(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}
    response = _json_response(
        "POST",
        "https://openrouter.ai/api/v1/chat/completions",
        {"choices": [{"message": {"images": [{"image_url": {"url": "data:image/png;base64,aW1hZ2U="}}]}}]},
    )

    class _RecordingClient(_FakeClient):
        def post(self, *_args, **kwargs) -> httpx.Response:
            recorded.update(kwargs)
            return response

    monkeypatch.setattr(openrouter_module.httpx, "Client", lambda timeout=60.0: _RecordingClient(response))

    provider = OpenRouterImageProvider(ProviderConfig(name="openrouter"), api_key="test-key")
    request = ImageRenderRequest(
        prompt="render slide 2",
        model="openrouter-model",
        reference_images=[b"reference-bytes"],
        seed=123,
    )

    provider.render(request)

    payload = recorded["json"]
    content = payload["messages"][0]["content"]
    assert isinstance(content, list)
    assert content[0]["type"] == "text"
    assert content[1]["type"] == "image_url"
    assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_llm_image_quality_fixes.py -q
```

Expected: failure because `ImageRenderRequest` has no `reference_images` field and OpenRouter sends string content.

- [ ] **Step 3: Add seed/reference fields and capabilities**

Update `ppt-maker-with-image/scripts/llm/image/base.py`:

```python
from dataclasses import dataclass
from typing import Sequence
```

Change `ImageRenderRequest` to:

```python
@dataclass(frozen=True)
class ImageRenderRequest:
    prompt: str
    model: str
    resolution: str = "3840x2160"
    aspect_ratio: str = "16:9"
    mime_type: str = "image/png"
    seed: int | None = None
    reference_images: Sequence[bytes] | None = None
```

Add these properties to `ImageProvider`:

```python
    supports_reference_images: bool = False
    supports_seed: bool = False

    @property
    def capability_info(self) -> dict[str, bool]:
        return {
            "supports_reference_images": self.supports_reference_images,
            "supports_seed": self.supports_seed,
        }
```

- [ ] **Step 4: Implement OpenRouter reference-image content**

In `ppt-maker-with-image/scripts/llm/image/openrouter.py`, add class attributes:

```python
    supports_reference_images = True
    supports_seed = False
```

Add helper functions near `_openrouter_image_size()`:

```python
def _build_message_content(prompt: str, reference_images: Any) -> Any:
    if not reference_images:
        return prompt
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image_bytes in reference_images:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}})
    return content
```

Then change the payload `messages` entry to:

```python
            "messages": [{"role": "user", "content": _build_message_content(request.prompt, request.reference_images)}],
```

- [ ] **Step 5: Declare OpenAI/Gemini capabilities for this pass**

In `ppt-maker-with-image/scripts/llm/image/openai.py`, add inside `OpenAIImageProvider`:

```python
    supports_reference_images = False
    supports_seed = True
```

In `ppt-maker-with-image/scripts/llm/image/gemini.py`, add inside `GeminiImageProvider`:

```python
    supports_reference_images = False
    supports_seed = False
```

- [ ] **Step 6: Run provider tests**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_llm_image_quality_fixes.py -q
```

Expected: all tests in `test_llm_image_quality_fixes.py` pass.

- [ ] **Step 7: Commit Task 2**

Run:

```bash
cd /Users/guojiexie/Development/skills
git add ppt-maker-with-image/scripts/llm/image/base.py ppt-maker-with-image/scripts/llm/image/openrouter.py ppt-maker-with-image/scripts/llm/image/openai.py ppt-maker-with-image/scripts/llm/image/gemini.py ppt-maker-with-image/tests/test_llm_image_quality_fixes.py
git commit -m "Add reference image support to image provider contract" -m "Image rendering requests now carry optional seed and reference image bytes. OpenRouter sends those bytes as multimodal image_url content, while other adapters declare their capabilities so the render stage can downgrade cleanly." -m "Constraint: Reference images are opt-in and slide 1 must remain unreferenced" -m "Confidence: high" -m "Scope-risk: moderate" -m "Tested: python3 -m pytest ppt-maker-with-image/tests/test_llm_image_quality_fixes.py -q"
```

---

### Task 3: Route First-Slide References in Render Stage

**Files:**
- Modify: `ppt-maker-with-image/scripts/pipeline/stage_render.py`
- Modify: `ppt-maker-with-image/scripts/run_ppt_job.py`
- Test: `ppt-maker-with-image/tests/test_stage_render.py`

- [ ] **Step 1: Create failing render-stage tests**

Create `ppt-maker-with-image/tests/test_stage_render.py` with:

```python
from __future__ import annotations

from pathlib import Path

from llm.config import ModelConfig, ModelRoleConfig, ProviderConfig
from pipeline import stage_render


class _FakeProvider:
    supports_reference_images = True
    supports_seed = True

    def __init__(self) -> None:
        self.requests = []

    def render(self, request):
        self.requests.append(request)
        return b"image-bytes"

    def close(self) -> None:
        pass


def _model_config() -> ModelConfig:
    return ModelConfig(
        default_provider="openrouter",
        text=ModelRoleConfig(provider="openrouter", model="text-model"),
        image=ModelRoleConfig(provider="openrouter", model="image-model"),
        providers={"openrouter": ProviderConfig(name="openrouter")},
    )


def test_stage_render_routes_first_slide_as_reference_for_following_slides(
    tmp_path: Path,
    monkeypatch,
) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    slide_prompts = {
        "slides": [
            {"page_no": 1, "title": "封面", "image_prompt": "slide 1"},
            {"page_no": 2, "title": "分析", "image_prompt": "slide 2"},
            {"page_no": 3, "title": "行动", "image_prompt": "slide 3"},
        ]
    }

    paths = stage_render.run_stage(
        {"consistency": {"use_reference_image": True, "reference_source": "first_slide", "seed": 123}},
        _model_config(),
        slide_prompts,
        tmp_path,
        dry_run=False,
    )

    assert len(paths) == 3
    assert provider.requests[0].reference_images is None
    assert provider.requests[1].reference_images == [b"image-bytes"]
    assert provider.requests[2].reference_images == [b"image-bytes"]
    assert provider.requests[1].seed == 123


def test_stage_render_keeps_reference_disabled_by_default(tmp_path: Path, monkeypatch) -> None:
    provider = _FakeProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    stage_render.run_stage(
        {},
        _model_config(),
        {"slides": [{"page_no": 1, "title": "一", "image_prompt": "one"}, {"page_no": 2, "title": "二", "image_prompt": "two"}]},
        tmp_path,
        dry_run=False,
    )

    assert provider.requests[0].reference_images is None
    assert provider.requests[1].reference_images is None
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_stage_render.py -q
```

Expected: failure because `stage_render` ignores `job.consistency` and never passes reference images.

- [ ] **Step 3: Implement consistency helpers**

In `ppt-maker-with-image/scripts/pipeline/stage_render.py`, add:

```python
def _consistency_config(job: dict[str, Any]) -> dict[str, Any]:
    consistency = job.get("consistency")
    return consistency if isinstance(consistency, dict) else {}


def _use_first_slide_reference(job: dict[str, Any]) -> bool:
    consistency = _consistency_config(job)
    return bool(consistency.get("use_reference_image")) and consistency.get("reference_source", "first_slide") == "first_slide"


def _seed(job: dict[str, Any]) -> int | None:
    value = _consistency_config(job).get("seed")
    return value if isinstance(value, int) else None
```

- [ ] **Step 4: Pass reference images during render**

In `run_stage()`, remove `del job`. Before the loop, add:

```python
    use_reference = _use_first_slide_reference(job)
    seed = _seed(job)
    first_slide_bytes: bytes | None = None
```

Inside the non-dry-run branch, before constructing `ImageRenderRequest`, add:

```python
                page_no = int(slide["page_no"])
                reference_images = [first_slide_bytes] if use_reference and page_no > 1 and first_slide_bytes else None
```

Then construct:

```python
                request = ImageRenderRequest(
                    prompt=build_image_render_prompt(slide.get("image_prompt", ""), config.resolution),
                    model=config.image.model,
                    resolution=config.resolution,
                    aspect_ratio=config.aspect_ratio,
                    seed=seed,
                    reference_images=reference_images,
                )
                rendered = provider.render(request)
                output_path.write_bytes(rendered)
                if page_no == 1:
                    first_slide_bytes = rendered
```

- [ ] **Step 5: Run render-stage tests**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_stage_render.py -q
```

Expected: all tests in `test_stage_render.py` pass.

- [ ] **Step 6: Commit Task 3**

Run:

```bash
cd /Users/guojiexie/Development/skills
git add ppt-maker-with-image/scripts/pipeline/stage_render.py ppt-maker-with-image/tests/test_stage_render.py
git commit -m "Route first slide reference images during rendering" -m "The render stage now reads job.consistency and passes slide_01 bytes to later slides only when first-slide reference mode is enabled. Default behavior remains unchanged." -m "Constraint: Slide 1 must never reference another image" -m "Confidence: high" -m "Scope-risk: moderate" -m "Tested: python3 -m pytest ppt-maker-with-image/tests/test_stage_render.py -q"
```

---

### Task 4: Add Unsupported-Reference Fallback and Manifest Evidence

**Files:**
- Modify: `ppt-maker-with-image/scripts/pipeline/stage_render.py`
- Modify: `ppt-maker-with-image/scripts/run_ppt_job.py`
- Test: `ppt-maker-with-image/tests/test_stage_render.py`

- [ ] **Step 1: Add failing fallback test**

Append to `ppt-maker-with-image/tests/test_stage_render.py`:

```python
class _NoReferenceProvider(_FakeProvider):
    supports_reference_images = False


def test_stage_render_downgrades_when_provider_lacks_reference_support(tmp_path: Path, monkeypatch) -> None:
    provider = _NoReferenceProvider()
    monkeypatch.setattr(stage_render, "build_image_provider", lambda *_args, **_kwargs: provider)

    paths = stage_render.run_stage(
        {"consistency": {"use_reference_image": True, "reference_source": "first_slide"}},
        _model_config(),
        {"slides": [{"page_no": 1, "title": "一", "image_prompt": "one"}, {"page_no": 2, "title": "二", "image_prompt": "two"}]},
        tmp_path,
        dry_run=False,
    )

    assert len(paths) == 2
    assert provider.requests[1].reference_images is None
```

- [ ] **Step 2: Run fallback test and verify failure**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_stage_render.py::test_stage_render_downgrades_when_provider_lacks_reference_support -q
```

Expected: failure because `stage_render` still passes reference bytes regardless of provider capability.

- [ ] **Step 3: Add provider capability check**

In `ppt-maker-with-image/scripts/pipeline/stage_render.py`, after provider creation add:

```python
    provider_supports_reference = bool(getattr(provider, "supports_reference_images", False)) if provider is not None else False
```

Change the reference assignment to:

```python
                reference_images = (
                    [first_slide_bytes]
                    if use_reference and provider_supports_reference and page_no > 1 and first_slide_bytes
                    else None
                )
```

- [ ] **Step 4: Add render metadata return shape**

Keep `run_stage()` returning `list[Path]` for compatibility. Add a small metadata file next to images:

```python
    metadata = {
        "use_reference_image": use_reference,
        "provider_supports_reference_images": provider_supports_reference,
        "reference_source": "first_slide" if use_reference else None,
        "fallback_reason": None if (not use_reference or provider_supports_reference) else "provider_does_not_support_reference_images",
    }
```

Before return:

```python
    write_json(output_dir / "render_metadata.json", metadata)
```

Also import `write_json` from `.common`.

- [ ] **Step 5: Update manifest artifact tracking**

In `ppt-maker-with-image/scripts/run_ppt_job.py`, after `image_paths = run_render_stage(...)`, read the metadata if present:

```python
    render_metadata_path = output_dir / "render_metadata.json"
    if render_metadata_path.exists():
        manifest["render_metadata"] = load_json(render_metadata_path)
```

- [ ] **Step 6: Run fallback tests**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_stage_render.py -q
```

Expected: all render-stage tests pass.

- [ ] **Step 7: Commit Task 4**

Run:

```bash
cd /Users/guojiexie/Development/skills
git add ppt-maker-with-image/scripts/pipeline/stage_render.py ppt-maker-with-image/scripts/run_ppt_job.py ppt-maker-with-image/tests/test_stage_render.py
git commit -m "Record reference image rendering fallback" -m "Render metadata now records whether first-slide reference mode was requested, whether the selected provider supports it, and why the run downgraded when support is missing." -m "Constraint: Unsupported provider features must not fail the run" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python3 -m pytest ppt-maker-with-image/tests/test_stage_render.py -q"
```

---

### Task 5: Apply Reference Policy to Single-Slide Regeneration

**Files:**
- Modify: `ppt-maker-with-image/scripts/regenerate_single_slide.py`
- Test: `ppt-maker-with-image/tests/test_regenerate_single_slide_reference.py`

- [ ] **Step 1: Add focused helper tests**

Create `ppt-maker-with-image/tests/test_regenerate_single_slide_reference.py`:

```python
from __future__ import annotations

from pathlib import Path

from regenerate_single_slide import load_first_slide_reference


def test_load_first_slide_reference_skips_page_one(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "slide_01.png").write_bytes(b"first")

    assert load_first_slide_reference(tmp_path, page_no=1, use_reference=True) is None


def test_load_first_slide_reference_returns_first_slide_for_later_pages(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "slide_01.png").write_bytes(b"first")

    assert load_first_slide_reference(tmp_path, page_no=2, use_reference=True) == [b"first"]


def test_load_first_slide_reference_disabled_by_default(tmp_path: Path) -> None:
    image_dir = tmp_path / "images"
    image_dir.mkdir()
    (image_dir / "slide_01.png").write_bytes(b"first")

    assert load_first_slide_reference(tmp_path, page_no=2, use_reference=False) is None
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_regenerate_single_slide_reference.py -q
```

Expected: import failure because `load_first_slide_reference` does not exist.

- [ ] **Step 3: Add helper in `regenerate_single_slide.py`**

Add:

```python
def load_first_slide_reference(output_dir: Path, *, page_no: int, use_reference: bool) -> list[bytes] | None:
    if not use_reference or page_no <= 1:
        return None
    first_slide = output_dir / "images" / "slide_01.png"
    if not first_slide.exists():
        return None
    return [first_slide.read_bytes()]
```

- [ ] **Step 4: Use helper when rerendering**

Before `ImageRenderRequest(...)` in `regenerate_single_slide.py`, add:

```python
            consistency = job.get("consistency") if isinstance(job.get("consistency"), dict) else {}
            reference_images = load_first_slide_reference(
                output_dir,
                page_no=args.page_no,
                use_reference=bool(consistency.get("use_reference_image")),
            )
```

Then pass:

```python
                reference_images=reference_images,
                seed=consistency.get("seed") if isinstance(consistency.get("seed"), int) else None,
```

- [ ] **Step 5: Run regeneration helper tests**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests/test_regenerate_single_slide_reference.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 5**

Run:

```bash
cd /Users/guojiexie/Development/skills
git add ppt-maker-with-image/scripts/regenerate_single_slide.py ppt-maker-with-image/tests/test_regenerate_single_slide_reference.py
git commit -m "Use first slide as regeneration reference when enabled" -m "Single-slide regeneration now follows the same reference policy as full rendering: slide 1 is never referenced, and later pages can opt into slide_01 as a stable visual anchor." -m "Constraint: Reference selection must not compound drift through neighboring slides" -m "Confidence: high" -m "Scope-risk: narrow" -m "Tested: python3 -m pytest ppt-maker-with-image/tests/test_regenerate_single_slide_reference.py -q"
```

---

### Task 6: End-to-End Verification and Real Rerun

**Files:**
- Modify only if tests reveal a defect.
- Output: `ppt-maker-with-image/outputs/reference-fix-rerun/deck.pptx`

- [ ] **Step 1: Run all unit tests**

Run:

```bash
cd /Users/guojiexie/Development/skills
python3 -m pytest ppt-maker-with-image/tests -q
```

Expected: all tests pass.

- [ ] **Step 2: Run import smoke**

Run:

```bash
cd /Users/guojiexie/Development/skills/ppt-maker-with-image/scripts
python3 - <<'PY'
import importlib

mods = [
    "pipeline.stage_render",
    "pipeline.stage_slide_prompts",
    "style.header",
    "llm.image.base",
    "llm.image.openrouter",
    "run_ppt_job",
    "regenerate_single_slide",
]
for mod in mods:
    importlib.import_module(mod)
print("import_smoke_ok")
PY
```

Expected: `import_smoke_ok`.

- [ ] **Step 3: Create a reference-enabled rerun job**

Run:

```bash
cd /Users/guojiexie/Development/skills/ppt-maker-with-image
python3 - <<'PY'
import json
from pathlib import Path

job = {
    "template_id": "huixin",
    "template_name": "慧新",
    "topic": "2026产品增长复盘",
    "target_audience": "管理层",
    "purpose": "季度复盘汇报",
    "style": "慧新",
    "page_count": 3,
    "key_points": ["增长结果", "关键驱动", "下一步行动"],
    "must_have_sections": ["总览", "拆解", "计划"],
    "constraints": {"brand_colors": ["#A8D86B", "#0F95B6"], "logo_required": False, "language": "zh-CN"},
    "outline_approved": False,
    "prompts_approved": False,
    "page_intent_approved": False,
    "consistency": {"use_reference_image": True, "reference_source": "first_slide", "seed": 123456},
    "output": {"directory": "/tmp/ppt-reference-fix-artifacts", "pptx_filename": "deck.pptx"},
}
Path("/tmp/ppt_reference_fix_job.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
print("/tmp/ppt_reference_fix_job.json")
PY
```

Expected: `/tmp/ppt_reference_fix_job.json`.

- [ ] **Step 4: Run real OpenRouter generation**

Run:

```bash
cd /Users/guojiexie/Development/skills/ppt-maker-with-image
rm -rf /tmp/ppt-reference-fix-artifacts
OPENROUTER_API_KEY="$OPENROUTER_API_KEY" /tmp/ppt-maker-rerun-venv/bin/python scripts/run_ppt_job.py /tmp/ppt_reference_fix_job.json --output-dir /tmp/ppt-reference-fix-artifacts --auto-approve-outline --auto-approve-prompts
```

Expected: `[OK] PPTX 已生成：/private/tmp/ppt-reference-fix-artifacts/deck.pptx`.

- [ ] **Step 5: Verify artifacts and page count**

Run:

```bash
cd /Users/guojiexie/Development/skills/ppt-maker-with-image
python3 scripts/review_job_status.py /tmp/ppt_reference_fix_job.json --output-dir /tmp/ppt-reference-fix-artifacts --json
python3 - <<'PY'
from pathlib import Path
from pptx import Presentation

ppt = Path("/tmp/ppt-reference-fix-artifacts/deck.pptx")
prs = Presentation(str(ppt))
print("slides", len(prs.slides))
print("ppt_size", ppt.stat().st_size)
for image in sorted((ppt.parent / "images").glob("slide_*.png")):
    print(image.name, image.stat().st_size)
PY
```

Expected:

```text
"completed": true
"issues": []
slides 3
slide_01.png ...
slide_02.png ...
slide_03.png ...
```

- [ ] **Step 6: Copy final outputs**

Run:

```bash
cd /Users/guojiexie/Development/skills/ppt-maker-with-image
mkdir -p outputs/reference-fix-rerun
cp /tmp/ppt-reference-fix-artifacts/deck.pptx outputs/reference-fix-rerun/deck.pptx
cp /tmp/ppt-reference-fix-artifacts/render_metadata.json outputs/reference-fix-rerun/render_metadata.json
cp /tmp/ppt-reference-fix-artifacts/manifest.json outputs/reference-fix-rerun/manifest.json
rm -rf outputs/reference-fix-rerun/images
cp -R /tmp/ppt-reference-fix-artifacts/images outputs/reference-fix-rerun/images
```

Expected: `outputs/reference-fix-rerun/deck.pptx` exists.

- [ ] **Step 7: Manual visual check**

Open:

```text
/Users/guojiexie/Development/skills/ppt-maker-with-image/outputs/reference-fix-rerun/deck.pptx
```

Expected:

```text
The deck has 3 pages.
Slides do not show visible "40-56px", "20-28px", "56-72px", "Caption: 12-14px", red measurement boxes, ruler labels, or prompt/schema fragments.
Slides 2 and 3 preserve a closer visual rhythm to slide 1 when OpenRouter accepts reference image input.
```

- [ ] **Step 8: Commit verification fixes only if needed**

If Step 4-7 required code changes, run:

```bash
cd /Users/guojiexie/Development/skills
git add <changed-files>
git commit -m "Stabilize reference image PPT rerun" -m "Verification exposed a concrete defect during the real OpenRouter rerun, and this commit contains only the targeted fix needed to pass the rerun." -m "Confidence: medium" -m "Scope-risk: narrow" -m "Tested: python3 -m pytest ppt-maker-with-image/tests -q; real OpenRouter rerun"
```

---

## Self-Review

- Spec coverage: prompt visibility rules are covered by Task 1; provider contract and OpenRouter reference payload by Task 2; first-slide routing by Task 3; unsupported-provider fallback and manifest evidence by Task 4; single-slide regeneration by Task 5; real rerun by Task 6.
- Placeholder scan: no reserved placeholder tokens or deferred-work language is used as a plan instruction.
- Type consistency: `ImageRenderRequest.seed` and `ImageRenderRequest.reference_images` are introduced in Task 2 and used consistently in Tasks 3 and 5. Provider capability names are `supports_reference_images` and `supports_seed` throughout.
