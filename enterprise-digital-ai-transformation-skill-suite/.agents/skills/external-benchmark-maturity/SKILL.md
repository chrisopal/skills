# 外部标杆、成熟度与 4A 能力评估

- **Skill name**: `external-benchmark-maturity`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

基于可配置成熟度模型和行业参考包，对现状业务能力、数字化能力和华为 4A 架构能力进行证据化评分，并定义目标成熟度。

## 适用场景

- 需要快速识别能力短板、架构治理短板和行业差距

## 必需输入

- `fact-register`
- `industry-reference-pack`
- `maturity-model`
- `peer-benchmark-sources`
- `value-agenda`

## 标准输出

- `maturity-assessment`
- `operating-model-maturity-assessment`
- `ba-maturity-assessment`
- `ia-maturity-assessment`
- `aa-maturity-assessment`
- `ta-maturity-assessment`
- `cross-cutting-maturity-assessment`
- `4a-maturity-profile`
- `benchmark-profile`
- `score-evidence-map`
- `target-maturity`
- `maturity-heatmap-data`

## 执行步骤

1. 确认评估对象、维度、等级定义和证据要求
2. 分别评估业务能力/流程、BA 治理、IA 治理、AA 管理、TA 能力和 cross-cutting 能力
3. 为每个评分关联证据、置信度和缺失项
4. 与行业标杆比较，但区分公开事实、研究估计和案例启示
5. 基于战略重要性、现状差距、实现难度和投资约束定义目标成熟度
6. 输出热力图和重点能力提升主题

## 质量规则

- 评分必须有行为或产物判据，不能凭主观印象
- 不得把“已购买系统”直接视为 AA 成熟
- 不得把“有数据平台”直接视为 IA 成熟
- 不得把“上云”直接视为 TA 成熟
- 目标成熟度不要求所有能力达到最高等级
- 外部案例不得伪装成客户事实

## 依赖 Skill

- `strategy-value-agenda`
- `evidence-factbase`

## Artifact 规则

- 所有评分必须引用 Evidence ID 或 Benchmark Source。
- 4A 成熟度按 BA/IA/AA/TA/cross-cutting 分类，并与后续 Gap 区分：成熟度是评估，Gap 是现状与目标的具体差异。

## 失败与降级

- 证据不足时只给区间或 `not-assessed`，不得强行评分。
- 行业标杆不具可比性时说明限制。

## 最小验收

- 任一分数都能说明“为什么是这个等级”。
- 4A 成熟度结果可以作为诊断和目标成熟度输入，但不会直接生成 Target 4A。
- 通过 `consulting-quality-review` 对应检查。
