# As-Is 华为 4A 企业架构

- **Skill name**: `as-is-enterprise-architecture`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

以华为 4A 为统一主干，将现状 Operating Model 正式化为 BA，并建立 IA、AA、TA、横向视图和跨域追溯，形成可验证的企业架构事实底座。

## 适用场景

- 数字化转型现状诊断；
- 应用整合、数据治理、技术现代化或 AI 准备度评估；
- 需要识别业务断点、信息问题、系统孤岛、技术债和风险。

## 必需输入

- `fact-register`
- `as-is-operating-model`
- `application-inventory`
- `interface-list`
- `data-and-information-assets`
- `infrastructure-platform-and-security-materials`
- `non-functional-and-compliance-requirements`

## 标准输出

### BA

- `as-is-business-architecture`
- `as-is-business-service-catalog`
- `as-is-business-information-requirements`

### IA

- `as-is-information-architecture`
- `as-is-information-domain-map`
- `as-is-business-object-model`
- `as-is-information-flow-and-lineage`
- `as-is-master-data-metric-semantic-map`
- `as-is-data-ownership-quality-security-view`

### AA

- `as-is-application-architecture`
- `as-is-application-service-catalog`
- `as-is-capability-process-application-map`
- `as-is-business-object-application-crud-map`
- `as-is-integration-api-event-map`
- `as-is-application-lifecycle-and-debt-register`

### TA

- `as-is-technology-architecture`
- `as-is-technology-service-catalog`
- `as-is-platform-infrastructure-deployment-view`
- `as-is-devsecops-operations-observability-view`
- `as-is-security-resilience-and-standards-view`
- `as-is-technology-lifecycle-and-debt-register`

### Cross-Domain

- `as-is-4a-architecture-package`
- `as-is-4a-traceability-matrix`
- `as-is-integration-and-interoperability-view`
- `as-is-security-and-trust-view`
- `as-is-ai-and-knowledge-readiness-view`
- `as-is-nfr-allocation`
- `as-is-4a-issue-and-debt-register`
- `architecture-fact-gaps-and-open-questions`

## 执行步骤

1. **复用 BA 源模型**：读取 As-Is Operating Model，保留相同 Capability、Process、Role、KPI Node ID，补充 Business Service 和 Information Requirement。
2. **建立 IA**：识别信息域、业务对象、主数据、指标、语义、信息流、权威来源、Owner、质量和安全规则。
3. **建立 AA**：将应用服务和应用映射到 BA 能力/流程以及 IA 业务对象，建立接口、事件、消息和生命周期视图。
4. **建立 TA**：识别技术服务、平台、部署、基础设施、工程运维、可观测性、安全、韧性、标准和技术债。
5. **建立横向视图**：将 Integration、Security & Trust、AI & Knowledge、NFR、Governance 分配到 4A 对象。
6. **建立 4A 追溯**：至少完成 Objective/KPI → BA → IA/AA → TA 的关键链路。
7. **叠加问题与证据**：把 Issue、Root Cause、Risk、Debt、Evidence 和 Assumption 挂接到具体架构节点，并形成跨 BA/IA/AA/TA 的统一问题与技术债登记册。
8. **组织验证**：分别由业务、数据、应用、技术和安全 Owner 验证，不得把建议混入现状。

## 质量规则

- 4A 必须使用 `BA/IA/AA/TA` 标准域。
- Operating Model 与 BA 必须共享节点 ID，不得维护冲突版本。
- IA 不能仅列数据平台；必须包含信息域、业务对象、信息流、标准、质量和责任。
- AA 不能仅列系统盒子；必须包含应用服务及其 BA/IA 映射。
- TA 不能仅列基础设施；必须包含技术服务、NFR、运维、韧性和支撑关系。
- 每个关键 AA Application Service 必须至少关联一个 BA Capability/Process 和一个 IA Business Object。
- 每个关键 TA Technology Service 必须关联其支撑的 AA/IA/NFR。
- As-Is 架构不得混入未经批准的 To-Be 方案。

## 依赖 Skill

- `as-is-operating-model`
- `evidence-factbase`

## Artifact 规则

- 所有输出必须带 `artifact-header`、`architecture_domains`、`state: as-is`。
- 4A View 使用 `architecture-view.schema.json`。
- 跨域关系使用 `architecture-traceability.schema.json`。
- 所有事实性结论必须关联 Evidence ID；无法确认的内容写入 Assumption Register。
- 经业务/IT Owner 核验后为 `validated`，经 G2 批准后为 `approved`。

## 失败与降级

- 缺少某架构域材料时，不得用推测补齐；应输出 `architecture-fact-gap` 和采集计划。
- 证据冲突时保留多版本观点并降低置信度。
- Rapid 工作流可只覆盖关键域和关键关系，但 BA、IA、AA、TA 四域不得缺失。

## 最小验收

- 四个架构域均有结构化 View。
- 随机抽样关键 Application Service 可追溯到 BA、IA 和 TA。
- 通过 `consulting-quality-review` 的 G2 4A 检查。
