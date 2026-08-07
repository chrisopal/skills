# 06｜校验与交付

## 三层校验

### 1. 内容保护

- 页数和顺序是否符合授权。
- 正文是否被误改。
- 数字、金额、日期、百分比、单位、型号是否变化。
- 客户名、公司名、产品名和受保护术语是否丢失。
- 图表数据和来源是否保持。

### 2. 视觉质量

- 标题位置、字体和颜色是否统一。
- 是否仍有文本溢出、元素重叠、越界和图片变形。
- 页面是否有明确视觉重点和阅读路径。
- 图表、表格、流程、架构和配图是否属于同一视觉系统。
- 是否存在过度装饰、过小字体和无效留白。

### 3. 技术质量

- 文件能否正常打开并再次保存。
- 页面对象是否可编辑。
- 动画、链接、备注和图表是否按授权保留。
- 字体替代风险是否已记录。
- 文件体积是否异常增长。

## 渲染门禁

最终候选文件必须生成逐页 PNG，并检查全部页面。缩略图总览用于发现一致性问题，单页 100% 图用于发现溢出、错位和低清问题。

## 最终人工视觉确认

自动验证不能替代最终人工视觉判断。人工查看全部渲染页后，填写 `templates/visual_signoff.template.json`，并运行：

```bash
python scripts/confirm_visual_review.py \
  --signoff work/visual_signoff.json \
  --source input.pptx \
  --candidate work/candidate.pptx
```

最终验证必须把该文件传给 `validate_pptx.py --visual-signoff`。未提供或未批准的签字会产生 `VAL-VISUAL-SIGNOFF=fail`；`--allow-unconfirmed-visual` 只允许结构测试使用，不能作为交付证据。

## 交付包

```text
deliver/
  optimized.pptx
  review_report.md
  review_report.json
  change_manifest.json
  style_tokens.json
  validation_report.md
  validation_report.json
  change_log.json
  before_after/
```

## 验收条件

- P0 = 0。
- 未接受的 P1 = 0。
- 内容保护检查全部通过，或有用户明确签字接受的差异。
- 视觉渲染检查完成。
- 所有无法自动验证的对象已列入人工复核清单。

### 人工复核风险登记

以下风险如果出现在候选文件中，必须在 `accepted_risks` 中登记对应 ID 后才能进入 `pass_with_accepted_risks`：

- `VAL-MANUAL-DIAGRAM`：SmartArt/Diagram。
- `VAL-MANUAL-EMBEDDED`：嵌入对象。
- `VAL-MANUAL-ANIMATION`：动画或时间线。
- `VAL-MANUAL-LINKS`：外部关系或超链接。
- `VAL-IMAGES`：允许替换或需要人工核对的图片。
- `VAL-RENDER-SKIPPED`：明确授权跳过渲染。

只列在 `manual_review_required` 中不等于上述技术风险已接受；未登记的人工复核风险会使验证失败。
