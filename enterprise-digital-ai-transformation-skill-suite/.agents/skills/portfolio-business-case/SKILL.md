# 组合优先级、4A 投资与商业论证

- **Skill name**: `portfolio-business-case`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

对转型举措进行价值、可行性、风险、4A 变更范围和依赖评估，形成投资组合、三年预算、TCO 和价值实现模型。

## 适用场景

- 需要确定先后顺序、预算、TCO、收益、回收期或管理层投资决策

## 必需输入

- `initiative-catalog`
- `architecture-change-package-map`
- `target-4a-architecture-package`
- `transition-architectures`
- `baseline-kpis`
- `cost-rates`
- `benefit-assumptions`
- `resource-capacity`
- `risk-model`
- `strategic-priorities`

## 标准输出

- `prioritization-model`
- `initiative-scorecards`
- `recommended-portfolio`
- `4a-investment-profile`
- `budget-and-capacity`
- `three-year-budget`
- `tco-model`
- `benefit-case`
- `cash-flow-and-payback`
- `sensitivity-analysis`
- `value-realization-plan`

## 执行步骤

1. 定义与项目一致的价值、战略、可行性、数据准备度、风险、4A 复杂度和依赖评分
2. 按 Initiative 的 BA/IA/AA/TA 变更包估算业务变革、数据治理、应用建设、集成、平台、迁移和技术基础成本
3. 估算软件、基础设施、实施、内部人力、变革、运营、过渡期双轨运行、数据迁移、退役和预备金
4. 估算收入、利润、成本、营运资本、风险、合规、速度和体验收益
5. 形成基准、保守和积极情景
6. 结合依赖、Transition Architecture、资源容量和价值选择组合，而非仅按单项得分排序
7. 为每项收益定义 Owner、基线、目标、实现时间和验证机制
8. 输出按 BA/IA/AA/TA/cross-cutting 分类的投资构成，支持管理层理解“钱投到哪里”

## 质量规则

- 所有数字必须注明来源、口径、假设、置信区间和税/币种口径
- 不得把重复收益在多个 Initiative 中累计
- 软收益与财务收益分开呈现
- 预算必须包含持续运营、组织变革、迁移、并行运行和退役成本
- 不得只估软件采购而忽略 IA 治理、BA 变革和 TA 运维成本
- 优先级模型的权重必须可配置并经审批
- 投资组合必须与 Target 4A 和 Transition Architecture 一致

## 依赖 Skill

- `to-be-enterprise-architecture`
- `gap-initiative-design`

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- 每笔重大成本必须关联 Initiative 和 4A 变更包。
- 每项收益必须关联 KPI、Owner 和验证机制。
- 产物默认状态为 `draft`，经业务、CFO/CIO 和 Architecture Board 核验后为 `validated`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实；输出 `blocked` 任务结果、缺失项和建议采集动作。
- 证据冲突时保留多版本观点，降低置信度并创建验证问题。
- Transition Architecture 未完成时，必须显式增加迁移与并行运行不确定性区间。

## 最小验收

- 每个优先 Initiative 有价值、4A 变更范围、成本、依赖和风险。
- 总预算可按年度、Initiative、成本类型和 4A 域分解。
- 通过 `consulting-quality-review` 对应检查。
