# To-Be 华为 4A 企业架构与过渡架构

- **Skill name**: `to-be-enterprise-architecture`
- **Version**: `1.3.0`
- **类型**: 可复用咨询 SOP

## 目的

以华为 4A 为统一主干，将目标 Operating Model 正式化为 Target BA，并设计 Target IA、AA、TA、横向架构和 Transition Architecture。

## 适用场景

- 形成企业级数字化/智能化目标蓝图；
- 设计应用整合、数据治理、平台底座、云化和 AI 架构；
- 为 Gap、投资组合和三年路线图提供结构化目标状态。

## 必需输入

- `to-be-operating-model`
- `as-is-4a-architecture-package`
- `as-is-4a-traceability-matrix`
- `architecture-driving-principles`
- `non-functional-requirements`
- `regulatory-and-risk-constraints`
- `technology-and-product-constraints`

## 标准输出

### BA

- `target-business-architecture`
- `target-business-service-catalog`
- `target-business-information-requirements`

### IA

- `target-information-architecture`
- `target-information-domain-and-business-object-model`
- `target-master-data-metric-semantic-model`
- `target-information-flow-data-product-knowledge-architecture`
- `target-data-governance-quality-security-model`

### AA

- `target-application-architecture`
- `target-application-service-catalog`
- `target-domain-product-platform-boundaries`
- `target-capability-process-application-map`
- `target-business-object-application-crud-map`
- `target-integration-api-event-architecture`
- `application-rationalization-plan`

### TA

- `target-technology-architecture`
- `target-technology-service-catalog`
- `target-cloud-edge-network-platform-architecture`
- `target-data-integration-ai-platform-architecture`
- `target-devsecops-mlops-observability-architecture`
- `target-security-resilience-dr-operations-architecture`
- `technology-standards-and-product-strategy`

### Cross-Domain & Transition

- `target-4a-architecture-package`
- `target-4a-traceability-matrix`
- `architecture-principles-and-standards`
- `architecture-decision-records`
- `integration-and-interoperability-architecture`
- `security-and-trust-architecture`
- `ai-and-knowledge-architecture-view`
- `nfr-allocation`
- `transition-architectures`

## 执行步骤

1. **正式化 Target BA**：复用目标 Operating Model 的节点，补充业务服务、业务信息需求和架构责任。
2. **设计 Target IA**：定义信息域、业务对象、主数据、指标语义、数据产品、知识、信息流、Owner、标准、质量、安全和生命周期。
3. **设计 Target AA**：由 BA 能力/流程和 IA 信息需求推导应用服务、应用域、数字产品、共享平台、集成和 AI 应用边界。
4. **设计 Target TA**：由 AA/IA 和 NFR 推导技术服务、平台、基础设施、工程运维、安全、韧性、标准和产品策略。
5. **设计横向架构**：形成 Integration、Security & Trust、AI & Knowledge、NFR、Governance 视图。
6. **记录架构决策**：对重大边界、选型和模式保留备选方案、权衡和 Decision Record。
7. **形成 4A 追溯**：确保每个关键 AA/TA 组件回溯到业务价值和信息需求。
8. **设计过渡架构**：G4给出候选阶段状态、迁移依赖与演进动作；G5投资组合确认后由G6固化Wave、时间和资源。不把候选波次当作已批准路线图。

## 质量规则

- 第一阶段读取 `shared/references/phase-one-planning.md`，制造业读取 `shared/references/manufacturing-planning-toolkit.md`；目标BA复用L1-L4流程，IA不可省略。AA明确L4/信息对象映射、服务边界、CRUD权威源、集成及异常处理；TA明确云边端逻辑部署、IT/OT分区、断网降级、NFR、恢复、运维责任和成本假设，避免提前输出设备或接口实施规格。

- 每个目标组件必须支持明确的能力、流程、业务服务、信息对象或 NFR。
- 先定义能力、服务和架构模式，再选择产品。
- 目标架构必须包含利旧、新建、改造、整合、迁移和淘汰策略。
- 数据责任、应用责任、技术责任和业务 Owner 必须清晰。
- 必须说明 NFR、安全、运维、迁移、成本和合规约束。
- IA/AA/TA 不得反向改变已批准 Target BA，除非发起正式设计变更。
- Transition Architecture 必须可由 Roadmap Wave 消费。

## 依赖 Skill

- `strategy-value-agenda`
- `to-be-operating-model`
- `as-is-enterprise-architecture`

## Artifact 规则

- 所有输出必须带 `artifact-header`、`architecture_domains`、`state: to-be/transition`。
- 4A View 使用 `architecture-view.schema.json`。
- 跨域关系使用 `architecture-traceability.schema.json`。
- 设计假设和未决决策必须显式记录。
- 经业务/IT/Architecture Board 核验后为 `validated`，经 G4 批准后为 `approved`。

## 失败与降级

- G4前可消费经业务评审的候选Operating Model并保留其实际状态；G4对OM和4A共同审批，二者均获批准才将Target BA标为approved，不因同阶段未审批而禁止设计草案。
- 关键 IA/AA/TA 选择存在重大争议时，输出备选架构和决策请求。
- Rapid 工作流可以降低对象粒度，但 BA、IA、AA、TA、关键追溯和过渡原则不得缺失。

## 最小验收

- Target BA/IA/AA/TA 四域完整。
- G4抽样目标Application Service可追溯到BA、IA、TA、Owner、KPI/证据；Gap/Initiative正式关系在G5补齐，Wave在G6补齐，不因缺后续成果阻断G4。
- 至少形成一个可供 Roadmap 使用的 Transition Architecture。
- 通过 `consulting-quality-review` 的 G4 4A 检查。
