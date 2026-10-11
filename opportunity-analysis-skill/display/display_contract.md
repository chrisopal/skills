# Display Contract

Display层只接收结构化数据，不直接消费自然语言摘要。

默认实现是`src/opportunity_skill/renderer.py`。宿主Agent或产品工作台可以替换模板、CSS或Renderer，但必须保持输入为结构化数据，输出包含HTML和Markdown fallback。

## 模板

- `opportunity_card`: 商机摘要卡
- `opportunity_detail`: 商机详情页
- `customer_profile`: 客户画像卡
- `opportunity_list`: 默认商机列表
- `opportunity_kanban`: 可选商机看板
- `next_action_list`: 下一步行动列表
- `risk_table`: 风险表

`opportunity_detail`应展示`archived_files`或Evidence上的`archived_files`，图片类文件使用缩略图，其他文件使用文件卡片和可点击链接。链接应优先使用相对于HTML输出目录的`relative_path`。

`opportunity_detail`还应展示`decision_chain`，把客户需求负责人、项目推进负责人、最终决策人、技术/IT负责人和采购/商务负责人区分开。缺失节点不能静默省略，应显示为待补充。

`opportunity_detail`必须展示`commercial_assessment`和`sales_confirmation_questions`：三组评分、评估可信度、关键待确认数量、维度判断依据，以及优先要问商务人员的问题。商务回答进入`commercial_assessment.dimensions[].answer`后，应展示为已确认依据。

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


## 生命周期与静态导航

详情和查询条目读取 `lifecycle`：`current_stage_id` 是正式阶段，`suggested_stage_id` 是材料建议，`status` 单独表示进行中、暂停、丢单或取消。正式阶段轨迹只点亮当前阶段，不按序号构造已完成标记。旧数据缺少 lifecycle 时，原 `opportunity.stage_id/stage` 仅作建议阶段，当前阶段待确认且历史为空。

首屏显示负责人、下一行动、期限、阻塞和版本；`actions` 展示完成结果及 `evidence/evidence_ids`，`history` 展示真实迁移，`facts`、`artifacts`、`contracts` 保留登记值。失效、文件变更或被新版本替代的成果仍可见。文件状态只反映已登记文件的完整性检查，不表示客户验收、证据事实已核验或合同法律效力；空成果集合显示未登记。长编号、校验值和原始结构化字段放入原生 `details`。

查询条目可为扁平商机对象或带 `opportunity/lifecycle` 的详情对象。列表与看板仅在条目实际提供 `detail_url` 或 `url` 时显示导航链接；无 URL 时标题是普通文字。材料链接优先 relative_path，拒绝脚本、data 和协议相对 URL；链接不可用时保留文件名称及不可用状态。此展示层没有写操作、脚本或事件处理器。

`SkillDisplayRenderer.render(..., theme="light" | "dark", profile="enterprise" | "legacy")` 保持 HTML/Markdown 双输出。默认 enterprise 使用内嵌本地语义 Token，无 CDN 或额外依赖；legacy 只恢复原 CSS，业务字段与生命周期行为保持当前规则。浏览器检查与业务验收分别记录。
