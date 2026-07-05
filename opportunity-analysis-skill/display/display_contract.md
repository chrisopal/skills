# Display Contract

Display层只接收结构化数据，不直接消费自然语言摘要。

默认实现是`src/opportunity_skill/renderer.py`。宿主Agent或产品工作台可以替换模板、CSS或Renderer，但必须保持输入为结构化数据，输出包含HTML和Markdown fallback。

## 模板

- `opportunity_card`: 商机摘要卡
- `opportunity_detail`: 商机详情页
- `customer_profile`: 客户画像卡
- `opportunity_kanban`: 商机看板
- `next_action_list`: 下一步行动列表
- `risk_table`: 风险表

`opportunity_detail`应展示`archived_files`或Evidence上的`archived_files`，图片类文件使用缩略图，其他文件使用文件卡片和可点击链接。链接应优先使用相对于HTML输出目录的`relative_path`。

## 安全规则

- 禁止`<script>`；
- 禁止内联JS事件；
- 所有用户输入必须HTML escape；
- 默认输出HTML片段，同时输出Markdown fallback。

## Extension Rules

- 新模板应注册到`display/template_manifest.yaml`和`manifest.yaml`。
- 新模板只使用`{{token}}`占位符，由Renderer负责转义和替换。
- 产品工作台可以忽略HTML文件路径，直接消费`display_result.html`。
- CLI和验证脚本必须至少覆盖`opportunity_card`、`opportunity_kanban`和`opportunity_detail`。
