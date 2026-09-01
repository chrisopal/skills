# 咨询故事线、4A 蓝图与 PPT 内容包

- **Skill name**: `transformation-storyline-builder`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

将已审批的战略、Operating Model、华为 4A、AI、投资组合和 Roadmap 编排为适合不同受众的咨询故事线和结构化 Slide Content Pack；不承担视觉渲染。

## 适用场景

- 需要管理层汇报、专题报告、项目建议书或 PPT 内容输入

## 必需输入

- `approved-artifacts`
- `approved-4a-architecture-packages-and-traceability`
- `audience-and-decision-needs`
- `deck-purpose`
- `page-budget`
- `presentation-style-profile`

## 标准输出

- `deck-brief`
- `storyline`
- `slide-content-pack`
- `chart-specs`
- `4a-blueprint-page-specs`
- `diagram-specs`
- `appendix-plan`
- `executive-messages`
- `citation-appendix`

## 执行步骤

1. 明确受众、会议目的、需要做出的决策和页数预算
2. 选择结论先行的故事弧：Why → Diagnosis → North Star → Operating Model → Target 4A → AI → Portfolio → Roadmap → Ask
3. 根据受众决定 4A 表达深度：管理层展示总体蓝图与关键变化，架构评审展示域内模型和追溯
4. 为每页定义唯一核心结论、证据、Artifact、视觉意图和前后逻辑
5. 为 BA、IA、AA、TA 和 4A 总体蓝图生成结构化 diagram spec
6. 生成图表、流程图、路线图、预算和治理规格
7. 生成附录、术语、4A 对象索引和证据索引
8. 输出给外部 PPT Template/Rendering Skill，不直接改写分析结论

## 4A 页面规则

- 总体 4A 页必须表达业务牵引与技术支撑关系，不能只是四层堆叠
- BA 页重点表达价值流、能力、流程和组织变化
- IA 页重点表达业务信息、数据域、责任、标准、流转和知识底座
- AA 页重点表达应用服务、边界、集成和演进策略
- TA 页重点表达平台、部署、安全、韧性和运维
- Integration、Security、AI、Governance 以横向能力或叠加层表达，不作为第五个 A
- 页面中的每个关键架构对象必须引用已批准 4A Artifact

## 质量规则

- 一页只传达一个主结论
- 标题必须是结论性标题而非主题名
- 每页必须引用已审批 Artifact 或 Evidence
- 不得在 PPT 阶段创造新事实、数字或 4A 架构组件
- 视觉 Skill 只能优化表达，不能改变结论、对象、关系和数据
- IA/DA 名称可以按客户口径显示，但内部引用保持 IA

## 依赖 Skill

- `to-be-enterprise-architecture`
- `consulting-quality-review`

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- 4A 页面需标明源 Artifact ID 和适用状态（As-Is/To-Be/Transition）。
- 修改已批准内容时必须回到上游 Artifact 形成新版本，不得只改 Slide。

## 失败与降级

- 缺少已批准 4A Artifact 时，不得生成“正式目标架构”页面；可以生成待确认占位和缺口说明。
- 证据冲突时保留多版本观点，降低置信度并创建验证问题。
- 页数不足时优先保留目标 4A 总体蓝图，分域细节移入附录，而不是删除追溯和关键决策。

## 最小验收

- Storyline 包含 Operating Model 与 Target 4A 的清晰衔接。
- 所有架构图对象可追溯到 approved Artifact。
- 输出可由 PPT Skill 直接渲染，不需要其补做咨询分析。
