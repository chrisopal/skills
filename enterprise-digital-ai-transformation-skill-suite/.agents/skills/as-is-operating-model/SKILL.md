# As-Is Operating Model 诊断

- **Skill name**: `as-is-operating-model`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

建立现状价值链、价值流、能力、流程、组织、治理、KPI 与痛点的统一业务模型，并作为 As-Is BA 的唯一业务源模型。

## 与 4A 的边界

- 本 Skill 负责 Operating Model 的业务诊断和管理设计视角。
- `as-is-enterprise-architecture` 复用本 Skill 的节点，生成正式 As-Is BA View，并连接 IA、AA、TA。
- 不得重新创建另一套 Capability、Process、Role 或 KPI；所有节点使用稳定 Node ID。

## 适用场景

- 需要系统理解企业如何创造价值、如何协同和如何衡量绩效；
- 需要为 As-Is BA、成熟度诊断和问题分析提供业务源模型。

## 必需输入

- `fact-register`
- `value-agenda`
- `org-materials`
- `process-materials`
- `kpi-data`
- `customer-and-partner-information`

## 标准输出

- `as-is-operating-model`
- `as-is-value-chain`
- `as-is-value-streams`
- `as-is-capability-map`
- `as-is-process-hierarchy`
- `as-is-business-service-candidates`
- `as-is-org-role-model`
- `as-is-governance-model`
- `as-is-kpi-map`
- `business-information-requirements`
- `business-pain-point-map`
- `as-is-ba-source-model`

## 执行步骤

1. 从客户、产品/服务和生态定义企业价值链边界。
2. 建立 L0-L2 价值流并识别端到端责任。
3. 建立能力地图并关联战略重要性、成熟度和 Owner。
4. 建立 L0-L3 流程架构，必要时选择重点流程下钻。
5. 识别业务服务、消费者、结果和信息需求。
6. 映射组织、角色、决策权、治理机制和 KPI。
7. 将痛点、等待、返工、断点和控制风险挂接到模型节点。
8. 为所有节点分配稳定 ID，供 BA View 直接引用。

## 质量规则

- 能力、流程、组织、业务服务、信息需求和 KPI 必须交叉追溯。
- 不得把部门清单直接当作能力地图。
- 端到端流程必须跨越职能边界。
- 现状描述与改进建议分开。
- 全面到 L3，只有优先场景才进入 L4-L5。
- 不得输出 IA、AA 或 TA 方案。

## 依赖 Skill

- `strategy-value-agenda`
- `evidence-factbase`

## Artifact 规则

- 所有输出必须带 `artifact-header` 和 `architecture_domains: [BA]`。
- 所有事实性结论必须关联 Evidence ID；无法确认的内容写入 Assumption Register。
- 产物默认状态为 `draft`，经业务 Owner 核验后为 `validated`，经 Gate 批准后为 `approved`。
- 修改已批准产物时创建新版本，并把旧版本标记为 `superseded`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实；输出 `blocked` 任务结果、缺失项和建议采集动作。
- 证据冲突时保留多版本观点，降低置信度并创建验证问题。
- 项目采用 Rapid 工作流时，可降低深度，但不能省略核心价值流、能力、流程、Owner、KPI 和信息需求。

## 最小验收

- 输入/输出符合 Manifest 与共享 Schema。
- 与 BA 使用相同 Node ID。
- 通过 `consulting-quality-review` 对应检查。
- 形成可供 As-Is 4A 消费的结构化 Artifact，而不只是散文报告。
