---
name: enterprise-diagrams
description: 用可编辑 JSON 规格和纯矢量 SVG 生成企业架构、流程、泳道、时序与数据链路图；适合需要稳定版式、语义色彩、可审计路由和可二次编辑交付的图示任务。
metadata:
  version: "1.0.0"
  language: zh-CN
---

# Enterprise diagrams

把工程图先写成可审阅的 JSON，再用 `scripts/diagram_svg.py` 渲染为不依赖外部资源的 SVG。源文件应保留在交付物旁，方便用户后续调整标题、节点、边、分组和主题。渲染器会拒绝缺失节点、重复 ID、row/col/span 重叠、悬空边、未知枚举、超限数量和无法安全布线的规格。

先从正文或已确认方案取得节点与关系，选择 layered（分层）、flow（流程）、pipeline（工艺链）、swimlane（责任泳道）、network（网络分区）、parallel（并行汇聚）、sequence（消息时序）或 matrix（对应矩阵）。颜色可选 reference（默认参考多色）、blue、teal、green、slate、monochrome；用户选择优先。将主题保存到 JSON 的 `theme`，版式保存到 `layout`。投标套件通过 `visuals.diagram_engine=blueprint` 与 `visuals.diagram_theme` 调用本能力，Draw.io 仍是独立可选引擎。

运行后读回实际 SVG，检查分支标签归属、泳道责任、箭头方向与原方案一致，再核对中文、长标题和 A4 可读性。警告要求拆图时生成总览与局部图，不直接缩小字号。复杂嵌套 alt/loop 时序可采用已有 PlantUML 或 Draw.io；系统界面示意继续调用宿主生图 Skill。用户提出修改时保存新版本 JSON 和成图，保留旧版以供回查。

入口函数是 `render_svg(spec, theme=None)`，返回 SVG、画布尺寸、主题、布局、节点几何、正交边路径、分组几何和 warnings。命令行调用方式为：

```bash
python scripts/diagram_svg.py --source example.diagram.json --out example.svg [--theme teal]
```

CLI stdout 只输出不含 SVG 正文的精简 JSON 元数据；`--out` 必须是新的 `.svg` 路径，工具会创建父目录但拒绝覆盖已有文件。SVG 文件本身是 UTF-8 文本，可以直接在浏览器、Illustrator、Inkscape 或 PowerPoint 流程中继续处理。不要把 SVG 重新截图成位图来替代源文件。

完整字段、限制、验收要点和对话式修改约定见 [references/spec.md](references/spec.md)。六种主题参数在 [assets/diagram-themes.json](assets/diagram-themes.json)，可运行样例在 [assets/examples](assets/examples)。
