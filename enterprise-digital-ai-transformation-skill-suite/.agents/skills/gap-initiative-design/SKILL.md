# 4A Gap 分析与转型举措设计

- **Skill name**: `gap-initiative-design`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

比较 As-Is 与 To-Be Operating Model 和华为 4A 架构，形成可执行的 Gap Register、Initiative Cards、工作包和依赖图。

## 必需输入

- `as-is-operating-model`
- `to-be-operating-model`
- `as-is-4a-architecture-package`
- `target-4a-architecture-package`
- `constraints`

## 可选输入

- `ai-transformation-overlay`

## 标准输出

- `ba-gap-register`
- `ia-gap-register`
- `aa-gap-register`
- `ta-gap-register`
- `cross-cutting-gap-register`
- `consolidated-4a-gap-register`
- `initiative-catalog`
- `initiative-cards`
- `architecture-change-package-map`
- `work-package-structure`
- `dependency-graph`
- `quick-win-foundation-and-retirement-map`

## 执行步骤

1. 按 BA 比较能力、流程、业务服务、组织、治理、KPI、规则和信息需求。
2. 按 IA 比较信息域、业务对象、标准、质量、责任、语义、数据产品和信息流。
3. 按 AA 比较应用服务、边界、集成、生命周期、技术债和 AI 应用能力。
4. 按 TA 比较技术服务、平台、基础设施、工程运维、韧性、安全、标准和生命周期。
5. 比较 Integration、Security & Trust、AI & Knowledge、NFR 和 Governance 横向差距。
6. 为每个 Gap 定义 As-Is/To-Be Node、严重度、价值影响、风险和前置条件。
7. 将多个相关 Gap 聚合为业务可理解的 Initiative，而不是直接使用系统模块名。
8. 为 Initiative 定义目标、范围、成果、Owner、涉及 4A 域、依赖、估算和成功指标，并生成其 BA/IA/AA/TA/cross-cutting 变更包映射。
9. 识别基础工程、灯塔场景、规模化举措、整合迁移和退役举措。

## 质量规则

- Gap 必须是现状与目标之间的差异，不是泛化问题。
- 每个 Initiative 必须关闭一个或多个明确 Gap。
- 禁止用系统模块名替代转型举措定义。
- 举措必须说明对 BA、IA、AA、TA 的影响；不涉及的域需显式标记 N/A。
- 依赖关系必须可用于 Transition Architecture 和路线图计算。

## 依赖 Skill

- `as-is-enterprise-architecture`
- `to-be-operating-model`
- `to-be-enterprise-architecture`

## 最小验收

- 每个 Gap 有 architecture_domain、as_is_node_id、to_be_node_id、Evidence 和 Initiative 映射。
- 每个 Initiative 有 affected_architecture_domains，并在 `architecture-change-package-map` 中列出新增、改造、整合、迁移、利旧与退役对象。
- 通过 4A Gap 完整性和跨域依赖检查。
