# Runtime Closure Contract

这是 `dtx-consulting-orchestrator` 的最小运行闭环快照契约：只校验可追溯性、复核证据、依赖失效和交付映射，不执行 Skill、不写数据库、不自动批准。既有登记格式到本契约的兼容适配不在范围内。

版本1.1.0。此文件是可复用技术契约，不是客户项目的批准产物。
参考 `task-card.schema.json`、`quality-review-report.schema.json` 和 `enterprise-planning.yaml`。
路径相对于校验器 `ROOT`；文件哈希能证明字节一致，不能证明文件来源或审批人身份真实性。

## JSON interface

顶层必须包含：

```json
{
  "snapshot_id": "...",
  "project_id": "...",
  "mode": "manual-simulation | host-execution",
  "execution_state": "in-progress | ready | delivered",
  "tasks": [],
  "reviews": [],
  "gate_decisions": [],
  "upstream_changes": [],
  "deliveries": []
}
```

文件引用统一为 `{id, version, sha256, path}`。校验器在 `ROOT` 下读取并重新计算 SHA-256，拒绝绝对路径、越出 ROOT、缺文件、哈希不匹配和不可读文件；不会执行文件内容。

## Task execution and stale propagation

每个任务必须声明：

- `required_input_ids` 与 `inputs` 一一对应，防止上一阶段单输入冒充多输入；
- `outputs`，每项 `status` 只能是 `candidate | validated | approved | stale`；
- `run.mode` 与快照模式一致，且为固定枚举；`run.actor`；
- `host-execution` 还必须有 `skill_name`、三段式 `skill_version` 和真实 `run.evidence_ref`。

本工具不解析 Skill Manifest 来推导必需输入，也不认证运行日志来源；
总控须先按既有任务卡 Schema/Manifest 检查任务范围，不能以缩减 required_input_ids 绕过业务前置条件。

同一快照中，下游输入引用已有任务输出的 ID 时，版本、哈希及路径必须完全一致。
`upstream_changes` 使用 `{artifact_id, from_version, to_version}`。校验器从任务 `inputs` 图递归传播 stale；`depends_on` 只能补充关系，不能作为唯一依赖来源。受影响输出若未标 `stale` 即失败。

## Review and remediation

Review 必须绑定某个任务输出的完全相同 `id/version/sha256/path`；`generated_by` 必须等于对应任务的 `run.actor`，`reviewed_by` 必须不同且 `reviewer_independent: true`。`results` 必须分别包含 `technical`、`professional`、`customer`，状态使用固定枚举。

Finding 必须有 `owner`、`due`，`status` 为 `open | closed`。开放项可以尚未有复测证据；关闭项必须提供真实 `retest_evidence` 引用。正式交付要求相关 Review 为独立审查且 `technical.status=pass`、`professional.status=pass`，并且所有 finding 已关闭并有复测证据。

`blocking`（省略时默认为 `true`）必须是布尔值；开放 blocking finding 不能与 `professional.status=pass` 并存。输出标记为 `approved` 时，同样必须有独立技术及专业 PASS、关闭整改和 customer approved Gate，即使当前没有 delivery。阶段 Gate 可以单独批准，但不能替代客户交付批准；conditional-pass 也不能替代 approved。

## Gate and simulation boundary

`manual-simulation` 不得产生 `validated`/`approved` 输出、客户 approved 结果、approved/conditional-pass Gate 或 formal delivery。它只能表达候选、开放问题和 pending/rejected 决策。

`host-execution` 的批准必须提供精确候选引用、真实 `decision_record_ref`、`decided_by`、`decided_at`，且 `gate_type=customer` 才能满足正式交付的客户 Gate。文件哈希只证明当前字节，不证明 decision record 的真实身份。

## Delivery mapping

交付可在 `execution_state=in-progress` 时为空；其他状态必须有四类且各一次的 `report`、`contentpack`、`html`、`ppt`。每项必须有完整 Artifact 引用、`page_count`、覆盖 `1..page_count` 的 `page_map`，每页 `source_id` 必须能在实际 JSON contentpack 的 `slides`/`pages` ID 中解析。

`contentpack` 必须是 JSON，页数取实际 `slides`/`pages` 数量，页面标识使用本套件的 `slide_id`，兼容 `id`，两者同时出现必须相同。
`ppt` 从 OOXML 的 presentation、关系文件和实际 slide XML 读取引用页数，允许文件编号不连续，拒绝缺失、外部、越界、重复及孤立页。
声明页数不能覆盖真实计数；不同载体页数与包页数不同时，必须用 `page_count_explanation` 解释，并逐页映射到内容包。PPT 映射必须覆盖全部内容页 ID，可为拆页重复引用同一 ID。
formal item 必须绑定状态为 approved 的实际 task output，并通过该 output 的独立技术及专业评审、关闭整改和 customer approved Gate。

报告/HTML 的视觉真实性、审批记录身份和客户事实真实性超出本 stdlib 校验器能力，必须由后续人工/专用工具验证。

## CLI

```bash
python scripts/validate_runtime_closure.py SNAPSHOT.json [ROOT]
```

标准输出为 `{passed, errors, scope}` JSON；无错误退出 `0`，有错误退出 `1`。
