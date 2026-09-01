# 咨询项目范围与章程定义

- **Skill name**: `engagement-scoping`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

将客户诉求、合同边界和管理层预期转化为可执行的咨询项目章程，并在 G0 明确华为 4A 企业架构的范围、深度和裁剪规则。

## 适用场景

- 项目启动、范围重置、阶段扩展或交付物重定义

## 必需输入

- `sponsor-brief`
- `proposal-or-contract`
- `company-profile`
- `known-constraints`

## 标准输出

- `project-charter`
- `scope-map`
- `stakeholder-map`
- `deliverable-catalog`
- `interview-plan`
- `question-backlog`
- `methodology-profile`
- `architecture-framework-profile`

## 执行步骤

1. 澄清业务背景、触发事件、决策者与需要做出的管理决策
2. 定义 in-scope、out-of-scope、组织/区域/业务/时间边界
3. 定义成功标准、关键 KPI、交付物、里程碑和审批人
4. 形成利益相关者地图、访谈计划与资料清单
5. 建立 `architecture-framework-profile`：固定 BA/IA/AA/TA 四域，定义各域范围、最低深度、横向视图、As-Is/To-Be/Transition 状态和追溯阈值
6. 登记关键假设、约束、风险和待决问题

## 质量规则

- 范围必须同时定义包含项和排除项
- 每项交付物必须有用途、受众、审批人和完成标准
- 不得把尚未确认的客户诉求写成已批准目标
- 章程应能直接驱动后续证据采集与工作流选择
- 4A 可裁剪深度和视图，但不得删除 BA、IA、AA、TA 任一域；IA 的内部标准代码固定为 `IA`

## 依赖 Skill

- 无强制前置 Skill；仍需满足对应 Artifact 输入。

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- 所有事实性结论必须关联 Evidence ID；无法确认的内容写入 Assumption Register。
- 产物默认状态为 `draft`，经业务/IT Owner 核验后为 `validated`，经 Gate 批准后为 `approved`。
- 修改已批准产物时创建新版本，并把旧版本标记为 `superseded`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实；输出 `blocked` 任务结果、缺失项和建议采集动作。
- 证据冲突时保留多版本观点，降低置信度并创建验证问题。
- 项目采用 Rapid 工作流时，可降低深度，但不能省略证据和状态标识。

## 最小验收

- 输入/输出符合 Manifest 与共享 Schema。
- 通过 `consulting-quality-review` 对应检查。
- 形成可供下游 Skill 消费的结构化 Artifact，而不只是散文报告。
- `architecture-framework-profile` 通过 `architecture-framework-profile.schema.json` 校验，并在 G0 获得批准。
