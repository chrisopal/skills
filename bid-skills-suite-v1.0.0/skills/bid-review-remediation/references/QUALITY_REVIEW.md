# 质量计划与逐项复核

质量闭环由宿主先读回当前原件，再保存两个项目文件：

- `profiles/quality-plan.json`：宿主把 `04-scoring.json` 的每个 `node_type=scored` 叶子拆成一个或多个 `condition_id`，并登记当前 `04/05/09` 哈希、原文引用、正文引用和受影响章节。
- `reviews/quality-review.json`：宿主逐条填写条件和共同事实的结论；`unknown` 保留未知，脚本不会预测评委分数或把语义判断改成通过。

必须先写质量计划，再创建输入快照和15评审。计划存在时，15评审的 `data.quality_review_ref` 必须精确绑定质量评审文件；没有计划的历史15评审会在 `review_checks.check` 中明确返回 `quality_gate=NOT_RUN`。

## 最小质量计划

下面对象展示字段和引用形状，哈希必须由宿主对项目内实际字节计算：

```json
{
  "schema_version": "1.0",
  "project_id": "PROJECT-001",
  "plan_id": "QP-001",
  "revision": 1,
  "inputs": [
    {"relative_path": "artifacts/04-scoring.json", "sha256": "<64 hex>"},
    {"relative_path": "artifacts/05-compliance.json", "sha256": "<64 hex>"},
    {"relative_path": "artifacts/09-evidence-selection.json", "sha256": "<64 hex>"}
  ],
  "conditions": [
    {
      "condition_id": "S1-C1",
      "scoring_id": "S1",
      "kind": "phrase",
      "description": "按原文第一档条件回读",
      "source_refs": [
        {"source_id": "SRC-001", "revision": 1, "sha256": "<64 hex>", "location": "P3", "quote": "原文条件短句", "kind": "tender"}
      ],
      "section_ids": ["CH-01"]
    }
  ],
  "facts": [
    {
      "fact_id": "F-DELIVERY-DAYS",
      "kind": "numeric",
      "expected": 30,
      "unit": "日",
      "source_refs": [
        {"source_id": "SRC-001", "revision": 1, "sha256": "<64 hex>", "location": "P4", "quote": "工期30日", "kind": "tender"}
      ],
      "body_refs": [
        {"relative_path": "artifacts/11-technical-content.json", "sha256": "<64 hex>", "location": "/data/chapters/0/body", "quote": "工期30日"}
      ],
      "section_ids": ["CH-01"]
    }
  ]
}
```

`conditions` 也可以按评分叶子分组，写成 `{ "scoring_id": "S1", "conditions": [...] }`。每个条件仍必须有唯一 `condition_id`。计划会拒绝重复、未知或缺失的评分叶子，并重新核对三份上游哈希和每个 `source_refs`。

## 最小质量评审

```json
{
  "schema_version": "1.0",
  "project_id": "PROJECT-001",
  "plan_ref": {"relative_path": "profiles/quality-plan.json", "sha256": "<64 hex>"},
  "status": "needs_review",
  "conditions": [
    {
      "condition_id": "S1-C1",
      "conclusion": "satisfied",
      "rationale": "已回读原文条件和实际正文。",
      "source_refs": [
        {"source_id": "SRC-001", "revision": 1, "sha256": "<64 hex>", "location": "P3", "quote": "原文条件短句", "kind": "tender"}
      ],
      "body_refs": [
        {"relative_path": "artifacts/11-technical-content.json", "sha256": "<64 hex>", "location": "/data/chapters/0/body", "quote": "正文实际短句"}
      ]
    }
  ],
  "facts": [
    {"fact_id": "F-DELIVERY-DAYS", "conclusion": "consistent", "rationale": "正文的30日与登记事实一致。"}
  ],
  "semantic_acceptance": "REVIEWER_SUPPLIED_NOT_CERTIFIED_BY_SCRIPT"
}
```

正文引用复用核心评审的定位规则，只能指向实际 `artifacts/11-*`、`12-*` 或 `14-*` 的具体 JSON Pointer/文本行；不能引用 `15-review`、`quality-review`、计划或其它评审文件自证。条件 `unknown` 会阻塞质量门禁；已确认的 `partial`/`missing` 只产生警告和整改动作。共同事实的数字必须在登记的正文引用中出现，短语和单位按去空白后的原文匹配；正文引用中的其它数字会报告参数冲突。

检查结果包含 `errors`、`blockers`、`warnings`、宿主原样提供的 `semantic_acceptance`，以及 `actions`/`remediation_rows`。每个动作带有 `target_id`、`row_id`、`reason`、`blocking` 和 `section_ids`，供宿主只派发受影响章节。脚本结果是机械证据，不认证企业真实性、签章、评委主观分或人工授权。

Python 调用的主入口是 `quality_checks.check(project, quality_review, plan)`；为方便宿主编排，也接受 `check(project, plan, quality_review)` 或以项目内路径传入两者。`prepare(project)` 按当前计划生成全部 `unknown` 条件和事实行。

本地命令：

```bash
python scripts/quality_checks.py prepare --project /path/to/project
python scripts/quality_checks.py check --project /path/to/project
```

## 计分阶段与绑定通过

条件结论限定为 `satisfied/partial/missing/unknown/deferred`，评分条件不能用 `not_applicable` 绕过。`deferred` 只适用于计划显式标记 `phase: "evaluation"` 的评标阶段条件，例如评委纠错后的报价、其他投标人价格、基准价及最终价格分；评审仍须登记原因和当前报价正文引用。它不会生成未知价格或预测得分，也不会产生要求补写竞争对手数据的整改任务。

`binding_ready` 只表示当前来源、正文引用与条件清单的机械绑定有效；已确认的评分失分仍显示警告。该字段不能替代核心评审的 `formal_release_ready`。原文条件必须属于对应04评分叶子的已登记引用范围和原文短句；共同事实按登记的窄引用核对数字，不用整章碰巧出现的同值自证。

当前编标规程中，`phase=evaluation` 条件只允许 `deferred` 或尚未复核的 `unknown`；不能改标为 `satisfied`、`partial` 或 `missing`。真实评标数据的登记与认证不在该编标检查器范围内。缺少本方有效报价仍由单独的报价输入条件阻塞或警告，不被延后外部数据条件掩盖。
