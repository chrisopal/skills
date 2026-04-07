# ppt-maker-with-image

这是一个可复用的“图片优先 PPT 生成” skill，适合把完整需求转成：

1. 需求确认
2. 大纲
3. 每页提示词
4. 图片化页面
5. 最终 `.pptx`

它也支持只根据单页提示词生成单页图片和单页 `pptx`。

## 目录结构

- `SKILL.md`：技能定义与工作流
- `agents/openai.yaml`：UI 元数据
- `assets/example-job.json`：最小多页任务示例
- `assets/ppt_job_template.json`：多页任务模板
- `assets/single_slide_job_template.json`：单页任务模板
- `assets/huixin_template.json`：慧新模板预设
- `assets/huixin_master_style_brief.json`：慧新完整母版约束
- `scripts/`：从 `job.json` 到图片与 `pptx` 的工具链
- `references/`：prompt 模板、模板预设、工作流说明

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

## 最小多页示例

先复制并修改示例：

```bash
cp assets/example-job.json /tmp/example-job.json
```

然后执行：

```bash
python scripts/run_ppt_job.py /tmp/example-job.json
```

这个流程会按阶段输出：

- `master_style.json`
- `outline.json`
- `slide_prompts.json`
- `images/*.png`
- `deck.pptx`

如果你想直接走完，可先把 `outline_approved` 和 `prompts_approved` 设为 `true`，或者加上：

```bash
python scripts/run_ppt_job.py /tmp/example-job.json --auto-approve-outline --auto-approve-prompts
```

## 人工修改后回写

如果你已经人工编辑过 `outline.json` 或 `slide_prompts.json`：

```bash
python scripts/sync_job_artifacts.py /tmp/example-job.json --approve-outline --approve-prompts
```

## 单页重生成

```bash
python scripts/regenerate_single_slide.py /tmp/example-job.json --page-no 2 --instruction "改成更明显的双栏对照"
```

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

## 推荐模板

当前内置了 `慧新` 模板预设，适合：

- 白底咨询风
- 绿色主色 + Teal 辅色
- 信息密度高但结构清晰
- 咨询汇报、经营分析、阶段性进展页
