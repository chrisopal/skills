# ppt-maker-direct-pptx

这是一个“确认式 + 页面级 PptxGenJS 直接绘制 PPTX”的 Codex skill。它用于把客户需求逐步转成可编辑 PowerPoint：先确认需求、模板、大纲和每页页面意图，再让模型生成每页独立的 JS 绘制模块，最后组装成 `.pptx`。

## 能做什么

- 需求确认：主题、目标客户、用途、风格、页数、重点内容必须完整。
- 模板确认：支持慧新 4 套模板和深色英文商务样例，也可通过 manifest 继续扩展模板 preset。
- 大纲确认：先生成 `outline.json`，确认后才进入每页内容。
- 页面意图确认：每页包含标题、副标题、核心观点、页面文案、版式、视觉元素、图片占位、图表建议、演讲备注和最终生成提示词。
- 直接绘制 PPTX：最后生成 `slides/slide-XX.js`，用 PptxGenJS 绘制原生文本框、形状、线条、卡片、流程、图表占位和图片占位。
- 图片占位增强：可选调用图片模型生成局部图片资产，并嵌入到预留区域，避免图片压住文本。

## 安装

### 从仓库安装

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
```

如果你只想复制这一套 skill：

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git /tmp/chrisopal-skills
cp -R /tmp/chrisopal-skills/ppt-maker-direct-pptx ~/.codex/skills/ppt-maker-direct-pptx
```

安装后重启或刷新 Codex/Agent 客户端。

### 安装运行依赖

```bash
cd ~/.codex/skills/ppt-maker-direct-pptx
python3 -m pip install -r assets/python_requirements.txt
```

脚本会在需要时为渲染目录准备 `pptxgenjs`。本机需要可用的 `node` 和 `npm`：

```bash
node -v
npm -v
```

## 配置模型

脚本默认通过 OpenRouter 调用文本模型和图片模型。不要把 API key 写进仓库或 job 文件，使用环境变量：

```bash
export OPENROUTER_API_KEY="你的 OpenRouter API Key"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"
```

模型配置在：

```text
assets/model_config.yaml
```

默认配置：

```yaml
text_model: "openai/gpt-5.4-mini"
pptx_js_model: "openai/gpt-5.4-mini"
image_model: "google/gemini-3.1-flash-image-preview"
```

如需换模型，修改 `assets/model_config.yaml` 或运行脚本时传入 `--config path/to/model_config.yaml`。

首次 live 使用前必须确认 `OPENROUTER_API_KEY`、`OPENROUTER_BASE_URL` 和模型 ID 已配置正确。脚本会在 live run 前做 preflight；缺少 API key、Node/npm 或模型配置时会先给出可操作错误。

## 模板

内置慧新模板：

- `huixin`：正式商务科技咨询风，适合通用方案和汇报。
- `huixin-product-solution`：产品及解决方案介绍风，偏能力架构、场景、价值证明。
- `huixin-market-promo`：市场宣传风，偏卖点、价值主张和视觉冲击。
- `huixin-internal-meeting`：内部会议风，偏状态、风险、决策和行动项。
- `dark-english-business`：深色英文商务风，适合英文、全球化、高管、董事会或投资人场景。

模板通过 `assets/template_manifest.json` 注册。新增模板时添加一条 manifest 记录，并提供对应的 `*_template.json` 与 `*_master_style_brief.json`。

## 多页生成

复制 job 模板：

```bash
cp assets/ppt_job_template.json /tmp/my_ppt_job.json
```

至少填写这些字段：

```json
{
  "template_id": "huixin-product-solution",
  "template_name": "慧新-产品及解决方案介绍",
  "requirement_confirmed": true,
  "topic": "人形机器人智能工厂解决方案",
  "target_audience": "制造企业高管、信息化负责人、工厂负责人",
  "purpose": "方案汇报与项目立项沟通",
  "style": "白底，蓝绿灰，正式商务，科技咨询风",
  "page_count": 8,
  "key_points": ["总体蓝图", "业务闭环", "制造执行", "测试质量", "数据智能"],
  "outline_approved": false,
  "prompts_approved": false,
  "output": {
    "directory": "./artifacts/robot-factory",
    "pptx_filename": "robot-factory-solution.pptx"
  }
}
```

执行第一段，会生成大纲并停在确认关口：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json
```

查看 `artifacts/robot-factory/outline.json`，确认或手工调整后回写：

```bash
python3 scripts/sync_job_artifacts.py /tmp/my_ppt_job.json --approve-outline
```

再次执行，会生成每页页面意图与最终生成提示词，并停在提示词确认关口：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json
```

查看 `slide_prompts.json`，确认或修改后回写：

```bash
python3 scripts/sync_job_artifacts.py /tmp/my_ppt_job.json --approve-prompts
```

最后生成可编辑 PPTX：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json
```

如果你想快速端到端测试，可以使用自动确认：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json \
  --auto-approve-outline \
  --auto-approve-prompts
```

本地排版烟测可用 `--dry-run`，不会调用模型：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json \
  --dry-run \
  --auto-approve-outline \
  --auto-approve-prompts
```

## 图片占位与图片生成

当 `slide_prompts.json` 中某页包含 `image_placeholders` 时，skill 会把图片区域写入 `slide_specs.json` 的 `layout_regions.images`，正文和模块会被限制在 `layout_regions.content`。

正式生成图片资产：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json \
  --generate-images
```

只生成本地占位图，用于排版测试：

```bash
python3 scripts/run_ppt_job.py /tmp/my_ppt_job.json \
  --generate-images \
  --image-dry-run
```

也可以单独运行：

```bash
python3 scripts/generate_image_assets.py \
  --slide-specs artifacts/robot-factory/slide_specs.json \
  --master-style artifacts/robot-factory/master_style.json \
  --dry-run
```

## 单页直出

```bash
python3 scripts/render_single_slide_ppt.py \
  --prompt "生成一页人形机器人智能工厂总体解决方案蓝图，五层架构，右侧价值标签，蓝绿灰白底科技咨询风" \
  --template-id huixin-product-solution \
  --title "人形机器人智能工厂总体解决方案蓝图" \
  --output-dir ./artifacts/single-robot-factory
```

使用结构化单页 job：

```bash
cp assets/single_slide_job_template.json /tmp/single_slide_job.json
python3 scripts/render_single_slide_ppt.py --job /tmp/single_slide_job.json
```

## 单页重生成

修改某页页面意图后，只重生第 3 页并重新组装整套 PPTX：

```bash
python3 scripts/regenerate_single_slide.py /tmp/my_ppt_job.json \
  --page-no 3 \
  --instruction "减少文字密度，改为左右对照布局，保留慧新蓝绿灰风格"
```

只重新生成该页提示词，不渲染 PPTX：

```bash
python3 scripts/regenerate_single_slide.py /tmp/my_ppt_job.json \
  --page-no 3 \
  --prompt-only
```

## 状态检查与校验

检查 job 字段和确认状态：

```bash
python3 scripts/validate_job.py /tmp/my_ppt_job.json
```

如果手工改过中间产物，也可以校验 artifacts：

```bash
python3 scripts/validate_job.py /tmp/my_ppt_job.json --artifacts artifacts/robot-factory
```

查看当前缺少什么产物，以及下一步建议：

```bash
python3 scripts/review_job_status.py /tmp/my_ppt_job.json
```

输出 JSON：

```bash
python3 scripts/review_job_status.py /tmp/my_ppt_job.json --json
```

## 产物结构

典型输出目录：

```text
artifacts/robot-factory/
├── master_style.json
├── outline.json
├── slide_prompts.json
├── slide_specs.json
├── image_manifest.json
├── images/
├── slides/
│   ├── slide-01.js
│   ├── slide-02.js
│   └── compile.js
└── robot-factory-solution.pptx
```

## 常见问题

- 如果脚本提示缺少需求字段，先补齐 `topic / target_audience / purpose / style / page_count / key_points`，并设置 `requirement_confirmed=true`。
- 如果未确认模板，先填写 `template_id` 和 `template_name`，或按脚本推荐结果确认后再继续。
- 如果 JS 模型生成的页面模块验证失败，脚本会打印 warning 并降级到 deterministic editable layout，保证整套 PPTX 继续产出。
- 如果图片 API 失败，脚本会打印 warning、生成本地占位 PNG，并在 `image_manifest.json` / `slide_specs.json` 中写入 `fallback_reason`。
- 如果 PPT 页面文字重叠，优先修改 `slide_prompts.json` 的结构化页面意图，减少单页 key blocks 或明确 `image_placeholders` 的位置，再运行单页重生成。
- 如果需要图片但不想花费模型额度，使用 `--image-dry-run` 或 `generate_image_assets.py --dry-run`。
- 如果要换模型，只改环境变量和 `assets/model_config.yaml`，不要把密钥写入 Git。
