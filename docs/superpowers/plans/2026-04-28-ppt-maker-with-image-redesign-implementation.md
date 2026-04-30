# ppt-maker-with-image Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-architect `ppt-maker-with-image` into a stage-based, provider-agnostic, visually consistent pipeline with deterministic style headers, optional reference-image anchoring, and source-material grounded page intent.

**Architecture:** The implementation introduces `scripts/llm` for unified provider calls, `scripts/style/header.py` for non-LLM style constraints, and `scripts/pipeline/*` for six serial stages with file-level checkpoints. `run_ppt_job.py` becomes a thin orchestrator governed by `review_mode` and stage outputs on disk. A manifest tracks deterministic settings and provider capability fallbacks.

**Tech Stack:** Python 3.10+, `litellm`, `google-genai`, Pillow, PyYAML, httpx, python-pptx.

---

### 任务 1: 结构与依赖基线（准备）

**Files:**
- 修改: `ppt-maker-with-image/assets/python_requirements.txt`
- 修改: `ppt-maker-with-image/assets/model_config.yaml`
- 新增: `ppt-maker-with-image/scripts/llm/__init__.py`
- 新增: `ppt-maker-with-image/scripts/llm/config.py`
- 新增: `ppt-maker-with-image/scripts/llm/text.py`
- 新增: `ppt-maker-with-image/scripts/llm/image/base.py`
- 新增: `ppt-maker-with-image/scripts/llm/image/__init__.py`
- 新增: `ppt-maker-with-image/scripts/llm/image/openrouter.py`
- 新增: `ppt-maker-with-image/scripts/llm/image/openai.py`
- 新增: `ppt-maker-with-image/scripts/llm/image/gemini.py`
- 新增: `ppt-maker-with-image/scripts/llm/errors.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/__init__.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/manifest.py`

- [ ] **Step 1: 更新依赖与模型配置占位符**
```bash
cd /Users/guojiexie/Development/skills/ppt-maker-with-image
python3 - <<'PY'
from pathlib import Path
p = Path('assets/python_requirements.txt')
lines = p.read_text(encoding='utf-8').splitlines()
if 'litellm>=1.51' not in lines:
    lines.append('litellm>=1.51')
if 'google-genai>=0.5' not in lines:
    lines.append('google-genai>=0.5')
p.write_text('\n'.join(lines) + '\n', encoding='utf-8')

p2 = Path('assets/model_config.yaml')
p2.write_text('''text_model: "openai/gpt-4o"
image_model: "openrouter/google/gemini-2.0-flash-preview-image-02-05"
aspect_ratio: "16:9"
resolution: "3840x2160"
language: "zh-CN"
font_preferences:
  cjk: "Microsoft YaHei"
  latin: "Arial"
providers:
  openai:
    api_key_env: "OPENAI_API_KEY"
    base_url: null
  anthropic:
    api_key_env: "ANTHROPIC_API_KEY"
    base_url: null
  openrouter:
    api_key_env: "OPENROUTER_API_KEY"
    base_url: "https://openrouter.ai/api/v1"
  azure:
    api_key_env: "AZURE_OPENAI_KEY"
    base_url: ""
    api_version: "2024-10-21-preview"
  ollama:
    api_key_env: null
    base_url: "http://localhost:11434"
  gemini:
    api_key_env: "GEMINI_API_KEY"
    base_url: null
''', encoding='utf-8')
PY
```

- [ ] **Step 2: 运行失败验证（确认文件改动已写入）**
```bash
grep -n "litellm\|google-genai\|providers:" assets/python_requirements.txt assets/model_config.yaml
```
Expected: 新依赖与 provider 段落可见。

- [ ] **Step 3: 新建 llm 公共类型与异常定义**
```python
# scripts/llm/errors.py
from __future__ import annotations

class UnsupportedFeatureError(RuntimeError):
    """Raised when a provider cannot support requested image features."""

class ProviderError(RuntimeError):
    """Raised when provider returns malformed payloads or transport errors."""
```

```python
# scripts/llm/image/base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

@dataclass(frozen=True)
class ImageRenderRequest:
    prompt: str
    aspect_ratio: str = "16:9"
    resolution: str = "3840x2160"
    seed: int | None = None
    reference_images: Sequence[bytes] | None = None

class ImageProvider:
    supports_reference_images: bool = False
    supports_seed: bool = False

    def __init__(self, **_cfg) -> None:
        pass

    @property
    def capability_info(self) -> dict:
        return {
            "supports_reference_images": self.supports_reference_images,
            "supports_seed": self.supports_seed,
        }

    def render(self, request: ImageRenderRequest) -> bytes:
        raise NotImplementedError
```

- [ ] **Step 4: 写入 `llm/__init__.py` 与 `llm/config.py`**
```python
# scripts/llm/config.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import yaml
from typing import Any

@dataclass(frozen=True)
class ProviderOptions:
    base_url: str | None = None
    api_key_env: str | None = None
    api_version: str | None = None

@dataclass(frozen=True)
class LLMConfig:
    text_model: str
    image_model: str
    aspect_ratio: str
    resolution: str
    language: str
    font_preferences: dict[str, str]
    providers: dict[str, ProviderOptions]

    def provider_prefix(self, model: str) -> str:
        return model.split("/")[0]


def load_model_config(path: str | Path) -> LLMConfig:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    providers = {
        k: ProviderOptions(
            base_url=v.get("base_url"),
            api_key_env=v.get("api_key_env"),
            api_version=v.get("api_version"),
        )
        for k, v in (payload.get("providers") or {}).items()
    }
    return LLMConfig(
        text_model=payload["text_model"],
        image_model=payload["image_model"],
        aspect_ratio=payload.get("aspect_ratio", "16:9"),
        resolution=payload.get("resolution", "3840x2160"),
        language=payload.get("language", "zh-CN"),
        font_preferences=payload.get("font_preferences", {"cjk": "Microsoft YaHei", "latin": "Arial"}),
        providers=providers,
    )


def resolve_api_key(prefix: str, cfg: LLMConfig) -> str | None:
    opts = cfg.providers.get(prefix)
    if not opts or not opts.api_key_env:
        return None
    return os.getenv(opts.api_key_env)
```

```python
# scripts/llm/__init__.py
from .config import LLMConfig, ProviderOptions, load_model_config, resolve_api_key
from .text import call_text_model
from .image import build_image_provider
from .errors import UnsupportedFeatureError, ProviderError

__all__ = [
    "LLMConfig",
    "ProviderOptions",
    "load_model_config",
    "resolve_api_key",
    "call_text_model",
    "build_image_provider",
    "UnsupportedFeatureError",
    "ProviderError",
]
```

- [ ] **Step 5: 实现文本调用封装（纯 JSON、支持重试与宽松解析）**
```python
# scripts/llm/text.py
from __future__ import annotations

from typing import Any
import json
import litellm


def call_text_model(model: str, messages: list[dict[str, str]], *, timeout: float = 120.0) -> dict[str, Any]:
    response = litellm.completion(model=model, messages=messages, temperature=0.3, response_format={"type": "json_object"}, timeout=timeout)
    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except Exception:
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            raise
        return json.loads(raw[start : end + 1])
```

- [ ] **Step 6: 实现 `ImageProvider` 适配器（OpenRouter / OpenAI / Gemini）**
```python
# scripts/llm/image/openrouter.py
from __future__ import annotations

from httpx import Client, Timeout
from .base import ImageProvider, ImageRenderRequest
from ..errors import ProviderError

class OpenRouterImageProvider(ImageProvider):
    supports_reference_images = False
    supports_seed = False

    def __init__(self, base_url: str, api_key: str) -> None:
        self._client = Client(base_url=base_url, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, timeout=Timeout(180.0, connect=20.0))

    def render(self, request: ImageRenderRequest) -> bytes:
        r = self._client.post(
            "/chat/completions",
            json={
                "model": request.model,
                "messages": [{"role": "user", "content": request.prompt}],
                "modalities": ["image", "text"],
                "temperature": 0.1,
                "image_config": {"aspect_ratio": request.aspect_ratio, "image_size": "4K"},
            },
        )
        r.raise_for_status()
        images = r.json()["choices"][0]["message"].get("images") or []
        if not images:
            raise ProviderError("No images returned")
        data = images[0].get("image_url", {}).get("url")
        if data and data.startswith("http"):
            return self._client.get(data).content
        if data and data.startswith("data:"):
            import base64
            return base64.b64decode(data.split(",", 1)[1])
        raise ProviderError("Unsupported image payload")
```

```python
# scripts/llm/image/openai.py
from __future__ import annotations

from openai import OpenAI
from .base import ImageProvider, ImageRenderRequest

class OpenAIImageProvider(ImageProvider):
    supports_reference_images = False
    supports_seed = True

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def render(self, request: ImageRenderRequest) -> bytes:
        body = {
            "model": "gpt-image-1",
            "prompt": request.prompt,
            "size": request.resolution,
            "n": 1,
        }
        if request.seed is not None:
            body["seed"] = request.seed
        response = self._client.images.generate(**body)
        return self._client.files.content(response.data[0].b64_json)
```

```python
# scripts/llm/image/gemini.py
from __future__ import annotations

from google import genai
from .base import ImageProvider, ImageRenderRequest

class GeminiImageProvider(ImageProvider):
    supports_reference_images = False
    supports_seed = True

    def __init__(self, api_key: str) -> None:
        self._client = genai.Client(api_key=api_key)

    def render(self, request: ImageRenderRequest) -> bytes:
        resp = self._client.models.generate_content(model="gemini-2.5-flash-image-preview", contents=request.prompt)
        return resp.candidates[0].content.candidates
```

```python
# scripts/llm/image/__init__.py
from __future__ import annotations

from .base import ImageRenderRequest
from ..config import LLMConfig, resolve_api_key
from ..errors import UnsupportedFeatureError
from .openrouter import OpenRouterImageProvider
from .openai import OpenAIImageProvider
from .gemini import GeminiImageProvider


def build_image_provider(cfg: LLMConfig, *, model: str):
    pfx = model.split("/")[0]
    opts = cfg.providers.get(pfx)
    if pfx == "openrouter":
        api_key = resolve_api_key(pfx, cfg)
        if not api_key:
            raise UnsupportedFeatureError("Missing OPENROUTER_API_KEY")
        return OpenRouterImageProvider(opts.base_url or "https://openrouter.ai/api/v1", api_key)
    if pfx in {"openai", "gpt-image-2"}:
        api_key = resolve_api_key("openai", cfg)
        if not api_key:
            raise UnsupportedFeatureError("Missing OPENAI_API_KEY")
        return OpenAIImageProvider(api_key=api_key, base_url=opts.base_url if opts else None)
    if pfx in {"google", "gemini"}:
        api_key = resolve_api_key("gemini", cfg)
        if not api_key:
            raise UnsupportedFeatureError("Missing GEMINI_API_KEY")
        return GeminiImageProvider(api_key=api_key)
    raise UnsupportedFeatureError(f"Unsupported image provider: {pfx}")
```

- [ ] **Step 7: 执行提交（准备阶段）**
```bash
git add ppt-maker-with-image/assets/python_requirements.txt ppt-maker-with-image/assets/model_config.yaml ppt-maker-with-image/scripts/llm ppt-maker-with-image/scripts/pipeline/prompt.py 2>/dev/null || true
git commit -m "feat(ppt-maker-with-image): add llm abstraction scaffolding"
```

---

### 任务 2: Stage 1 Pipeline 化改造（统一调用 + 兼容模型入口）

**Files:**
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_master_style.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_outline.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_slide_prompts.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_render.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_assemble.py`
- 修改: `ppt-maker-with-image/scripts/run_ppt_job.py`
- 修改: `ppt-maker-with-image/scripts/regenerate_single_slide.py`
- 修改: `ppt-maker-with-image/scripts/render_single_slide_ppt.py`
- 修改: `ppt-maker-with-image/scripts/review_job_status.py`
- 修改: `ppt-maker-with-image/references/prompt-templates.md`
- 修改: `ppt-maker-with-image/references/workflow.md`
- 测试: `ppt-maker-with-image/tests/test_stage_master_style.py`
- 测试: `ppt-maker-with-image/tests/test_stage_outline.py`

- [ ] **Step 1: 新增通用清单与 manifest 工具**
```python
# scripts/pipeline/manifest.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
from typing import Any


def manifest_path(output_dir: Path) -> Path:
    return output_dir / "manifest.json"


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"provider_capabilities": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def write_manifest(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
```

- [ ] **Step 2: Stage 1：master_style 阶段（纯函数）**
```python
# scripts/pipeline/stage_master_style.py
from __future__ import annotations

from pathlib import Path
import json
from ..llm.config import LLMConfig
from ..llm import call_text_model
from ..references import load_prompt_template
from ..utils import build_requirement_summary


def run_stage(job: dict, config: LLMConfig, *, client=None, dry_run=False) -> dict:
    if job.get("master_style"):
        return job["master_style"]
    if dry_run:
        return {"visual_positioning": "正式、专业、结构化", "color_strategy": {"background": "#FFFFFF"}, "forbidden_elements": ["3D图表"]}
    if client is None:
        return {"visual_positioning": "professional", "color_strategy": {"background": "#FFFFFF"}, "forbidden_elements": []}
    prompt = load_prompt_template("Master Style Brief Generation Prompt")
    return call_text_model(
        model=config.text_model,
        messages=[
            {"role": "system", "content": prompt.format(requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False), template_preset_json=json.dumps(job.get("template_preset", {}), ensure_ascii=False))},
            {"role": "user", "content": "Generate master style JSON."},
        ],
    )
```

- [ ] **Step 3: Stage 2：outline 阶段（兼容 legacy `job.outline`）**
```python
# scripts/pipeline/stage_outline.py
from __future__ import annotations

from ..llm.config import LLMConfig
from ..llm import call_text_model
from ..references import load_prompt_template
from ..utils import build_requirement_summary
import json

def run_stage(job: dict, config: LLMConfig, *, dry_run=False) -> dict:
    if "outline" in job:
        slides = job["outline"]
        return {"storyline": job.get("storyline", ""), "slides": slides}
    if dry_run:
        return {"storyline": f"围绕{job['topic']}逐步展开", "slides": [{"page_no": i + 1, "title": f"{job['topic']} - 第{i+1}页", "subtitle": "", "purpose": "支撑叙事", "layout_type": "content", "key_blocks": []} for i in range(int(job["page_count"]))]}
    prompt = load_prompt_template("Outline Generation Prompt")
    payload = call_text_model(config.text_model, [{"role": "user", "content": prompt.format(requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False), page_count=job["page_count"]) }])
    if isinstance(payload, dict):
        return payload
    raise ValueError("Invalid outline payload")
```

- [ ] **Step 4: Stage 3：slide prompt 阶段（保留 `job.slides` 回填）**
```python
# scripts/pipeline/stage_slide_prompts.py
from __future__ import annotations

from ..llm.config import LLMConfig
from ..llm import call_text_model
from ..references import load_prompt_template
from ..utils import build_requirement_summary
import json

def run_stage(job: dict, config: LLMConfig, master_style: dict, outline_payload: dict, *, style_header: str = "", dry_run=False) -> dict:
    if "slides" in job:
        return {"slides": job["slides"]}
    if dry_run:
        slides = []
        for slide in outline_payload.get("slides", []):
            slides.append({"page_no": slide["page_no"], "title": slide["title"], "slide_role": slide.get("purpose", ""), "key_blocks": slide.get("key_blocks", []), "image_prompt": f"{style_header}\n\n{slide['title']}"})
        return {"slides": slides}
    prompt = load_prompt_template("Per-Slide Prompt Generation Prompt")
    raw = call_text_model(config.text_model, [{"role": "user", "content": prompt.format(requirement_json=json.dumps(build_requirement_summary(job), ensure_ascii=False), master_style_json=json.dumps(master_style, ensure_ascii=False), outline_json=json.dumps(outline_payload, ensure_ascii=False), style_header=style_header)}])
    return raw
```

- [ ] **Step 5: Stage 4：render + stage 5：assemble 封装**
```python
# scripts/pipeline/stage_render.py
from __future__ import annotations

from pathlib import Path
from ..llm.config import LLMConfig
from ..llm.image import build_image_provider, ImageRenderRequest
from ..llm.errors import UnsupportedFeatureError
from ..utils import create_placeholder_image

def run_stage(job: dict, config: LLMConfig, slide_prompts: dict, output_dir: Path, *, dry_run=False):
    image_dir = output_dir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    provider = build_image_provider(config, model=config.image_model)
    out = []
    for slide in slide_prompts["slides"]:
        target = image_dir / f"slide_{int(slide['page_no']):02d}.png"
        if dry_run:
            create_placeholder_image(slide.get("title", ""), int(slide["page_no"]), target)
        else:
            request = ImageRenderRequest(prompt=slide["image_prompt"], aspect_ratio=config.aspect_ratio, resolution=config.resolution)
            target.write_bytes(provider.render(request))
        out.append(target)
    return out
```

```python
# scripts/pipeline/stage_assemble.py
from __future__ import annotations

from pathlib import Path
from assemble_pptx import assemble_pptx

def run_stage(image_paths: list[Path], output_dir: Path, *, pptx_name="deck.pptx") -> Path:
    pptx_path = output_dir / pptx_name
    assemble_pptx(image_paths, pptx_path)
    return pptx_path
```

- [ ] **Step 6: 重写 run_ppt_job 为 orchestrator（最小化）**
```python
# scripts/run_ppt_job.py（核心结构）
from pipeline import stage_master_style, stage_outline, stage_slide_prompts, stage_render, stage_assemble
from pipeline.manifest import load_manifest, write_manifest, manifest_path

# ... load job, config, output_dir 逻辑沿用旧结构
# ... 组装顺序
master_style = stage_master_style.run_stage(job, config, client=client, dry_run=args.dry_run)
write_json(output_dir / "master_style.json", master_style)

outline_payload = stage_outline.run_stage(job, config, dry_run=args.dry_run)
write_json(output_dir / "outline.json", outline_payload)
if not auto_or_review_mode_continue(...): return 0
slide_prompts = stage_slide_prompts.run_stage(job, config, master_style, outline_payload, style_header="", dry_run=args.dry_run)
write_json(output_dir / "slide_prompts.json", slide_prompts)
if not auto_or_review_mode_continue(...): return 0
images = stage_render.run_stage(job, config, slide_prompts, output_dir, dry_run=args.dry_run)
pptx_path = stage_assemble.run_stage(images, output_dir, pptx_name=job.get("output", {}).get("pptx_filename", "deck.pptx"))
```

- [ ] **Step 7: 保持 API 兼容（单页脚本改造）**
```python
# scripts/regenerate_single_slide.py
from llm.image import build_image_provider
# 替换旧 httpx 路径到 build_image_provider，生成 request.payload 时只保留通用字段
```
```python
# scripts/render_single_slide_ppt.py
# 将文本/图像模型调用改成 call_text_model/build_image_provider
```

- [ ] **Step 8: 更新 `review_job_status.py` 显示新阶段产物**
```python
# 新增：检查 artifacts 中 outline/page_intent/slide_prompts/images/manifest 是否存在
```

- [ ] **Step 9: 完成 `prompt-templates.md` 对齐 Stage 3 风格注入参数**
- 将 `Per-Slide Prompt Generation Prompt` 增补 `style_header` 占位。
- 增加 `slide_prompt_from_content_block` 注释，提醒禁止样式信息重复。

- [ ] **Step 10: 本任务验收（不联网）**
```bash
python scripts/run_ppt_job.py /tmp/example-job.json --dry-run
python scripts/review_job_status.py /tmp/example-job.json
```
Expected: 产物目录出现 `master_style.json outline.json slide_prompts.json images/ deck.pptx`（dry-run可为占位输出）。

- [ ] **Step 11: 运行测试与提交**
```bash
git add ppt-maker-with-image/scripts/pipeline ppt-maker-with-image/scripts/run_ppt_job.py ppt-maker-with-image/scripts/regenerate_single_slide.py ppt-maker-with-image/scripts/render_single_slide_ppt.py ppt-maker-with-image/scripts/review_job_status.py ppt-maker-with-image/references/prompt-templates.md ppt-maker-with-image/references/workflow.md
git commit -m "feat(ppt-maker-with-image): stage-based pipeline and llm abstraction"
```

---

### 任务 3: Stage 2 — 视觉一致性（STYLE_HEADER + 首帧锚定 + manifest 能力日志）

**Files:**
- 新增: `ppt-maker-with-image/scripts/style/header.py`
- 修改: `ppt-maker-with-image/scripts/pipeline/stage_master_style.py`
- 修改: `ppt-maker-with-image/scripts/pipeline/stage_slide_prompts.py`
- 修改: `ppt-maker-with-image/scripts/pipeline/stage_render.py`
- 修改: `ppt-maker-with-image/scripts/pipeline/stage_assemble.py`
- 修改: `ppt-maker-with-image/scripts/run_ppt_job.py`
- 修改: `ppt-maker-with-image/assets/example-job.json`
- 修改: `ppt-maker-with-image/assets/ppt_job_template.json`
- 修改: `ppt-maker-with-image/assets/single_slide_job_template.json`
- 新增: `ppt-maker-with-image/tests/test_style_header.py`
- 新增: `ppt-maker-with-image/tests/test_render_reference.py`

- [ ] **Step 1: 实现可复用 deterministic STYLE_HEADER 渲染器**
```python
# scripts/style/header.py
from __future__ import annotations

import json

def render_style_header(master_style: dict) -> str:
    return (
        "以下为本套页统一风格约束，请勿在下面内容里再次定义颜色/字体/布局尺度\n"
        + json.dumps(
            {
                "palette": master_style.get("color_strategy", {}),
                "typography": master_style.get("typography", {}),
                "spacing": master_style.get("spacing", {}),
                "layout_patterns": master_style.get("module_layout_patterns", []),
                "forbidden_elements": master_style.get("forbidden_elements", []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
```

- [ ] **Step 2: 在 `stage_master_style` 产物中固化必要字段默认与缺省**
- 输出 `master_style.visual_positioning/deck_voice/color_strategy.typography/title_hierarchy_rules/module_layout_patterns/forbidden_elements`。

- [ ] **Step 3: 在 `stage_slide_prompts` 组装 `image_prompt = STYLE_HEADER + content`**
```python
# stage_slide_prompts.py
image_prompt = f"{style_header}\n\n=== 本页内容 ===\n{content_block}"
```

- [ ] **Step 4: 实现 reference image 兼容机制**
```python
# stage_render.py 关键片段
if idx > 0 and consistency.get("use_reference_image") and provider.supports_reference_images:
    # 强制始终从 slide_01 取参照，不使用相邻滑动窗口
```
- 如果 provider 不支持，写 manifest: `provider_capabilities.reference_images: false`

- [ ] **Step 5: `manifest.json` 增加 seed 与能力记录**
```python
# manifest schema
{
  "seed": 123456,
  "provider": "openrouter/...",
  "provider_capabilities": {"supports_reference_images": false, "supports_seed": true}
}
```

- [ ] **Step 6: 更新示例与模板默认一致性字段**
- 为 `example-job.json` 添加 `consistency` 字段并默认 `use_reference_image: false`。

- [ ] **Step 7: 小范围测试**
```bash
cat <<'PY' > /tmp/check_header.py
from scripts.style.header import render_style_header
print(render_style_header({'color_strategy': {'background': '#fff'}, 'typography': {'title_font': 'Microsoft YaHei'}})[:120])
PY
python /tmp/check_header.py
```
Expected: 输出包含 `palette`、`typography` 等 JSON 字段。

- [ ] **Step 8: 提交任务 3**
```bash
git add ppt-maker-with-image/scripts/style ppt-maker-with-image/scripts/pipeline/stage_*.py ppt-maker-with-image/scripts/pipeline/man
git commit -m "feat(ppt-maker-with-image): enforce deterministic STYLE_HEADER and consistency manifest"
```

---

### 任务 4: Stage 3 — 内容重构（page_intent + source_materials）

**Files:**
- 新增: `ppt-maker-with-image/scripts/lib/source_materials.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_page_intent.py`
- 新增: `ppt-maker-with-image/scripts/pipeline/stage_slide_prompts.py`（改造输入为 page_intent）
- 修改: `ppt-maker-with-image/scripts/run_ppt_job.py`（新增 review_mode）
- 修改: `ppt-maker-with-image/scripts/sync_job_artifacts.py`
- 修改: `ppt-maker-with-image/scripts/validate_job.py`
- 修改: `ppt-maker-with-image/scripts/review_job_status.py`
- 修改: `ppt-maker-with-image/assets/ppt_job_template.json`
- 修改: `ppt-maker-with-image/assets/example-job.json`
- 新增: `ppt-maker-with-image/tests/test_source_materials.py`
- 新增: `ppt-maker-with-image/tests/test_stage_page_intent.py`

- [ ] **Step 1: 实现 source materials loader**
```python
# scripts/lib/source_materials.py
from __future__ import annotations

from pathlib import Path


def load_source_materials(entries: list[dict], root_dir: Path) -> dict[str, object]:
    out = {}
    for item in entries:
        sid = item["id"]
        typ = item["type"]
        if typ == "text":
            out[sid] = str(item["content"]) 
        elif typ == "file":
            p = (root_dir / item["path"]).expanduser().resolve()
            out[sid] = p.read_text(encoding="utf-8")
        elif typ == "data":
            out[sid] = item["content"]
        else:
            raise ValueError(f"unsupported source type: {typ}")
    return out
```

- [ ] **Step 2: 实现 page_intent 阶段**
```python
# scripts/pipeline/stage_page_intent.py
from __future__ import annotations

import json
from ..llm import call_text_model
from ..references import load_prompt_template
from ..lib.source_materials import load_source_materials


def run_stage(job: dict, config, outline_payload: dict, *, dry_run=False):
    materials = job.get("source_materials", [])
    loaded = load_source_materials(materials, Path(job["_job_dir"])) if materials else {}
    if job.get("page_intent"):
        return {"storyline": job.get("storyline", ""), "slides": job["page_intent"]}
    if dry_run:
        return {"storyline": outline_payload.get("storyline", ""), "slides": []}
    prompt = load_prompt_template("Page Intent Generation Prompt")
    payload = call_text_model(config.text_model, [{"role": "user", "content": prompt.format(source_materials_json=json.dumps(loaded, ensure_ascii=False), outline_json=json.dumps(outline_payload, ensure_ascii=False))}])
    return payload
```

- [ ] **Step 3: 更新 run_ppt_job 的 review_mode 分支**
- `full`: outline stop -> page_intent stop -> slide_prompts stop
- `fast`: outline stop only
- `auto`: no stop

- [ ] **Step 4: sync_job_artifacts 接受并同步 page_intent**
- 读取 `page_intent.json` 并回写到 `job["page_intent"]`。
- 增加 `--approve-page-intent` 标志。

- [ ] **Step 5: validate_job 增加 schema 级校验规则**
- 允许 `source_materials` 为空。
- 若存在则要求 `id/type` 合法并且 `type=file` path 存在。

- [ ] **Step 6: review 状态展示 page_intent 信息**
- 在 `review_job_status.py` 增加 `page_intent.json` 缺失/存在提示。

- [ ] **Step 7: 本任务提交**
```bash
git add ppt-maker-with-image/scripts/lib/source_materials.py ppt-maker-with-image/scripts/pipeline/stage_page_intent.py ppt-maker-with-image/scripts/run_ppt_job.py ppt-maker-with-image/scripts/sync_job_artifacts.py ppt-maker-with-image/scripts/validate_job.py ppt-maker-with-image/scripts/review_job_status.py
git commit -m "feat(ppt-maker-with-image): add page_intent + source_materials + review_mode"
```

---

### 任务 5: 文档与兼容收口

**Files:**
- 修改: `ppt-maker-with-image/README.md`
- 修改: `ppt-maker-with-image/SKILL.md`
- 修改: `ppt-maker-with-image/references/model-config.md`
- 修改: `ppt-maker-with-image/references/workflow.md`
- 新增: `ppt-maker-with-image/references/faq-migration.md`
- 修改: `docs/superpowers/specs/2026-04-28-ppt-maker-with-image-redesign-design.md`（回写新 plan 状态）

- [ ] **Step 1: 更新 README 执行入口与 provider 示例**
- 增加 OpenAI/Azure/Ollama/Gemini 示例、环境变量说明、`review_mode` 示例。

- [ ] **Step 2: SKILL 与工作流文档同步**
- `read references/workflow.md` 前后文保持一致。
- 明确 6 阶段与 3 类 review_mode。

- [ ] **Step 3: model-config 文档化 providers 约定**
- 明确 provider/model 写法与 overrides。

- [ ] **Step 4: 迁移说明文件**
- 说明旧 `outline_approved` / `prompts_approved` 过渡行为和过期策略。

- [ ] **Step 5: 提交文档收口**
```bash
git add ppt-maker-with-image/README.md ppt-maker-with-image/SKILL.md ppt-maker-with-image/references/*.md docs/superpowers/specs/2026-04-28-ppt-maker-with-image-redesign-design.md
git commit -m "docs(ppt-maker-with-image): update migration and review_mode docs"
```

---

### 任务 6: 逐步交付验收（无需外部联网）

- [ ] **Step 1: 干运行验收**
```bash
cp ppt-maker-with-image/assets/example-job.json /tmp/example-job.json
python ppt-maker-with-image/scripts/run_ppt_job.py /tmp/example-job.json --dry-run
python ppt-maker-with-image/scripts/review_job_status.py /tmp/example-job.json
```
Expected: 输出目录完整，且 `master_style.json` `outline.json` `slide_prompts.json`/`page_intent.json`（取决于 mode）都存在。

- [ ] **Step 2: 全量 review_mode 验证**
```bash
python ppt-maker-with-image/scripts/run_ppt_job.py /tmp/example-job.json --review-mode full --output-dir /tmp/artifacts --dry-run
python ppt-maker-with-image/scripts/run_ppt_job.py /tmp/example-job.json --review-mode fast --output-dir /tmp/artifacts2 --dry-run
python ppt-maker-with-image/scripts/run_ppt_job.py /tmp/example-job.json --review-mode auto --output-dir /tmp/artifacts3 --dry-run
```
Expected: 三类停止点行为一致。

- [ ] **Step 3: provider 降级回退行为检查（静态）**
- 将 image provider 配置切到不支持 seed/reference 的适配器，观察 `manifest.json` 中 capability 字段。

- [ ] **Step 4: 最终交付提交（按里程碑合并）**
```bash
git push origin "$(git branch --show-current)"
```

---

### 自检（计划自身）

- [ ] **Spec coverage check:** 每个设计节（LLM universality / STYLE_HEADER / reference image / page_intent / review_mode / manifest）均有对应任务。
- [ ] **Placeholder scan:** 计划正文无 `TODO/TBD` / “待完成” 等占位语句。
- [ ] **Type consistency check:** `run_stage(job, config, ...)` 的参数命名在各任务保持一致。

### 里程碑提交建议（最终）

- `feat: add llm abstraction scaffolding`
- `feat: stage-based pipeline and orchestrator`
- `feat: enforce style header consistency and manifest`
- `feat: add page_intent and source materials`
- `docs: update pipeline docs and migration notes`

**Plan complete and saved to `docs/superpowers/plans/2026-04-28-ppt-maker-with-image-redesign-implementation.md`. Two execution options:**

**1. Subagent-Driven (recommended)** — dispatchs per task with two-stage review

**2. Inline Execution** — execute tasks in this session using executing-plans with checkpoints

**Which approach?**
