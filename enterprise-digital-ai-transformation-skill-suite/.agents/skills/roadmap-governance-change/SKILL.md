# 三年路线图、Transition Architecture、治理与变革计划

- **Skill name**: `roadmap-governance-change`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

把投资组合转化为依赖驱动、资源可行、价值可验证，并与每个阶段 4A 状态一致的实施路线图和治理体系。

## 适用场景

- 需要形成年度/季度路径、项目群、Transition Architecture、治理组织和变革计划

## 必需输入

- `recommended-portfolio`
- `dependency-graph`
- `4a-investment-profile`
- `budget-and-capacity`
- `transition-architectures`
- `target-4a-architecture-package`
- `to-be-operating-model`
- `value-realization-plan`

## 标准输出

- `multi-year-roadmap`
- `wave-plan`
- `4a-evolution-map`
- `transition-architecture-by-wave`
- `critical-path`
- `resource-demand-profile`
- `program-governance`
- `architecture-governance-and-compliance`
- `data-ai-governance`
- `change-and-communications-plan`
- `talent-and-training-plan`
- `benefit-governance`

## 执行步骤

1. 识别必须先行的制度、BA 变革、IA 治理、AA 平台/集成、TA 基础和组织能力
2. 依据依赖、价值、风险、Transition Architecture 和资源形成 Waves
3. 对每个 Wave 定义业务结果、BA/IA/AA/TA 目标状态、里程碑、决策 Gate 和交付物
4. 定义过渡期的新旧流程、新旧数据源、新旧应用和技术平台的并行关系
5. 明确数据迁移、接口切换、上线、回退、退役和稳定运行条件
6. 建立 SteerCo、Transformation Office、Architecture Board、Data/AI Governance 等机制
7. 定义业务 Owner、产品 Owner、数据 Owner、架构 Owner、项目经理和技术责任
8. 制定沟通、培训、采用、激励和组织转变计划
9. 把 KPI 基线、收益验证和纠偏机制嵌入路线图

## 质量规则

- 路线图必须由依赖、容量和 Transition Architecture 驱动，不能只是按年份均匀分配
- 每个 Wave 要有可验证业务结果和明确 4A 状态
- 治理角色必须有决策权而非只列会议名称
- 变革管理不可作为最后附录
- 路线图必须保留旧系统退役、数据迁移、双轨运行和回退节点
- 架构治理必须覆盖原则、标准、例外、评审、项目符合性和架构资产更新
- 不能出现 Roadmap 已安排 Initiative，但目标/过渡 4A 中没有对应架构状态

## 依赖 Skill

- `to-be-enterprise-architecture`
- `portfolio-business-case`
- `gap-initiative-design`

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- 每个 Wave 必须关联 Initiative、Transition Architecture、目标 KPI 和 4A 变更对象。
- 所有事实性结论必须关联 Evidence ID；无法确认的内容写入 Assumption Register。
- 产物默认状态为 `draft`，经业务、PMO 和 Architecture Board 核验后为 `validated`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实；输出 `blocked` 任务结果、缺失项和建议采集动作。
- Transition Architecture 与 Portfolio 冲突时必须返回 Portfolio 或 Target 4A 修订，不能在 Roadmap 中静默绕过。
- Rapid 工作流可按年度而非季度规划，但不能省略阶段 4A 状态和关键迁移条件。

## 最小验收

- 每个主要 Wave 有对应 Transition Architecture 和可验证业务结果。
- 关键依赖、迁移、并行运行、回退和退役节点完整。
- 通过 `consulting-quality-review` 的 G6 检查。
