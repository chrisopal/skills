# 数字化与 AI 转型咨询主编排

- **Skill name**: `dtx-consulting-orchestrator`
- **Version**: `1.2.0`
- **类型**: 可复用咨询 SOP

## 目的

管理项目状态、依赖、任务卡、人工门禁与子 Skill 调用顺序，并确保 Enterprise Architecture 始终采用华为 4A（BA/IA/AA/TA）内容模型。主 Skill 只做编排，不替代任何专业分析 Skill。

## 适用场景

- 启动或继续一个端到端数字化/AI 转型咨询项目
- 需要判断下一步应调用哪个 Skill
- 需要生成阶段任务卡、检查依赖或推进人工 Gate
- 需要检查 Operating Model、4A、AI、Gap、Roadmap 是否按正确顺序衔接

## 必需输入

- `project-context`
- `artifact-register`
- `workflow-profile`
- `architecture-framework-profile`
- `gate-decisions`
- `open-issues`

## 标准输出

- `run-plan`
- `task-cards`
- `project-state`
- `dependency-status`
- `4a-completeness-status`
- `gate-request`
- `issue-log`

## 执行步骤

1. 读取 AGENTS.md、项目上下文、工作流、华为 4A 规范与 Artifact Register
2. 判断当前阶段、已完成 Gate、阻塞项与缺失输入
3. 对 EA 阶段检查 BA/IA/AA/TA 四域、Cross-cutting 视图和 Traceability Matrix 的完整性
4. 按 `task-card.schema.json` 仅生成一个可执行任务卡，并指定唯一主 Skill、输入版本、预期输出、验收条件、Gate 和独立 Reviewer
5. 执行后登记产物版本、架构域、来源、状态与依赖
6. 调用 `consulting-quality-review` 进行独立检查
7. 满足退出条件后提交人工 Gate；未通过则创建修订任务卡

## 4A 编排规则

- G2 前必须先完成 `as-is-operating-model`，再完成 As-Is 4A；不能用系统盘点代替 BA
- G4 前必须先完成 `to-be-operating-model`，再完成 Target 4A 和 `target-4a-traceability-matrix`
- `ai-transformation-overlay` 可以与 Target 4A 迭代，但其新增对象必须回写 4A 后才可批准
- G5 只消费已经批准或至少 validated 的 4A Gap 和 Target 4A 对象
- G6 必须使用 Transition Architecture，不能仅按年份排列项目
- G8 不得允许 PPT Skill 创建新的 4A 对象

## 质量规则

- 不得直接完成业务分析、架构设计、路线图或 PPT 内容
- 不得跳过 Evidence、As-Is、To-Be、4A、Portfolio 等必要 Gate
- 不得把 draft/assumed 产物当作 validated/approved 产物
- 每次只下发一个主任务卡，避免多个 Skill 并行修改同一核心 Artifact
- 缺少任一 BA、IA、AA、TA 关键产物时，4A 完整性状态不得为 complete

## 依赖 Skill

- 无强制前置 Skill；仍需满足对应 Artifact 输入。

## Artifact 规则

- 所有输出必须带 `artifact-header`。
- 所有任务卡必须通过 `task-card.schema.json` 校验；`blocked` 任务必须列明阻塞原因，不得伪装为 ready。
- 对架构阶段输出 `4a-completeness-status`，至少包含四域状态、孤立对象数量和追溯覆盖率。
- 所有事实性结论必须关联 Evidence ID；无法确认的内容写入 Assumption Register。
- 修改已批准产物时创建新版本，并把旧版本标记为 `superseded`。

## 失败与降级

- 缺少必需输入时，不得补造客户事实；输出 `blocked` 任务结果、缺失项和建议采集动作。
- 证据冲突时保留多版本观点，降低置信度并创建验证问题。
- Rapid 工作流可降低颗粒度，但不能取消 4A 四域覆盖与最小追溯。

## 最小验收

- 能正确阻止缺少 Target IA 或 4A Traceability 的项目进入 G4。
- 能把 AI 变更回写 Target 4A 作为后续任务，而不是直接进入 Gap/Roadmap。
- 输入/输出符合 Manifest 与共享 Schema。
