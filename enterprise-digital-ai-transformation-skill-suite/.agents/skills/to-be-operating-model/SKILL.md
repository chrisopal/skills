# To-Be Operating Model 设计

- **Skill name**: `to-be-operating-model`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

围绕价值议程设计目标价值流、能力、流程、组织、决策权、治理、KPI、人才与工作方式，并作为 Target BA 的唯一业务源模型。

## 与 4A 的边界

- 本 Skill 决定未来业务如何运行。
- `to-be-enterprise-architecture` 将已批准 Operating Model 节点正式化为 Target BA，并继续设计 IA、AA、TA。
- 不得在 EA Skill 中重新发明另一套能力、流程、组织和 KPI。

## 适用场景

- 需要形成未来运营蓝图和业务变革目标；
- 需要为 Target 4A 提供业务需求和设计约束。

## 必需输入

- `value-agenda`
- `priority-diagnostic-findings`
- `opportunity-themes`
- `target-design-questions`
- `as-is-operating-model`
- `design-constraints`
- `industry-reference-pack`

## 标准输出

- `to-be-operating-model`
- `operating-model-design-principles`
- `target-value-streams`
- `target-capability-map`
- `target-process-architecture`
- `target-business-service-model`
- `target-org-role-model`
- `decision-rights-and-governance`
- `target-kpi-system`
- `talent-and-ways-of-working`
- `target-business-information-requirements`
- `to-be-operating-model-blueprint`
- `target-ba-source-model`

## 执行步骤

1. 确认目标业务结果与 Operating Model 设计原则。
2. 对关键价值流设计端到端责任和客户结果。
3. 定义目标能力、能力归属和差异化能力。
4. 定义业务服务、消费者、结果和服务水平。
5. 重构关键流程、决策、规则和控制点。
6. 设计组织边界、角色、RACI/决策权、治理和协作机制。
7. 设计 KPI、激励、人才、技能与工作方式。
8. 定义对 IA 信息、AA 应用服务、TA 非功能能力的业务需求。
9. 给出关键设计选择、备选方案和取舍。

## 质量规则

- 每项设计必须回溯到价值议程或现状根因。
- Operating Model 不等于组织架构图。
- 流程、组织、业务服务、KPI 和治理必须相互一致。
- 明确哪些能力自建、共享、外包或生态协同。
- 重大选择应保留备选方案和取舍依据。
- 输出必须足以驱动 IA、AA、TA 设计。

## 依赖 Skill

- `issue-root-cause-opportunity`
- `strategy-value-agenda`

## Artifact 规则

- 所有输出必须带 `artifact-header` 和 `architecture_domains: [BA]`。
- 所有事实性结论必须关联 Evidence ID；设计假设写入 Assumption Register。
- 产物默认状态为 `draft`，经业务 Owner 核验后为 `validated`，经 Gate 批准后为 `approved`。
- 修改已批准产物时创建新版本，并把旧版本标记为 `superseded`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实。
- 重大设计取舍未形成共识时，保留备选方案，不得假装已批准。
- Rapid 工作流可降低细节，但必须保留价值流、能力、业务服务、关键流程、组织治理、KPI 和信息需求。

## 最小验收

- 输入/输出符合 Manifest 与共享 Schema。
- Target BA 可直接引用相同 Node ID。
- 通过 `consulting-quality-review` 对应检查。
- 形成可供 Target 4A 消费的结构化 Artifact，而不只是散文报告。
