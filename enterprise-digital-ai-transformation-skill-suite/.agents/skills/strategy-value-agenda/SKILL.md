# 战略、价值议程与架构驱动原则

- **Skill name**: `strategy-value-agenda`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

把企业战略、经营目标和管理层关注点转化为价值议程、结果指标、转型原则和能够牵引 Operating Model 与华为 4A 的架构驱动原则。

## 适用场景

- 项目启动后需要统一“为什么转、转成什么、如何衡量”
- 需要为 BA/IA/AA/TA 提供战略约束和设计方向

## 必需输入

- `project-charter`
- `fact-register`
- `strategy-documents`
- `management-interviews`
- `financial-and-operational-kpis`

## 标准输出

- `strategic-context`
- `value-agenda`
- `outcome-kpi-tree`
- `transformation-principles`
- `architecture-driving-principles`
- `north-star-hypotheses`

## 执行步骤

1. 提取增长、效率、客户、风险、韧性、创新和可持续等战略主题
2. 区分战略事实、管理层观点、外部假设和待验证命题
3. 建立 Objective → Value Driver → KPI/Outcome 的价值树
4. 定义 Operating Model 和 4A 需要遵循的业务优先、数据原则、应用原则、技术原则、AI 原则和治理原则
5. 把战略约束转为可验证的 North Star 假设和设计问题
6. 明确价值冲突和取舍，例如统一与灵活、集中与自治、速度与控制、利旧与重构

## 质量规则

- 每个战略主题必须有来源和业务含义
- KPI 必须有定义、公式、Owner、基线或基线获取计划
- 架构原则必须能指导设计取舍，不能只是口号
- 原则应说明适用范围、理由、影响和允许例外的条件
- 不得在战略阶段提前锁定具体厂商产品

## 依赖 Skill

- `evidence-factbase`

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- `architecture-driving-principles` 应按 BA/IA/AA/TA/cross-cutting 分类。
- 所有事实性结论必须关联 Evidence ID；无法确认的内容写入 Assumption Register。

## 失败与降级

- 缺少战略资料时，可基于管理层访谈形成假设版，但必须标记 `assumed`。
- KPI 无基线时输出基线采集任务，不得虚构数字。

## 最小验收

- Value Agenda 能牵引 To-Be Operating Model。
- 架构驱动原则能用于评审至少一个 BA、IA、AA、TA 设计取舍。
- 通过 `consulting-quality-review` 对应检查。
