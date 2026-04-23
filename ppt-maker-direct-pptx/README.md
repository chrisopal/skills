# ppt-maker-direct-pptx

这是一个“确认式 + 直接绘制 PPTX”的 skill。

它保留了 `ppt-maker-with-image` 的前半段流程：

1. 需求确认
2. 模板推荐与确认
3. 大纲生成与确认
4. 每页结构化页面意图生成与确认

不同点在最后一步：

- 不再生成整页图片
- 而是根据 `master_style + slide_prompts + slide_specs`
- 直接绘制为 PowerPoint 原生对象
- 输出可编辑的 `.pptx`

## 典型用途

- 方案汇报
- 咨询型汇报
- 管理层汇报
- 需要更高可编辑性的 PPT 输出

## 主要脚本

- `scripts/run_ppt_job.py`
- `scripts/render_single_slide_ppt.py`
- `scripts/regenerate_single_slide.py`
- `scripts/review_job_status.py`
- `scripts/assemble_pptx.py`

## 核心产物

- `master_style.json`
- `outline.json`
- `slide_prompts.json`
- `slide_specs.json`
- `deck.pptx`

## 单页直出

```bash
python scripts/render_single_slide_ppt.py --prompt "这里写单页提示词" --template-id huixin
```

## 多页生成

```bash
python scripts/run_ppt_job.py path/to/job.json
```
