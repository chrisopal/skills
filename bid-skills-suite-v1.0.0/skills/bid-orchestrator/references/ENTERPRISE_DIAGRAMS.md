# Enterprise diagrams specification

## 输入

输入是一个 JSON object：`version` 必须是字符串 `"1.0"`；`title` 必填；`subtitle`、`footer`、`theme`、`width` 可选；`layout` 必须为 `layered`、`flow`、`pipeline`、`swimlane`、`network`、`parallel`、`sequence` 或 `matrix`。`theme` 可选值为 `reference`、`blue`、`teal`、`green`、`slate`、`monochrome`。

普通布局的节点使用 `{id,title,description?,row,col,span?,role?,shape?,badge?}`。`row`、`col`、`span` 是非负整数；同一 row 上的 `[col,col+span)` 区间不得重叠。`role` 为 `primary`、`process`、`data`、`success`、`decision`、`neutral` 或 `warning`；`shape` 为 `box`、`diamond` 或 `note`。边使用 `{from,to,label?,kind?,route?}`，其中 `kind` 为 `normal`、`feedback`、`dashed`，`route` 为 `auto`、`left`、`right`。边允许自环。分组使用 `{id,title,members,kind?,role?}`，`kind` 为 `band`、`zone` 或 `lane`。

`sequence` 将所有节点视为 row 0 的参与者标题，边数组顺序就是消息顺序；自环表示参与者的内部消息。消息间距按实际标签高度扩展，多行自调用标签不应压到下一条消息。其他布局依照 row/col 网格自动计算列宽、行高和换行，节点正文字体自然尺寸不低于 16px。

## 限制与拒绝条件

- 节点最多 64 个，边最多 120 条；空 nodes、重复 ID、悬空边、悬空分组成员会被拒绝。
- width 必须为有限数值且在 640–4000px；文本保留原字符并按显示宽度换行。
- 渲染前会拒绝未知枚举、布尔值冒充整数、重复 row/col/span 单元格和 sequence 中非 row 0 节点。
- 正交连接器只从节点边界离开，路径会避让所有节点的安全外扩区；无法找到安全路径时抛出错误并停止输出，不生成可能穿过节点正文的 SVG。
- `network` 与 `parallel` 中跨列边优先使用源节点右/左端口到目标节点左/右端口；同列边继续使用上下端口，其他布局默认按行方向使用上下端口。这样汇聚节点的输入与后续输出不会复用相反方向的同一竖直轨道。
- 边标签按实际线段的四分之一、二分之一和四分之三位置寻找侧旁空位：水平线优先上下放置，垂直线优先左右放置，并避让节点、分组标题和已占用标签。候选按到所属折线的距离排序；拥挤时 metadata 会返回无箭头 `leader_points`，SVG 绘制细引导线并再次检查节点与其他标签障碍。宽反馈标签在显式 `route=right` 时会为右侧安全轨道扩展画布；仍无安全位置时明确拒绝规格。
- SVG 中所有用户文本均转义；不使用外部图片、脚本、`foreignObject`、网络字体或数据 URI。
- CLI 的 `--out` 必须以 `.svg` 结尾且目标不存在；这样重跑不会覆盖已有证据或用户修改。

## 验收

审阅时同时保留 JSON 和 SVG。检查 stdout 元数据中的 `nodes[].x/y/width/height`、`edges[].points/path/safe`、`groups[]`，确认边的 `safe` 全为 true、节点无交叠、路径不穿过节点矩形，长中文/ASCII 标签在 SVG 中完整出现。默认画布宽度为 900px；A4 版心按 453.5×652pt（约 16×23cm）估算，metadata 的 `warnings` 会提示缩放后正文小于 8pt 或高度超过 23cm，应拆分总览与局部图。需交付 A4 时，把 SVG 放入后续排版流程，并在该流程中重新核对页边距、缩放和导出 PDF；本 Skill 只保证画布内的矢量几何。

中文必须同时检查 SVG、实际 PNG 和文档渲染页面；PDF 能提取中文不代表字形已显示。若文档工具的隔离字体配置找不到宿主已有字体，可为该次渲染指定项目内 `FONTCONFIG_FILE`，引用实际已安装字体目录并把缓存放在项目 QA 目录，再重新逐页检查。保持文档工具规定的编译器，不切换桌面编译器来掩盖失败；不修改宿主全局字体配置，不打包字体文件。字体映射和适用环境须记入交付检查记录。

## 对话式修改

先指出要改的 JSON 字段，再重新渲染和读取元数据。例如“把评审节点改成紫色菱形”对应 `role=decision, shape=diamond`；“把反馈箭头放到右侧”对应该 edge 的 `route=right`。不要只改 SVG 文本而丢失 JSON 来源。若修改会造成 row/col/span 重叠、边悬空或超出限制，应报告具体冲突并保留上一个可渲染规格。
