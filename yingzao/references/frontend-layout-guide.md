# 稀疏排版垫图与程序门控

垫图是调用图像模型前的空间证据，不是风格稿、网页截图或半成品海报。默认用 `scripts/typeset_compose.py` 在中性灰阶画布上渲染必要真实文字；最终配色、材质、背景、主体造型与字形表面由主导参考和图像模型完成。

高风格化任务中：Image 1 提供真实身份，Image 2 提供整体视觉机制，Image 3 才提供排版关系。缺少 Image 2 时，不要让完整垫图成为最强风格锚点；改用更稀疏的 `geometry-only` 或摄影本位轻编辑。

## 模式

### `typeset-guide`（默认）

只含一个展示标题组、一个地点/对象组和必要资料。不得嵌入目标照片像素，不含最终色场、纸纹、渐变、阴影、卡片、完整主体矩形或完成态装饰。若创意简报声明主体遮字，必须另含从 Image 1 真实轮廓描出的低对比 `subject-footprint`，让遮挡在垫图中实际发生。`literal` 展示字使用真实字体；`reinterpret` 用字符槽与小型字面标签锁定空间，不显示大号普通字体轮廓；资料字使用常规真实字体。

### `geometry-only`（门控失败时回退）

只用中性轴线、低对比真实轮廓或主体范围表达构图，不含真实文字、伪字、文字框、空卡片或可见网格。它不证明文字对齐。

### `layered-final-type`（仅用户预先明确选择）

图像模型先生成不含关键文字的艺术底版，再用真实字体和可选主体蒙版合成。它不是成图失败后的补丁；默认整体 edit 不使用。

## 确定性编译器

```bash
python3 scripts/typeset_compose.py blank analysis/typeset-spec.json analysis/typeset-guide.png \
  --report analysis/typeset-report.json
```

最小规格：

```json
{
  "mode": "typeset-guide",
  "canvas": [1536, 1024],
  "background": "#EEEEEC",
  "primitives": [],
  "layers": [
    {
      "id": "title",
      "role": "display",
      "glyph_design_mode": "reinterpret",
      "guide_render": "scaffold",
      "guide_marker": "T1",
      "guide_label": "DISPLAY TITLE",
      "text": "飞檐",
      "font": "/absolute/path/to/authorized-font.ttf",
      "font_index": 0,
      "size_px": 236,
      "x": 928,
      "y": 682,
      "fill": "#777777",
      "orientation": "horizontal",
      "layer": "front"
    },
    {
      "id": "place",
      "role": "metadata",
      "text": "善化寺",
      "font": "/absolute/path/to/authorized-sans.ttf",
      "size_px": 42,
      "x": 936,
      "y": 934,
      "fill": "#242424",
      "orientation": "vertical",
      "vertical_order": "top-to-bottom",
      "layer": "front"
    }
  ],
  "alignment_groups": [
    {
      "id": "title-place-left",
      "axis": "left",
      "basis": "ink",
      "members": ["title", "place"]
    }
  ]
}
```

坐标在 `0..1` 时按画布比例解释，其余为像素。对齐轴支持 `left / right / top / bottom / center_x / center_y / baseline`；`basis` 为 `ink` 或 `layout`。

## 编译器保证

- **字体覆盖**：使用 fontTools 读取所选 font index 的 cmap，逐字验证该层实际文案；缺字直接失败，不把 Pillow 画出的 `.notdef` 豆腐块当成有效字形。
- **角色显式**：展示层只认 `role: display / display-title / title / structural-title`，不从 layer id 猜测；`subtitle-pinyin` 等 metadata 不会误用展示字 padding。
- **语义标记**：需要模型执行动作的文字层与 primitive 使用 `guide_marker + guide_label`；标记 ID 为短 ASCII，标签为可移植 ASCII。报告保留同一映射，供 `prepare_generation.py` 与 `design-plan.json` 双向核验。
- **字形路径显式**：展示层必须声明 `glyph_design_mode: literal / reinterpret`。前者用 `guide_render: text`；后者必须用 `guide_render: scaffold`，避免普通字体像素成为比字形简报更强的锚点。
- **真实字面**：每层同时记录 `layout_bbox` 与 `ink_bbox`，碰撞和光学对齐使用真实墨迹边界。
- **对齐组**：默认容差为画布宽度的 `0.25%`。含展示标题的组默认 `basis: ink`；确需 `layout` 时必须填写 `layout_reason`。
- **竖排顺序**：当前编译器只支持 `vertical_order: top-to-bottom`；竖排未声明或横排误填都会失败。竖排不得加入 baseline 组。
- **基线语义**：多行文字的 baseline 只指首行；比较其他行时拆成独立层或使用上下边界。
- **禁穿区**：资料字至少扩张 `0.5em`，展示字至少扩张 `0.25` 个字高。`rect / ellipse / polygon / line` 均参与相交检查。
- **主体遮字证据**：`text-behind-subject` 只接受 `layer: subject_front` 且 `role: subject-footprint` 的 primitive，对应文字必须为 `layer: behind_subject`。普通线条或背景图形不能冒充主体轮廓。
- **越界与碰撞**：可见墨迹不得裁切或溢出；未声明的文字碰撞失败。

报告必须 `passed=true` 才能把垫图交给图像模型。任一前置门失败，修正 JSON 或降级为 `geometry-only`；不得手动拖动后跳过报告。

## Primitive 与遮挡契约

`primitives` 默认为空。只有关键遮挡不能用文字说明时，才使用从 Image 1 描出的低对比主体轮廓；不得用 primitive 搭建成品背景或网页栏位。主体轮廓不是随手画的屋顶线，而是能表达计划主体占幅、偏置和主要外轮廓的闭合 polygon。

允许 primitive 进入文字禁穿区时，必须按 primitive—文字对登记：

```json
{
  "primitives": [
    {
      "id": "subject-footprint",
      "type": "polygon",
      "role": "subject-footprint",
      "layer": "subject_front",
      "guide_marker": "S1",
      "guide_label": "REAL SUBJECT",
      "points": [[0.18, 0.42], [0.84, 0.42], [0.91, 0.78], [0.12, 0.78]],
      "fill": "#666666",
      "opacity": 64
    }
  ],
  "layers": [{"id": "title", "role": "display", "layer": "behind_subject"}],
  "overlap_contracts": [
    {
      "id": "eave-cuts-title",
      "primitive": "subject-footprint",
      "text": "title",
      "reason": "真实屋檐在标题前形成一次受控遮挡",
      "z_order": "text-behind-subject"
    }
  ]
}
```

未知对象、空原因、重复契约、非主体 primitive 冒充 `text-behind-subject` 或未登记相交均失败。若只是规则线与文字的设计重叠，使用其他明确 z_order，不能伪装为主体互动。文字—文字有意重叠用层级的 `allow_overlap`，但必须在创意简报写明共同轴、z 顺序和视觉任务；它不会放行 primitive—文字相交。

主动背景区、色窗或材质区同样用低对比 primitive 标出并赋予 `B1 / M1` 等标记；它只说明作用范围，不画最终颜色、纹理或完成态装饰。一个标记可出现在多个元素上，但 `guide_label` 必须完全一致；所有垫图标记都必须被设计计划至少一个 binding 引用，设计计划引用的标记也必须真实出现在 spec 与 report 中。

## 网格与标题组

- 所有宣称共享左边、右边、中轴、顶边、底边或基线的关系都必须有 `alignment_group`；肉眼近似不算。
- 建筑名拆成地点词、对象名和拼音时，先建立一个父级锁定组；不能把三段分别自由定位。
- 三轨竖题通常为：左侧真实拼音微字、中间重字重对象名、右侧较小地点词。三轨至少共享两条可解释边界，且对象名在缩略尺度承担第一层级。
- 全幅等宽标题的各字必须同高、同宽、同字重、同基线；主体可以遮字，文字不能为避让主体而缩小或错位。
- 规则线/分割线只有服务信息分组或共同轴时才出现，并必须避开所有文字禁穿区。
- 避免卡片、胶囊、按钮、投影容器和等权信息块。秩序来自字级、字重、留白、共同轴和受控遮挡。

## 交给图像模型

垫图只控制必要文案、角色、字号比例、边界、换行、共同轴和阅读顺序。提示模型：

- Image 2 的整体视觉机制高于垫图；Image 3 的中性颜色和 primitive 不是最终设计。
- 用 Image 1 的真实主体替换任何中性占位。
- `subject-footprint` 只锁计划占幅、偏置和遮挡边界；模型必须用 Image 1 的真实建筑替换它并完成抠取、区域材质和共同重光，不能把灰色 polygon 当成成品色块。
- 文字、主体、背景和材质在同一次 edit 中形成统一物质语言，不在成图上覆盖干净数字字体。
- `reinterpret` 保留垫图字符槽、共同轴与小型字面标签，但必须按生成前 `glyph-brief.md` 重新设计最终轮廓；scaffold 框线和标签不能出现在成图中。资料字保持 conventional and literal。

具体输入顺序和提示词结构以 [image-generation-workflow.md](image-generation-workflow.md) 为唯一真源。
