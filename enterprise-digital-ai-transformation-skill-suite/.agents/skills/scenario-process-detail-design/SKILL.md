# 重点场景、L3-L5 流程与 4A 实施级详细设计

- **Skill name**: `scenario-process-detail-design`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

对优先灯塔场景或重点流程进行可实施级详细设计，把 Target Operating Model 和 4A 蓝图下钻为流程、信息、应用、技术、控制和 MVP 需求。

## 必需输入

- `approved-target-operating-model`
- `approved-target-4a-architecture-package`
- `priority-scenario`
- `initiative-card`
- `constraints-and-standards`

## 标准输出

### BA Detail

- `l3-l5-process-model`
- `service-blueprint-or-user-journey`
- `raci-decision-rights-business-rules-controls`
- `human-agent-system-workflow`

### IA Detail

- `business-object-and-data-requirement-spec`
- `information-flow-and-lineage-spec`
- `master-data-metric-quality-security-spec`
- `knowledge-semantic-and-evaluation-data-spec`

### AA Detail

- `application-service-and-functional-requirement-spec`
- `integration-api-event-spec`
- `agent-skill-tool-and-human-workbench-spec`
- `permission-audit-and-exception-spec`

### TA Detail

- `deployment-runtime-capacity-and-nfr-spec`
- `security-observability-operations-and-dr-spec`
- `environment-devsecops-mlops-llmops-spec`

### Delivery

- `mvp-scope`
- `acceptance-criteria`
- `ai-evaluation-spec`
- `codex-ready-task-breakdown`

## 执行步骤

1. 确认场景业务结果、KPI、Owner、范围和 Initiative。
2. 下钻 BA 到 L3-L5，设计正常、异常、决策、控制和人机责任。
3. 下钻 IA，定义业务对象、数据、知识、指标、质量、权限和血缘。
4. 下钻 AA，定义应用服务、功能、交互、集成、Agent/Skill 和人工工作台。
5. 下钻 TA，定义部署、Runtime、NFR、安全、运维、可观测性和工程流水线。
6. 形成 MVP、验收标准、评测和实施任务。

## 质量规则

- 详细设计不得超出批准的 Target 4A 边界，除非发起 Architecture Change。
- 每项功能必须回溯到 BA 流程/规则和 IA 信息对象。
- 每项技术要求必须回溯到 AA 服务或 NFR。
- 异常、权限、审计、人工接管和回滚必须完整。

## 依赖 Skill

- `to-be-enterprise-architecture`
- `gap-initiative-design`

## Artifact 规则

- 所有输出必须带 `artifact-header`，并标明 `architecture_domains` 与源 Target 4A Node ID。
- 输入的 `approved-target-operating-model` 与 `approved-target-4a-architecture-package` 只读；新增边界必须创建 Architecture Change Request。
- 详细需求、接口、数据、NFR 和验收标准必须保持 BA/IA/AA/TA 追溯。

## 失败与降级

- 未取得批准的目标 Operating Model 或 Target 4A 时，不得输出 implementation-ready 状态。
- 某一 4A 域资料不足时，标记为 `blocked` 或明确 N/A 理由，不得以通用模板补造客户设计。
- AI 场景无法定义评测、人工升级和回滚时，只能进入探索性 POC，不得进入生产 MVP。

## 最小验收

- BA/IA/AA/TA 四类详细设计齐全或有明确 N/A 理由。
- 可直接进入产品设计、招标、开发或配置实施。
