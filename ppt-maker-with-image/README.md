# ppt-maker-with-image

这是一个可复用的“图片优先 PPT 生成” skill：先把需求拆成结构化阶段产物，再生成每页图片，最后组装为 `.pptx`。它适合咨询汇报、经营分析、产品总结、方案介绍等需要强视觉一致性的中文 PPT。

当前版本的核心目标是：

1. 确认优先：大纲、逐页提示词和视觉参考策略都可在人确认后继续。
2. 图片优先：每页先生成高质量页面图片，再按图片尺寸嵌入 PPT。
3. 风格一致：支持把第一页作为后续页面的视觉参考传给支持该能力的图像模型。
4. 提示词安全：渲染前会清理设计规格中的尺寸数字、`px`、`pt`、间距标签、caption 标注等，避免这些内容出现在最终图片上。
5. 可恢复：每个阶段都会落盘 JSON，支持人工编辑、同步、单页重生成和状态检查。

## 目录结构

- `SKILL.md`：技能定义与工作流入口
- `agents/openai.yaml`：UI 元数据
- `assets/example-job.json`：最小多页任务示例
- `assets/ppt_job_template.json`：多页任务模板
- `assets/single_slide_job_template.json`：单页任务模板
- `assets/huixin_template.json`：慧新模板预设
- `assets/huixin_master_style_brief.json`：慧新完整母版约束
- `assets/model_config.yaml`：文本与图片模型配置
- `references/workflow.md`：阶段化执行说明
- `references/prompt-templates.md`：提示词模板与边界约束
- `scripts/`：从 `job.json` 到图片与 `pptx` 的工具链
- `tests/`：pipeline、LLM fallback、提示词清洗、PPT 组装等回归测试

## 安装

### Codex

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/chrisopal/skills.git ~/.codex/skills/chrisopal-skills
ln -sfn ~/.codex/skills/chrisopal-skills/ppt-maker-with-image ~/.codex/skills/ppt-maker-with-image
```

### Claude Code

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/chrisopal/skills.git ~/.claude/skills/chrisopal-skills
ln -sfn ~/.claude/skills/chrisopal-skills/ppt-maker-with-image ~/.claude/skills/ppt-maker-with-image
```

## Python 依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r assets/python_requirements.txt
```

如需真实调用模型，请配置：

```bash
export OPENROUTER_API_KEY=...
export OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
```

## 多页生成流程

先复制并修改示例：

```bash
cp assets/example-job.json /tmp/example-job.json
```

然后执行：

```bash
python scripts/run_ppt_job.py /tmp/example-job.json
```

pipeline 会按阶段输出：

1. `master_style.json`：整套 PPT 的视觉母版、版式节奏和设计约束。
2. `outline.json`：页数、标题、每页讲述目标和内容分配。
3. `page_intent.json`：逐页意图、重点信息、图表/布局建议。
4. `slide_prompts.json`：每页图像生成提示词。
5. `images/*.png`：逐页图片。
6. `render_metadata.json`：图像生成 provider、参考图、seed/fallback 等元数据。
7. `deck.pptx`：最终 PowerPoint 文件。
8. `manifest.json`：完整产物清单和运行状态。

如果想一次走完确认点，可以使用：

```bash
python scripts/run_ppt_job.py /tmp/example-job.json --auto-approve-outline --auto-approve-prompts
```

## 确认点与参考图策略

生成图片前，skill 会把“是否把第一页作为视觉参考传给大模型”作为显式策略处理。推荐配置在 `job.json` 中：

```json
{
  "consistency": {
    "use_reference_image": true,
    "reference_source": "first_slide"
  }
}
```

行为说明：

- 第 1 页正常生成，不引用自身。
- 第 2 页及之后会优先使用 `images/slide_01.png` 作为视觉参考。
- OpenRouter 图像接口支持参考图时会传入参考图。
- provider 不支持 `seed` 时会自动丢弃 seed，不阻塞生成。
- provider 不支持参考图时会按能力降级，并在 `render_metadata.json` 中记录。

## 提示词清洗与图片质量保护

为避免设计规格误入图片，渲染边界会自动清洗 renderer-facing prompt：

- 去除 `40-56px`、`20-28px`、`12-14px` 等尺寸标注。
- 去除 `px`、`pt`、`R=12`、`margin`、`spacing`、`caption` 等原始设计规格。
- 保留设计意图，例如层级、留白、卡片结构、商务科技风、品牌色。
- 单页重生成和 `render_single_slide_ppt.py` 也复用同一套清洗策略。

这能防止“尺寸数字”“红框标注”“Caption: 12-14px”这类设计说明被模型当成画面内容生成出来。

## 人工修改后回写

如果你已经人工编辑过 `outline.json` 或 `slide_prompts.json`：

```bash
python scripts/sync_job_artifacts.py /tmp/example-job.json --approve-outline --approve-prompts
```

同步后继续运行 `run_ppt_job.py`，pipeline 会复用已确认产物。

## 单页重生成

```bash
python scripts/regenerate_single_slide.py /tmp/example-job.json --page-no 2 --instruction "改成更明显的双栏对照"
```

单页重生成会沿用：

- 当前 `master_style.json`
- 当前 `page_intent.json`
- 当前提示词清洗规则
- 当前参考图策略
- 当前 provider 能力 fallback

## 单页直出示例

直接用命令行 prompt：

```bash
python scripts/render_single_slide_ppt.py \
  --prompt "中文PPT页面，白底，双栏布局，左侧问题，右侧方案，正式商务科技风。" \
  --template-id huixin \
  --title "单页方案页"
```

或者用任务文件：

```bash
python scripts/render_single_slide_ppt.py --job assets/single_slide_job_template.json
```

## 状态检查

```bash
python scripts/review_job_status.py /tmp/example-job.json
```

状态检查会汇总阶段产物、图片数量、PPT 页数、缺失文件和可继续执行的下一步。

## 推荐模板

当前内置了 `慧新` 模板预设，适合：

- 白底咨询风
- 绿色主色 + Teal 辅色
- 信息密度高但结构清晰
- 咨询汇报、经营分析、阶段性进展页

## 稳定性与兼容性

当前 main 版本已经包含以下容错：

- OpenRouter 图片返回 malformed JSON 时自动重试。
- 文本模型 `complete_json` 返回 malformed JSON 时自动重试。
- `master_style` 回流到 job/schema 时兼容缺失字段。
- dry-run 与生产分支共享 pipeline helper，避免阶段行为分叉。
- `outputs/` 是运行时生成目录，不作为源码提交内容。

## 验证状态

最近一次 main 验证：

- `python3 -m pytest -q ppt-maker-with-image/tests`
- staged pipeline 与 `run_ppt_job.py` import smoke
- 真实 OpenRouter 端到端生成曾验证 3 张图片与 3 页 PPT 对齐
