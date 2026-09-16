---
name: yingzao
description: Transform real Chinese architecture and place-based cultural photos into art-directed editorial posters, integrated multi-photo scenes, and optional source comparisons. Use for historic buildings, vernacular streets, culturally rooted shops, interiors, food, travel covers, and place montages; do not use for generic advertising, routine retouching, or invented places.
---

# Yingzao · 营造

把真实建筑与在地文化照片转译为有主体处理、主动背景、字形设计和空间互动的编辑海报。先从照片提出创意命题，再让一张兼容的主导参考强化它；Token 负责检索与机制追踪，不能替代设计判断。

## 核心合同

- 高风格化任务固定使用：Image 1 校正原图、Image 2 一张主导参考实图、Image 3 稀疏中性排版垫图。生成前必须由 `scripts/prepare_generation.py` 编译成一次调用清单，不得互相替代、改序或在调用时重新概括提示词。
- 所选 Recipe 必须保存为 `analysis/recipe.json`，再把全部启用 Token 编入 `analysis/design-plan.json`：除确定性校正项外，每个 Token 都要归入主体、背景、字体或互动动作，并指向 Image 3 中同名的区域标记。编译器把这些动作写入最终模型提示词；只在简报里出现、不进入提示词和垫图的 Token 视为未投递。
- 创意命题必须先于参考检索，并同时说明：`主体如何处理 / 背景如何主动参与 / 文字如何与真实轮廓互动 / 哪个非默认排版动作打破双居中`。
- `reinterpret` 展示字在首次生成前完成 `glyph-brief.md` 和逐字光学补偿，并在垫图使用 `guide_render: scaffold`，避免普通字体轮廓压过字形说明；不能只写宋体、黑体、衬线或“高级复古”。资料小字可使用另一常规字族。
- 图像模型必须完成语义抠取、构图修复、共同重光、背景重建、区域材质、图文遮挡等代码不能替代的动作。普通裁图、滤镜、渐变和打字能复现的方案无效。
- 单图的主体域、背景域、互动域都要在缩略尺度可见。主体居中、标题居中且互不接触的“两座孤岛”默认无效。
- 提示词只表达一个艺术方向，不拼接 Token 约束、失败案例或长验收清单。
- 只生成用户要求的数量。成图后必须读回一次并简要指出明显问题，但不自动评分、制作 proof 或重生成；用户反馈后才定向修改。

## 输入确认

从用户消息提取：地点/对象与必要文案、海报数量、是否要原图对照拼图。已明确的不再问；用户说“你决定”时默认 1 张、只用已确认或可核实短词、不生成对照拼图。名称不确定时可识别或检索，不能凭外观编造。

## 工作流

### 0. 建立安全输入

1. 运行 `python3 scripts/check_dependencies.py`。入口会自动寻找调用者目录中的兼容 `.venv`；失败时停止并说明，不全局安装，也不静默降级。
2. 产物写入调用者工作目录的 `output/yingzao/<run-id>/`，不得写入 Skill 包。
3. 每张来源运行 `scripts/photo_preflight.py`，判定 `hero / support / reject`，记录照片轴和构图问题。需要时先用 `scripts/rectify.py` 做确定性校正。
4. 事实按 `VERIFIED / OBSERVED / USER-CONFIRMED / UNCONFIRMED` 分级；只有前三类进入海报。细则见 [photo-preflight.md](references/photo-preflight.md) 与 [research-and-annotation.md](references/research-and-annotation.md)。

### 1. 冻结创意命题并选择参考

先写四域命题，再从 preflight 的受控标签检索：

```bash
python3 scripts/design_tokens.py suggest \
  --tag <标签> --count <数量+1> --maximize-distance \
  --history output/yingzao/<run-id>/recipe-history.json \
  --record-history
python3 scripts/design_tokens.py recipe <id> --json \
  > output/yingzao/<run-id>/analysis/recipe.json
```

零命中返回状态 2，此时换受控词重查。用 `recipe <id> --json` 取得真实 `reference_assets`，并将完整输出保存为 `analysis/recipe.json`；高风格化任务恰好选择一张主导参考。它必须与目标的主体占幅、负空间拓扑和互动边界兼容，并实际示范主体处理、主动背景和图文关系。选择方法见 [mixing-logic.md](references/mixing-logic.md)。

把会改变生成决策的内容写入 [creative-brief.md](references/creative-brief.md)，再通过 [preflight-gates.md](references/preflight-gates.md) 的八个生成前门控。

### 2. 设计字形与空间关系

按 [frontend-layout-guide.md](references/frontend-layout-guide.md) 用 `scripts/typeset_compose.py` 生成中性稀疏垫图。先写 `design-plan.json`，把四域动作分别标为 `S1 / B1 / T1 / I1` 等；对应标题层、主体轮廓和背景区域必须使用 `guide_marker + guide_label` 标在垫图上。展示层必须显式声明 `glyph_design_mode`；`reinterpret` 只画字符槽与小型字面标签，不把普通字体的大轮廓喂成最终形制。垫图只锁必要文字、层级、共同轴、阅读顺序、动作区域和主要遮挡，不锁最终颜色、材质或网页式容器。

展示标题为 `reinterpret` 时，按 [display-glyph-morphology.md](references/display-glyph-morphology.md) 保存 `analysis/glyph-brief.md`：选择一个字形谱系，记录至少五项可见特征，并逐字说明光学问题、轮廓动作和不可改变的标准部件。若声明主体压字，垫图必须用 Image 1 的真实轮廓建立 `subject-footprint` 和遮挡契约。

### 3. 整体生成

单图和同址多图融合默认使用 edit。先按 [image-generation-workflow.md](references/image-generation-workflow.md) 写提示词并运行 `scripts/prepare_generation.py`；只有脚本返回 `READY` 才能调用图像模型。调用时原样使用清单中的 `tool_arguments`，不得省略主导参考、垫图或主体/背景/互动段。

多图“合一”时逐图提取主体，重组进共享透视、光向、接触阴影、边缘语言和材质的同一环境；只有用户明确要求组照或对照时才保留照片矩形。

### 4. 交付与按需扩展

- 生成后先用读图工具打开成图，按 [image-generation-workflow.md](references/image-generation-workflow.md) 做一次五项快速读回，把最明显的 0–3 个问题写入 `analysis/readback.md`；不因此自动重生成。
- 用户不要拼图：交付海报。用户要对照：运行 `scripts/make_comparison.py ORIGINAL POSTER OUTPUT`。
- 邀请用户指出字体、主体处理、构图、材质、文案或融合关系中的具体修改。收到反馈后，局部问题以当前成图为 edit target；主体、背景、主布局、参考方向或图文关系等结构问题回到校正原图，重做命题、参考和垫图。
- 海报交付后问一次：“要不要继续把这张海报扩展成一张 3×3 视频分镜图，并附一段可直接交给视频模型的提示词？”用户同意后才读取 [video-storyboard.md](references/video-storyboard.md)；不要自动生成视频。

## 按需参考

| 情况 | 文件 |
| --- | --- |
| 需要具体字体、构图、材质或文化转译方法 | [art-direction.md](references/art-direction.md) |
| 制作排版垫图 | [frontend-layout-guide.md](references/frontend-layout-guide.md) |
| 设计展示字形 | [display-glyph-morphology.md](references/display-glyph-morphology.md) |
| 维护 Recipe / Token | [token-system.md](references/token-system.md) |
| 读取所选参考的编码 | [reference-encoding-matrix.md](references/reference-encoding-matrix.md)、[reference-encoding-expansion-2026.md](references/reference-encoding-expansion-2026.md)；只读命中的条目 |
