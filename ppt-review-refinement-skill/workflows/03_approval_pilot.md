# 03｜授权与样板

## 变更授权

`change_manifest.json` 是执行边界，不是建议清单。任何未写明的高风险动作默认为禁止。

### 至少确认

- 正文是否可改；标题是否可优化。
- 页面顺序是否可改；是否允许拆分/合并/删除。
- 是否统一主题、颜色、字体、字号、布局和组件。
- 是否允许重画图表、流程和架构图。
- 配图是否允许裁切、调色、替换或生成。
- 是否必须保留动画、链接、备注、母版和编辑性。
- 受保护数字、名称、术语和页面。

### 冲突处理

- `body_text=preserve` 与 `allow_rewrite_body=true` 冲突时，以更严格规则为准并报告。
- `image.replace=forbidden` 时，即使视觉评审建议替换，也只能列为未执行建议。
- `slide_order=preserve` 时可以调整页内结构，但不能移动页面。

## 样板页选择

优先选择问题典型、代表性强、可迁移设计语言的页面：

- 一页封面或章节。
- 一页高频普通版式。
- 一页复杂结构页。

不要只选择最容易美化的页面。

## 样板输出

每个样板必须包含：

- 原页图。
- 优化页图。
- 具体修改清单。
- 对设计 Token 的映射。
- 内容是否发生变化。
- 可迁移到哪些页面。
- 尚未解决的风险。

## 确认记录

使用 `templates/pilot_review.template.md` 记录人工判断，并将确认结果结构化为 `pilot_confirmation.json`。没有 `status=approved` 且覆盖所有计划样板页的确认记录，状态不能进入 `PILOTED`，L2/L3 执行器也会拒绝运行。

L2/L3 执行：

```bash
python scripts/execute_refinement_plan.py \
  --input input.pptx \
  --output work/candidate.pptx \
  --plan work/refinement_plan.json \
  --tokens work/style_tokens.json \
  --manifest work/change_manifest.json \
  --pilot-confirmation work/pilot_confirmation.json \
  --log work/change_log.json \
  --before-after-dir work/before_after
```

不支持的动作会明确失败并保留源文件，不会静默降级为“看起来完成”。
