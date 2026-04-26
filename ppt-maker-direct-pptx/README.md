# ppt-maker-direct-pptx

直接生成**可编辑 PowerPoint** 的 Codex/Agent skill。先逐项确认需求、风格、大纲、每页意图，再用 PptxGenJS / python-pptx 直接绘制原生文本框、形状、卡片、KPI 条、流程、矩阵等元素到 `.pptx`，所有内容都是 PowerPoint / Keynote 里**可二次编辑**的对象——不是图片切片。

## 使用场景

- **季度业务回顾 / 经营复盘**：KPI 横条 + 双栏对照 + 总结要点，三五张内讲清结论。
- **产品方案与解决方案介绍**：架构分层 + 四卡矩阵 + 三阶段路线图，结构化呈现能力 → 方案 → 价值。
- **市场宣传 / 活动推广**：封面冲击 + 卖点矩阵 + 案例墙，强调主张和转化路径。
- **内部周会 / 月会 / 项目复盘**：进展条 + 决策项 + 行动跟踪，管理视角清晰。
- **英文董事会 / 投资人汇报**：深色商务风、英文复盘、克制的高管语气。
- **批量产出风格统一的 deck**：一次定义 master_style，跨多份 deck 保持配色 / 字号 / 模块布局一致。
- **要求最终甲方可编辑**：所有元素都是原生 PPT 对象，客户拿到后能直接改文案、改配色、改布局。

## 主要功能

### 1 · 七道确认闸的工作流

```
1 需求确认  →  2 模板/风格  →  3 风格预览  →  4 大纲  →  5 页面意图  →  6 图片计划  →  7 渲染前总结  →  渲染
```

每道闸都有显式的"放行 / 不放行"规则，缺字段、Lint fail、状态不对都会被拦下。
完整文档见 [`references/v2-flow.md`](./references/v2-flow.md)。

### 2 · 风格系统：预设 / NL 生成 / 参考素材

- **5 个内置预设**：慧新通用、慧新-产品方案、慧新-市场宣传、慧新-内部会议、深色英文商务。
- **自然语言生成新风格**：`define_style.py nl --description "深蓝紫色赛博朋克科技风"` →  LLM 直出符合 schema 的 master_style。
- **参考素材抽取**：上传 PNG / PPT 截图，自动抽 5-7 色 palette + LLM 补 typography/forbidden_elements。
- **继承 + 覆盖**：选 `huixin` 但把主色换成 `#1A237E`，其他保留。

### 3 · 12 个 Layout Pattern + Slot 校验

每页选一个 pattern + 填槽位（`max_chars / required` 都可机检），不再"自由写文案让模型猜布局"：

`cover` · `section_divider` · `conclusion_top_modules` · `two_column_compare` · `four_card_matrix` · `three_stage_path` · `kpi_strip` · `architecture_layers` · `before_after` · `evidence_grid` · `summary_takeaways` · `freeform`（自由式兜底）

### 4 · Deterministic Python 渲染器

12 个 pattern 各有一个用 python-pptx 写的渲染函数，**不调 LLM、不依赖 Node**，slot 数据原样进 PPT。LLM 驱动的 PptxGenJS 路径仍然保留作为兜底（用于 freeform 页面）。

### 5 · 双层预览（不用打开 PPT 就能看）

- **Pattern 目录预览**：每次切风格自动重渲 12 个 pattern 的 SVG 缩略图。
- **每页 wireframe**：page intent 写好就生成低保真 SVG，提前看真实 slot 数据撑不撑得开 layout。

### 6 · 自动质量检查 + auto-fix

4 类 lint 嵌入闸口：

| 类别 | 检查内容 |
|---|---|
| Schema | 字段齐全、page_no 不重、pattern_id 已知、image_status 合法 |
| 布局几何 | 区域不重叠、不超出 16:9、卡片高度 ≥ 1.0 inch、字号在 master_style 范围 |
| 风格一致性 | 配色只用 palette、字号统一、forbidden_elements 没出现 |
| 内容质量 | 一页一个 core_message、跨页相似度、受众契合度（LLM judge，可关） |

可机修的 fail（区域剪裁 / 配色就近 snap / 字号 clamp）支持一键 `auto_fix_lint.py`。

### 7 · 状态机（断点续做）

每页 3 个独立状态层：`outline_status` / `intent_status` / `image_status`。每个 image_placeholder 也有 5 态状态机（`pending / placeholder / generated / skipped / regenerating`）——首次渲染不调图模型、用样式化占位框；交付后用户挑哪几页要真图、按页触发生成。详见 [`references/state-machines.md`](./references/state-machines.md)。

### 8 · 任意 OpenAI 兼容 LLM

OpenAI / Azure / OpenRouter / Groq / Together / DeepSeek / vLLM / Ollama / LiteLLM proxy 都直接支持。详见 [`references/byo-llm-providers.md`](./references/byo-llm-providers.md)。

---

## 安装

### 从仓库安装

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
```

只想要这一套 skill：

```bash
git clone https://github.com/chrisopal/skills.git /tmp/chrisopal-skills
cp -R /tmp/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
```

### 装运行依赖

```bash
cd ~/.codex/skills/ppt-maker-direct-pptx
python3 -m pip install -r assets/python_requirements.txt
```

LLM-driven JS 渲染路径需要 Node 和 npm（deterministic Python renderers 不需要）：

```bash
node -v   # ≥ 16
npm -v
```

---

## 配置

### LLM 提供方（任意 OpenAI 兼容端点）

设置 3 个环境变量即可：

```bash
export LLM_API_KEY="<your-key>"
export LLM_BASE_URL="<base-url>"
export LLM_TEXT_MODEL="<model-id>"
```

常见配置：

| 提供方 | LLM_BASE_URL | LLM_TEXT_MODEL 示例 |
|---|---|---|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |
| OpenRouter | `https://openrouter.ai/api/v1` | `anthropic/claude-3.5-sonnet` |
| Azure OpenAI | `https://<resource>.openai.azure.com/openai/deployments/<deployment>` | （用 deployment id） |
| Groq | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| Together | `https://api.together.ai/v1` | `Qwen/Qwen2.5-72B-Instruct-Turbo` |
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| vLLM (本地) | `http://localhost:8000/v1` | （服务端配置的 model name） |
| Ollama | `http://localhost:11434/v1` | `qwen2.5:14b` |
| LiteLLM 代理 | `http://localhost:4000/v1` | （路由到任一后端） |

老用户：`OPENROUTER_API_KEY` / `OPENROUTER_BASE_URL` 仍然作为 fallback 工作，无需迁移。
完整 9 个 provider 的 ready-to-paste 配置在 [`references/byo-llm-providers.md`](./references/byo-llm-providers.md)。

### `assets/model_config.yaml`

可选字段：

```yaml
text_model: "gpt-4o-mini"          # 必填
pptx_js_model: "gpt-4o-mini"        # 不填则继承 text_model
image_model: "dall-e-3"             # 选填，仅图片生成需要
image_size: "1024x1024"             # 选填
provider: "openai"                  # 选填，不填会从 base_url 推断
image_route: "images_api"           # 选填：images_api / chat
language: "zh-CN"
```

图片生成路径（`images_api` 走 `/v1/images/generations`，`chat` 走 `/v1/chat/completions` 加图消息）会从 base_url 自动推断；OpenAI / Azure 默认 `images_api`，OpenRouter / Anthropic 默认 `chat`。

### 模板选择

5 个内置预设（也可继续在 `assets/template_manifest.json` 注册新预设）：

- `huixin`：通用商务咨询风
- `huixin-product-solution`：产品方案介绍
- `huixin-market-promo`：市场宣传 / 活动
- `huixin-internal-meeting`：内部周会 / 月会
- `dark-english-business`：深色英文商务

不想用预设？用 `define_style.py nl` / `define_style.py reference` 自己生成或抽取一套。

---

## 工作流速查

### A · 七道闸全自动（推荐用于演示和小 deck）

```bash
python3 scripts/run_ppt_job_v2.py path/to/job.json --auto-approve
python3 scripts/render_pptx_from_intents.py \
  --slide-prompts artifacts/slide_prompts.json \
  --master-style artifacts/master_style.json \
  --output deck.pptx
```

`scripts/run_ppt_job_v2.py` 走完 7 道闸（生成 master_style / pattern catalog / wireframes / lint report / dashboard），渲染走 deterministic Python pattern renderers，不需要 Node 和 LLM。

复用本仓库的演示 job：

```bash
python3 scripts/run_ppt_job_v2.py e2e-demo/job.json --auto-approve
python3 scripts/render_pptx_from_intents.py \
  --slide-prompts e2e-demo/artifacts/slide_prompts.json \
  --master-style e2e-demo/artifacts/master_style.json \
  --output e2e-demo/artifacts/fy26q1-review.pptx
```

### B · 经典 4 闸 + LLM-driven JS 渲染（适合大 deck / 自定义复杂页）

```bash
# 1. 准备 job.json（必填字段：topic / target_audience / purpose / style / page_count / key_points）
cp assets/ppt_job_template.json /tmp/my_ppt_job.json

# 2. 跑到大纲闸
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json
#    → 检查 artifacts/<dir>/outline.json，调整后回写：
python3 scripts/sync_job_artifacts.py /tmp/my_ppt_job.json --approve-outline

# 3. 跑到页面意图闸
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json
#    → 检查 slide_prompts.json，调整后回写：
python3 scripts/sync_job_artifacts.py /tmp/my_ppt_job.json --approve-prompts

# 4. 渲染最终 PPTX
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json
```

一次性跑通（适合 demo）：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json \
  --auto-approve-outline --auto-approve-prompts
```

本地排版烟测（不调任何模型）：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json \
  --dry-run --auto-approve-outline --auto-approve-prompts
```

### C · 单页直出（fast path）

```bash
python3 scripts/render_single_slide_ppt.py \
  --prompt "生成一页人形机器人智能工厂总体解决方案蓝图..." \
  --template-id huixin-product-solution \
  --title "智能工厂蓝图"
```

### D · 单页重生成 / 局部修改

```bash
python3 scripts/regenerate_single_slide.py /tmp/my_ppt_job.json \
  --page-no 3 \
  --instruction "改为左右对照布局，减少文字密度"
```

只重写提示词、不渲染：加 `--prompt-only`。

### E · 自定义风格

```bash
# 自然语言生成
python3 scripts/define_style.py nl --description "深蓝紫色赛博朋克科技风"

# 参考图抽取（任意 PNG / PPT 截图）
python3 scripts/define_style.py reference --file ./reference.png

# 继承预设 + 改色
python3 scripts/define_style.py preset --id huixin \
  --override 'color_strategy.primary_green=#1A237E'
```

输出统一写到 `artifacts/master_style.json`。

### F · 状态查询 + Dashboard

```bash
# 看每页 outline / intent / image 状态 + lint 摘要
python3 scripts/dashboard.py path/to/job.json

# JSON 格式（用于编程读取）
python3 scripts/dashboard.py path/to/job.json --json

# 看缺哪些产物 / 下一步建议
python3 scripts/review_job_status.py /tmp/my_ppt_job.json
```

### G · 状态批量切换

```bash
# 批量锁页（intent 层）
python3 scripts/lock_pages.py --pages 1,3-5,7 --layer intent \
  --slide-prompts artifacts/slide_prompts.json

# 批量重置 needs_rework
python3 scripts/reset_pages.py --pages 4 --layer intent \
  --slide-prompts artifacts/slide_prompts.json

# 单图重生（标记 status=regenerating，下次 generate_image_assets 会处理）
python3 scripts/regenerate_image.py \
  --slide-specs artifacts/slide_specs.json \
  --slide 5 --img-id page-05-img-1
```

### H · Lint 与 auto-fix

```bash
# 跑某道闸的 lint，写入 artifacts/lint_report.json
python3 scripts/run_all_lints.py --gate gate_7 \
  --slide-specs artifacts/slide_specs.json \
  --master-style artifacts/master_style.json \
  --slide-prompts artifacts/slide_prompts.json \
  --outline artifacts/outline.json \
  --update-state    # 把 fail 页自动切到 needs_rework

# 自动修可修的 fail（剪裁区域 / snap 配色 / clamp 字号）
python3 scripts/auto_fix_lint.py \
  --report artifacts/lint_report.json \
  --slide-specs artifacts/slide_specs.json \
  --master-style artifacts/master_style.json \
  --slide-prompts artifacts/slide_prompts.json
```

详见 [`references/lint-rules.md`](./references/lint-rules.md)。

### I · 图片资产生成

```bash
# 默认：扫描所有 image_placeholder
python3 scripts/generate_image_assets.py \
  --slide-specs artifacts/slide_specs.json \
  --master-style artifacts/master_style.json

# 状态机感知：只跑 status=pending / regenerating
python3 scripts/generate_image_assets.py --respect-status ...

# 指定几张图
python3 scripts/generate_image_assets.py --ids page-05-img-1,page-08-img-2 ...

# 本地占位 PNG（不调图模型）
python3 scripts/generate_image_assets.py --dry-run ...
```

---

## 产物结构

```
artifacts/<dir>/
├── master_style.json        # 风格定义（预设 / NL / 参考图三选一）
├── outline.json             # 大纲（含 outline_status 状态机）
├── slide_prompts.json       # 每页 pattern_id + slots + intent_status
├── slide_specs.json         # 渲染规约 + image_placeholder 状态机
├── lint_report.json         # 最近一次 lint 结果
├── pattern_catalog/<hash>/  # 风格 × 12 pattern 缩略图
├── wireframes/page-NN.svg   # 每页低保真 wireframe
├── images/                  # 真实图片资产（调过图模型）
├── slides/                  # LLM-driven JS 模块（legacy 路径）
└── deck.pptx                # 最终可编辑 PowerPoint
```

---

## 常见问题

- **缺需求字段** → 先补齐 `topic / target_audience / purpose / style / page_count / key_points`，并设置 `requirement_confirmed=true`。
- **没确认模板** → 填 `template_id` 和 `template_name`，或按推荐结果 `--approve-outline`。
- **JS 模型生成的页面验证失败** → 脚本会 warn + 降级到 deterministic editable layout，整套 deck 仍然产出；想避开 LLM 直接用 v2 + `render_pptx_from_intents.py`。
- **图片 API 失败** → 写本地占位 PNG + 在 manifest 写 `fallback_reason`；用 `regenerate_image.py` 重试。
- **PPT 文字重叠** → 优先改 `slide_prompts.json` 的 pattern + slots，超 `max_chars` 会被 lint 拦下；改完跑 `regenerate_single_slide.py`。
- **不想花图模型额度** → `--image-dry-run` 或 `generate_image_assets.py --dry-run`，整 deck 用样式化占位框交付。
- **换 LLM 提供方** → 改环境变量 `LLM_API_KEY` / `LLM_BASE_URL` / `LLM_TEXT_MODEL`，密钥不要进 Git。

---

## 文档导航

| 想做什么 | 看哪份 |
|---|---|
| 快速理解全流程 | [`references/v2-flow.md`](./references/v2-flow.md) |
| 配第三方 LLM 提供方 | [`references/byo-llm-providers.md`](./references/byo-llm-providers.md) |
| 看每页 / 图片状态机规则 | [`references/state-machines.md`](./references/state-machines.md) |
| 看每条 lint 规则和 auto-fix 能力 | [`references/lint-rules.md`](./references/lint-rules.md) |
| 看模板预设详情 | [`references/template-presets.md`](./references/template-presets.md) |
| 看模型角色 | [`references/model-config.md`](./references/model-config.md) |
| 看对话模式（不靠 job.json） | [`references/conversational-mode.md`](./references/conversational-mode.md) |
| 看 prompt 模板 | [`references/prompt-templates.md`](./references/prompt-templates.md) |

设计稿与实施计划（仓库根目录）：

- `docs/plans/2026-04-25-ppt-direct-pptx-optimization-design.md`
- `docs/plans/2026-04-25-ppt-direct-pptx-optimization-implementation.md`
