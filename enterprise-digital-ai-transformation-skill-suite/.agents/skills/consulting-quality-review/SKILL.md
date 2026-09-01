# 独立质量、4A 追溯与一致性审查

- **Skill name**: `consulting-quality-review`
- **Version**: `1.2.0`
- **类型**: 可复用咨询 SOP

## 目的

独立检查证据充分性、Operating Model 与 BA 单一源、4A 完整性、跨域追溯、数字口径、逻辑链和 Gate 退出条件。

## 必需输入

- `artifact-register`
- `candidate-artifacts`
- `evidence-register`
- `quality-gate-definition`
- `project-charter`
- `architecture-framework-profile`

## 标准输出

- `quality-review-report`
- `4a-completeness-report`
- `4a-traceability-matrix`
- `unsupported-claim-list`
- `consistency-issue-list`
- `rework-actions`
- `gate-recommendation`

## 执行步骤

1. 检查 Artifact Header、版本、状态、architecture_domains 和依赖完整性。
2. 检查 Operating Model 与 BA 是否复用相同 Node ID。
3. 检查 BA、IA、AA、TA 的必需对象、View 和 Owner 是否完整。
4. 检查 Objective/KPI → BA → IA/AA → TA → Gap → Initiative → Benefit → Transition/Roadmap 的追溯链。
5. 抽查结论、数字、图表与 Evidence ID。
6. 检查 As-Is/To-Be/Transition/Gaps/Initiatives 的名称、边界和状态一致性。
7. 检查 Integration、Security & Trust、AI & Knowledge、NFR、Governance 是否贯穿 4A。
8. 检查预算收益是否重复、假设是否显式。
9. 根据 Gate 规则给出 pass、conditional-pass 或 fail，并生成修订任务。

## 质量规则

- Reviewer 不得审查自己刚生成的产物并自行批准。
- 发现无证据结论时必须阻止升级为 validated。
- 发现 AA 无 BA/IA 映射或 TA 无支撑关系时，G2/G4 必须 fail。
- 发现 Operating Model 与 BA 冲突时，必须先修复单一源模型。
- Gate 建议必须列明不通过项与修订动作。
- 不得为了排版完整而降低事实和逻辑要求。

## Artifact 规则

- `quality-review-report` 必须通过 `quality-review-report.schema.json` 校验。
- Reviewer 与候选 Artifact 的生成者必须不同；无法满足独立性时只能输出 `fail` 或请求外部复核。
- `pass` 报告不得包含阻断项；`conditional-pass` 和 `fail` 必须给出 Owner 与可验证的修订动作。

## 最小验收

- 质量报告包含四域完整性、纵向追溯、横向视图和状态一致性结论。
- 所有阻断项有明确 Artifact、Node、Owner 和修订动作。
