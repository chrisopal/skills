# 从已选设计图到可编辑对象

先读安装好的 image-to-editable-ppt/SKILL.md。对象划分、素材分离和 run 状态由该依赖管理；这里补充原稿、主题与页映射。

## 1. 固定并复核输入

```bash
python "$VISUAL/scripts/visual_bridge.py" --consulting-root "$CONSULTING" handoff \
  --project "$PROJECT" --output "$PROJECT/handoff-v001" --range 1,3
python "$VISUAL/scripts/visual_bridge.py" --consulting-root "$CONSULTING" verify-handoff \
  --project "$PROJECT" --output "$PROJECT/handoff-v001"
```

不传 range 才是全稿。handoff 还生成 `conversion-input.pptx`，严格一页一张已选原图，并携带对应原始 speaker_notes；这是带备注的转换输入，不是最终成品。它的页序与 handoff.pages 一致。prepare 的 run 路径读取命令结果。

```bash
editppt prepare "$PROJECT/handoff-v001/conversion-input.pptx" \
  --image-backend builtin-imagegen --max-concurrent-pages 2
```

没有备注且更适合直接图片输入时，也可按 handoff.json 的 pages 顺序显式传 images 路径给 prepare；不使用目录 glob，扩展名以实际记录为准。

其他宿主用 host-tool 参数替换 backend，并传实际契约。并发取“宿主空闲槽位、用户上限、页数”的最小值；示例的2不是固定能力假设。

## 2. 传递页任务

按依赖 `run next`、prompt builder、真实 spawn/dispatch 流程执行。每个页 Agent 的任务额外给出：

```text
可读附件：本页 content/page_NNN.json、style-profile.json、handoff.json。
只拥有转换 run 的 pages/page_NNN/；不修改原稿、主题或其他页。
映射以 handoff 的 page_id→slide_id→order 为准，不按图片上页码猜。
图像控制视觉位置/材质；原始内容控制文本、数字、单位、关系和备注。
将原稿里的可见内容重建为 native 文本/结构，纠正 OCR 或生成图错字。
若原稿和图像冲突涉及实质内容/布局，报告差异并先修设计图；不能自行改原稿。
按依赖 page-decision-tree 分离复杂素材，不截整块卡片/表格绕过编辑性。
完成原有页级 QA，并记录原稿核对、视觉比对和位图保留范围。
```

任务说明是父 Agent 派发的消息，不直接改 page_request.json 或状态文件。
有备注时使用上述 conversion-input.pptx；prepare 会按原有路径提取备注，finalize 保留 notes_manifest 的备注。不要手写或修改 notes_manifest 来绕过状态契约。

## 3. 对象层级与数据

- 正文、标题、标签：原生文本框；布局框、线、简单箭头、表格：原生结构。
- 照片、复杂插画、纹理、品牌图形：保留为独立图片素材，可移动/替换，不能称为内部可编辑矢量。
- 图表：有原始数据就按数据重建，核对单位、类别与系列。当前 editppt manifest 主要支持文字、形状、图片，不把形状重建误称为 PowerPoint 原生数据图表；数据随原稿保存。若任务明确要求“编辑数据”图表功能，需要使用经验证且能经 record/finalize 保留的图表扩展，未具备时明确差距，不直接改最终 PPTX 绕过 manifest。
- 不允许整页 source 图片垫底再放重复文字。所有重建必须能由本页 manifest 独立恢复。

## 4. 完成与回读

按依赖 record/finalize，随后执行：

```bash
python "$VISUAL/scripts/visual_bridge.py" --consulting-root "$CONSULTING" audit-pptx \
  --project "$PROJECT" --output "$PROJECT/handoff-v001" --pptx /实际输出/final.pptx
```

这是补充机器检查，不写 editppt 状态，也不等于视觉验收。finalize 后按质量参考完成最终渲染比较；如果有缺陷，回到页 manifest 修复，经原有 reset/record/finalize 重建。不要只修 page.pptx，因为最终文件从 manifest 重建。
