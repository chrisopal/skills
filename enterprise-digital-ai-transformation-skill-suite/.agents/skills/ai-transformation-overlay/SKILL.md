# AI 转型 4A 叠加层与人机协同设计

- **Skill name**: `ai-transformation-overlay`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

把 AI 从孤立用例提升为贯穿 BA、IA、AA、TA 的转型设计，并形成 Human-Agent-System、数据知识、应用服务、技术平台、评测和治理的一体化方案。

## 适用场景

- 项目包含生成式 AI、Agent、知识库、预测优化或智能决策；
- 需要在传统数字化蓝图上增加 AI Operating Model。

## 必需输入

- `value-agenda`
- `as-is-operating-model`
- `to-be-operating-model`
- `as-is-4a-architecture-package`
- `target-4a-architecture-package`
- `data-and-knowledge-assets`
- `risk-and-compliance-requirements`

## 标准输出

- `ai-transformation-overlay`
- `ai-opportunity-landscape`
- `ai-use-case-portfolio-candidates`
- `ba-ai-human-agent-system-designs`
- `ia-ai-data-knowledge-semantic-design`
- `aa-ai-agent-skill-application-design`
- `ta-ai-platform-runtime-engineering-design`
- `ai-4a-traceability-matrix`
- `evaluation-and-observability-model`
- `responsible-ai-governance`
- `ai-foundation-gaps`

## 执行步骤

1. 在 BA 的任务、决策、知识工作和跨组织协同层识别 AI 机会。
2. 设计 BA+AI：Human-Agent-System 责任、授权、交接、升级、控制和业务 KPI。
3. 设计 IA+AI：数据、知识、Ontology、语义、评测集、反馈数据、质量、权限和溯源。
4. 设计 AA+AI：AI 应用、Agent、Skill、RAG、Memory、Tool Connector、工作台、API 和事件协同。
5. 设计 TA+AI：模型服务、Agent Runtime、算力、向量/图引擎、MLOps/LLMOps、可观测性、安全、容量和成本。
6. 定义离线评测、在线评测、Trace、人工升级、回滚和审计。
7. 评估价值、可行性、数据准备度、风险、复用性和变革难度。
8. 把 AI 基础能力和场景需求反馈到 Target 4A、Gap、Initiative 和 Roadmap。

## 质量规则

- 不得为了使用 AI 而创造场景。
- 每个场景必须有 BA 业务 KPI、IA 数据/知识要求、AA 服务边界和 TA 工程要求。
- 高风险决策必须定义人类授权、升级和回滚。
- 知识与数据来源必须可追溯并受权限控制。
- Agent 不得绕过系统权威记录、业务规则和审计控制。
- AI 结论必须与 Operating Model 和 Target 4A 一致。

## 依赖 Skill

- `as-is-enterprise-architecture`
- `strategy-value-agenda`
- `to-be-operating-model`
- `to-be-enterprise-architecture`

## Artifact 规则

- 所有输出必须带 `architecture_domains: [BA, IA, AA, TA, cross-cutting]`。
- 每个 AI 场景必须关联对应 4A Node ID。
- 事实性结论必须关联 Evidence ID；设计假设和模型能力假设必须显式记录。

## 失败与降级

- 任一关键架构域缺失时，AI 场景不得进入推荐 Portfolio，只能标为 exploration。
- 无法定义评测、责任或人工兜底时，高风险场景不得进入生产路线图。

## 最小验收

- 每个优先 AI 场景均完成 BA+AI、IA+AI、AA+AI、TA+AI 四项设计。
- 通过 AI 4A 追溯和安全验收测试。
