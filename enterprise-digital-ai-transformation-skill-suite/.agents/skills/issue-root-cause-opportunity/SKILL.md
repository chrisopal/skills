# 问题、根因与 4A 机会识别

- **Skill name**: `issue-root-cause-opportunity`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

把分散痛点转化为有证据的 Issue Tree、根因链、影响量化和转型机会主题，并把问题精确挂接到 Operating Model、BA、IA、AA、TA 或跨域关系。

## 适用场景

- As-Is Operating Model 与 4A 基线完成后需要形成诊断结论和设计重点

## 必需输入

- `as-is-operating-model`
- `as-is-4a-architecture-package`
- `as-is-4a-traceability-matrix`
- `as-is-4a-issue-and-debt-register`
- `fact-register`
- `performance-data`

## 可选输入

- `maturity-assessment`
- `benchmark-profile`

## 标准输出

- `issue-tree`
- `root-cause-map`
- `4a-breakpoint-map`
- `impact-assessment`
- `opportunity-themes`
- `priority-diagnostic-findings`
- `target-design-questions`

## 执行步骤

1. 按价值、客户、效率、风险和能力对问题归类
2. 区分症状、直接原因、系统性根因和约束
3. 将根因挂接到 Operating Model、BA、IA、AA、TA 或 cross-cutting 节点
4. 识别 4A 断链：业务需求无信息支撑、数据无责任、能力无应用服务、应用无技术保障、技术组件无业务来源等
5. 用业务数据或区间估算影响，并登记计算口径
6. 识别单域问题与跨域系统性问题，避免把所有问题都归因为“系统不好”或“数据不准”
7. 形成跨问题的机会主题和目标设计问题

## 质量规则

- 每个核心结论必须有事实链而非单点印象
- 根因不得停留在“系统不好”“数据不准”等泛化表述
- 问题必须标注主架构域和关联架构域
- 量化必须保留基线、公式、假设和区间
- 机会主题应描述要改变的机制，不直接等同于采购某产品
- 跨域根因必须保留关系断点，不得强行归入单一 A

## 依赖 Skill

- `as-is-operating-model`
- `as-is-enterprise-architecture`

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- 每个 Issue/Root Cause 必须关联 Evidence 和受影响的 4A 对象或关系。
- 无法确认的内容写入 Assumption Register。
- 产物默认状态为 `draft`，经业务和架构 Owner 核验后为 `validated`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实；输出 `blocked` 任务结果、缺失项和建议采集动作。
- 证据冲突时保留多版本观点，降低置信度并创建验证问题。
- As-Is 4A 追溯覆盖不足时，输出诊断置信度和补充建模任务。

## 最小验收

- 每个优先根因可追溯到证据、业务影响和具体 4A 对象/关系。
- 能区分“应用功能缺失”和“BA 流程责任不清”两类不同根因。
- 通过 `consulting-quality-review` 对应检查。
