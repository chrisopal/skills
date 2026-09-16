# 图像生成与交付

这是图像工具调用、输入顺序、提示词与交付行为的唯一真源。生成前检查见 [preflight-gates.md](preflight-gates.md)；成图后只做一次读图诊断，不自动评分、proof 或重试。

## 运行目录与依赖

```text
output/yingzao/<run-id>/
  inputs/                 # 校正副本，不改原文件
  analysis/               # preflight、brief、字形/垫图、prompt、generation-call、readback
  drafts/                 # 仅用户要求探索时使用
  final/                  # 海报和可选对照
  recipe-history.json
```

先运行 `python3 scripts/check_dependencies.py`。所有依赖型脚本通过 `_runtime.py` 在调用者目录及父目录寻找兼容 `.venv`；也可由 `CAP_PYTHON` 指定隔离解释器。自动发现失败时停止并报告，不能全局安装或把缺包当成通过。只有用户授权后，才在调用者工作目录的隔离环境执行 `python -m pip install -r <skill>/requirements.txt`。

脚本不得把缓存、目录 HTML、测试图或运行产物写回 Skill 包。

## 动作与固定输入顺序

单图与同址多图融合默认用 edit：

```text
Image 1 — EDIT TARGET：真实几何与身份的唯一来源
Image 2 — PRIMARY VISUAL REFERENCE：整体迁移构图机制、主体处理、材质层级和图文张力；不复制其建筑、文字或符号
Image 3 — TYPESET GUIDE：只使用已确认文案、真实字面、共同轴、阅读顺序和实际主体轮廓遮挡；不含目标照片像素或最终风格
Image 4+ — 可选同址主体来源：只使用逐张点名的对象
```

主导参考必须是真实图像输入，优先用 `recipe <id> --json` 返回的 `quality=plate` 资产；无 plate 才用 thumbnail。最终由交接脚本复制成运行目录内的 `inputs/02-primary-reference.*`，避免安装位置变化或绝对路径失效。多图逐张说明可用内容、身份锚点和禁止迁移内容。

参考的最强机制不能在提示词中被全部禁止。`Reference transfer` 应点名 2–4 个能从 Image 2 直接看见的机制，覆盖主体处理、主动背景和图文关系；`Do not add` 只隔离其建筑身份、文字、品牌与符号。若删去这些内容后只剩“高级、克制、偏置、编辑感”等形容词，换一张参考。

文字路径：

- `typeset-guide-integrated`：默认正式路径；垫图与原图、参考同次送入 edit。
- `model-native-minimal-text`：门控不可用、文案极少或用户只要快速探索时使用。
- `geometry-only`：只约束主体范围、轴线与遮挡方向；仍保留 Image 2。
- `layered-final-type`：仅用户在生成前明确要求逐字绝对准确并接受程序字层时使用，不能因模型写字失败自动切换。

## GPT-Image-2 参数

直接调用 Images API 时：`model=gpt-image-2`；真实照片走 `/v1/images/edits`；正式成图用 `quality=high`，只有用户明确要求快速探索才用 `low/medium`；省略 `input_fidelity`；省略 `background` 或使用不透明背景，不能请求 `transparent`。多图作为独立 `image[]`，第一张始终是 edit target，蒙版只作用于第一张。

| 比例 | 尺寸 |
| --- | --- |
| 3:4 | `1536x2048` |
| 4:3 | `2048x1536` |
| 16:9 | `2048x1152` |
| 9:16 | `1152x2048` |
| 1:1 | `1536x1536` |

边长不超过 3840px、两边为 16 的倍数、长短边不超过 3:1、总像素 655,360–8,294,400。工具不暴露尺寸时先声明方向与安全区，生成后用 `fit_canvas.py` 做确定性 crop 或 pad，不拉伸；身份锚点余量不足时用 pad。

## 模型要完成的工作

优先级：`真实身份 > 四域命题 > 主导参考的完整机制 > 垫图空间关系 > 原照片局部像素`。身份不变量只保护建筑是谁，不等于冻结原构图、原背景和原材质。

- **主体域**：语义抠取，并发生尺度/位置重组或屋面、木构、墙体、器物、食物等分区材质转译。
- **背景域**：建立服务构图的色场、色窗、明度切片、负形或重建空间，不能只保留原天空或拉普通渐变。
- **互动域**：让真实檐口、屋脊、柱列、器物或食物轮廓与标题/色形产生遮挡、共边、穿插或负形咬合。
- **构图修复**：先识别原图的稳定骨架，只修一个主问题；允许补齐可连续推断的背景、直柱、墙、水面或地面，不发明屋顶、层数、门窗、雕塑或镜像构件。

普通裁切、统一滤镜、矩形拼版、网页式卡片或纯文字叠加不构成图像模型增值。主导参考提供的是整体设计逻辑，不是给成品加一层“参考色”。

## 设计语义编译

Recipe 不是只用于选参考。将 `design_tokens.py recipe <id> --json` 的完整输出保存为 `analysis/recipe.json`，并建立 `analysis/design-plan.json`。全部 `resolved_tokens` 和启用的 `selected_optional_tokens` 必须恰好投递一次：只有 `preflight / rectification` Token 可以进入 `preprocess_tokens`；其他 Token 必须组合进四个模型动作域。不要逐条拼接 Token 自带的 `prompt`，而要把相容 Token 合并成少量针对当前照片的可执行动作。

```json
{
  "schema_version": 1,
  "recipe_id": "cap.recipe.semantic-split-relief",
  "selected_optional_tokens": [],
  "preprocess_tokens": ["cap.subject.preflight-rectification"],
  "bindings": [
    {
      "id": "S1",
      "domain": "subject",
      "token_ids": ["cap.subject.identity-protection", "cap.subject.full-building", "cap.policy.recipe-geometry-gate"],
      "target": "Image 1 中完整相连的真实建筑主体",
      "prompt_instruction": "语义抠取完整主体，保留屋脊、层级与不对称身份锚点；重新安排占幅并对屋面、木构、墙体分区转译材质",
      "visible_result": "主体脱离原背景且分区材料清楚，不是统一滤镜",
      "guide_markers": ["S1"]
    },
    {
      "id": "B1",
      "domain": "background",
      "token_ids": ["cap.background.flat-field", "cap.material.arch-regional-flat", "cap.color.material-derived", "cap.policy.no-visible-lines", "cap.policy.no-ui-cards", "cap.policy.no-orphan-decorations", "cap.policy.background-rebuild"],
      "target": "S1 外围的连续负空间",
      "prompt_instruction": "重建为服务轮廓与标题的主动色场，并让取色来自真实建筑材料",
      "visible_result": "背景形成清晰色形，不保留原天空或普通渐变",
      "guide_markers": ["B1", "S1"]
    },
    {
      "id": "T1",
      "domain": "typography",
      "token_ids": ["cap.primitive.grid-6", "cap.primitive.optical-alignment", "cap.content.verified-name", "cap.content.verified-fact", "cap.type.display-cn", "cap.type.metadata", "cap.type.semantic-split-lockup", "cap.policy.typeset-guide-gated"],
      "target": "主标题和资料字锁定组",
      "prompt_instruction": "按字形简报重绘展示标题，保持资料字常规且沿垫图真实字面共同轴组织",
      "visible_result": "展示字有独特骨架，大小字不是同一套普通宋体",
      "guide_markers": ["T1"]
    },
    {
      "id": "I1",
      "domain": "interaction",
      "token_ids": ["cap.layout.center-monument"],
      "target": "S1 中轴主体与 T1 左右拆词标题之间的交界",
      "prompt_instruction": "让中轴建筑轮廓以低对比浮雕连接左右两组标题，并在一处真实外轮廓形成共边或受控前后关系",
      "visible_result": "缩略图可见主体把左右拆词标题连接成一个构图，而非三个孤岛",
      "guide_markers": ["S1", "T1"]
    }
  ]
}
```

四个 `domain` 缺一不可，总计使用 4–6 个合并后的 binding；每项必须同时写清 `target / prompt_instruction / visible_result / guide_markers`。同一 Token 不得重复投递，也不能只停留在 creative brief。编译器会把这些绑定插入真正传给 ImageGen 的 `Mechanism bindings` 段，并在 `generation-call.json.token_delivery` 留下追踪记录。

## 前置排版与字形

```bash
python3 scripts/typeset_compose.py blank analysis/typeset-spec.json analysis/typeset-guide.png \
  --report analysis/typeset-report.json
```

报告必须通过字体 cmap、fallback、真实字面、碰撞、溢出、共享轴、primitive 禁穿区、遮挡契约与竖排顺序。垫图保持中性灰阶；不含最终配色、纹理、完整主体矩形或网页容器。

垫图上的动作区域必须带与设计计划一致的短标记：`guide_marker` 使用 `S1 / B1 / T1` 这类 ASCII ID，`guide_label` 使用 `REAL SUBJECT / ACTIVE BACKGROUND / DISPLAY TITLE` 这类简短 ASCII 说明。编译器会把标记画成小徽标并验证 prompt↔guide 双向一致；这些徽标只用于告诉模型“哪个动作作用在哪里”，成图必须消失。

展示层必须在 spec 中声明 `glyph_design_mode`。`literal` 使用 `guide_render: text`；`reinterpret` 必须已有 `analysis/glyph-brief.md` 并使用 `guide_render: scaffold`。后者在 Image 3 只画字符槽和小型字面标签，锁定范围、共同轴与阅读顺序，但不再用大号普通宋体或黑体轮廓锚定模型。地点、年代、拼音和资料字保持 `literal`，并可使用不同常规字族建立层级。

## 最小提示词

只写本方案使用的内容：

```text
Primary transformation: <一句话写出成图中必须一眼看见的主体、背景、文字共同结果>
Image roles: <逐张角色与禁止迁移内容>
Composition diagnosis: <preserve 的理由，或一个主问题>
Composition repair: <一个主动作 + 可安全延续区域 + 可见结果 + 文字进入方式>
Subject treatment: <语义抠取范围 + 尺度/位置变化 + 分区材料或重光；不能只写“保留照片”>
Background treatment: <主动色场/色窗/明度切片/重建空间及其与主体的关系；不能只写渐变>
Interaction: <哪条真实轮廓与哪组文字/色形如何遮挡、共边、穿插或负形咬合>
Reference transfer: <从 Image 2 迁移的 2–4 个可见机制，以及占幅、负空间和互动边界的对应>
Identity invariants: <3–5 个决定身份的几何、题字或构件>
Typography layout: <Image 3 的标题组、共同轴、换行、阅读顺序与遮挡；scaffold 与 primitive 必须从成图消失>
Display glyph design: <仅 reinterpret 时写准确标题、形制、至少五项可见特征、逐字补偿与建筑对应；明确不复制普通字体轮廓>
Text (verbatim): <必要短文案>
Do not add: <不超过 5 个灾难性错误>
```

`literal` 方案删除整行 `Display glyph design`；`reinterpret` 方案必须保留。不要手写 `Mechanism bindings`，也不要把 Token ID、门控条目或历史问题清单塞进上述提示词；该段由设计计划确定性编译。原构图成立时写 `preserve`，保护偏心、框景、对角动势或横向跨越；不为模板强行居中、对称或补全。

## 固定交接：先编译，再调用

禁止凭记忆从简报直接调用图像模型。先把提示词保存为 `analysis/generation-prompt.txt`，再执行：

```bash
python3 scripts/prepare_generation.py \
  --run-dir output/yingzao/<run-id> \
  --source <校正原图> \
  --reference <主导参考 plate> \
  --guide <typeset-guide.png> \
  --typeset-spec <typeset-spec.json> \
  --typeset-report <typeset-report.json> \
  --recipe-json <recipe.json> \
  --design-plan <design-plan.json> \
  --glyph-brief <glyph-brief.md> \
  --prompt <generation-prompt.txt> \
  --output-image <final/poster.png>
```

`literal` 标题可省略 `--glyph-brief`。多图融合时在命令中追加一个或多个 `--support <同址来源图>`，并在 `Image roles` 中逐张点名 Image 4+。脚本会验证所有图不同、垫图尺寸与报告一致、报告已通过、提示词包含输入角色和主体/背景/互动段；还会展开 Recipe，检查所有启用 Token 的唯一投递、四域动作、prompt↔guide 标记双向一致。`reinterpret` 另验证 scaffold、准确标题、字形简报和逐字覆盖。它把绑定动作编进最终提示词，把输入复制到稳定路径并写出 `analysis/generation-call.json`。

只有终端返回 `READY` 才调用图像模型。调用时直接读取清单，严格映射：

```text
imagegen(manifest["tool_arguments"])
```

`tool_arguments` 已包含逐字 prompt 与有序 `referenced_image_paths`。不得重新概括 prompt、重排路径、改用最近会话图片，或只传原图；清单前三项永远是 edit target、主导参考、排版垫图，同址支持图从 Image 4 起依次追加。

## 交付与反馈

按预先确认数量生成并保存到 `final/`。保存后必须用读图工具打开实际成图，只检查五件事：

1. 主体是否仍可识别，是否真的发生抠取、尺度/位置或分区材质处理；
2. 背景是否主动参与，而不是原图天空、空白或普通渐变；
3. 标题是否仍是普通字体轮廓，准确文案、共同轴和小字角色是否成立；
4. 主体与文字/色形是否发生约定的遮挡、共边、穿插或负形；
5. Image 2 的完整机制是否可见，而不只是颜色相似。

把最明显的 0–3 个观察写入 `analysis/readback.md`，同时记录成图路径与对应 `call_signature`。这是读图诊断，不打分、不生成 proof、不自动重试，也不把结论回灌提示词。若有结构性失败，交付时直接说明并询问用户是否要改；若无明显问题写“未见明显结构性失败”。用户要求原图对照时再运行 `make_comparison.py`。

收到反馈后才修订：

- 局部字形、错字、边缘、小范围材质：以当前成图为 edit target，只改反馈范围，锁定其他像素。
- 主体处理、背景色场、主布局、参考方向或图文关系：回到校正原图，重做四域命题、参考选择与垫图；不在失败拓扑上继续补丁。
- 只针对展示字时复用并更新 `glyph-brief.md`，仍由模型重绘，不自动后贴字。

修改后交回用户；下一轮是否继续由用户决定，没有隐藏重试。

首次交付一张新海报后，再问一次是否扩展为九宫格视频分镜与视频提示词。只有用户同意才读取 [video-storyboard.md](video-storyboard.md)，且不自动生成视频。
