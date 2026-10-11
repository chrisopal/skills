# 项目与成果交接契约

## 文件与权威

运行工具仅需要 Python 3 标准库。项目内保存原件快照、work索引、带修订的artifacts、PPT交接与deliverables。以JSON为事实版本，Markdown是派生审阅视图。不得手工改已登记成果；提交同artifact_id的递增整数revision。运行 `runtime.py --help` 和对应子命令 `--help` 查看精确参数。

源文件用 `source PROJECT FILE --id SRC-001` 登记，命令计算快照hash。提取记录不是来源本身：后续证据应同时保留原件ID与定位。图片是否看过、PDF是否渲染过必须由实际执行者记录。

## 成果 envelope

```json
{
  "project_id": "PROJECT-001",
  "artifact_id": "REQ",
  "kind": "requirements",
  "revision": 1,
  "inputs": [{"artifact_id": "EV", "sha256": "从register返回值复制完整hash"}],
  "status": "ready",
  "data": {"items": []}
}
```

示例hash是说明，不是可执行值。每次输入必须引用本项目索引中真实版本的完整SHA-256。源和中间成果都属于依赖；相同hash不意味着可以跨项目复用。跨项目复用先作为本项目授权输入重新登记，保留原主体及使用范围。

`status`由作者申报draft/ready/blocked；工具另根据实际文件与依赖派生stale。ready只表示成果可供后续使用。确认状态保存在业务记录中，不因ready或review pass而变化。

## 各 kind 的 data 约定

运行工具做关键结构和依赖检查；以下业务字段由对应技能编写、审核技能逐项核验。不能因为JSON可解析就省略业务信息。

| kind | data内容 |
|---|---|
| brief | customer, supplier, audience, purpose, desired_decisions, page_budget, duration_minutes, authorization, assumptions |
| evidence | items: id(EV), source_id, locator, quote, evidence_type, read_status；reading_coverage: source_id, status, unread_scope, visual_review |
| requirements | items: id(REQ), statement, original_quote, evidence_ids, type, stakeholder, conditions, priority及basis, success_standard, conflicts, clarification_ids |
| clarification | items: id(Q), question, rationale, impact_ids, priority, respondent, requested_material, answer, answer_evidence_ids, status(open/answered/assumed), decision |
| storyline | nodes: id(NODE), parent_id, customer_question, claim, requirement_ids, evidence_ids, gaps；core_message, decision_request |
| materials | items: id(MAT), source_id, locator, evidence_ids, owner, product, version, capability_class, conditions, use_scope, match_status, reason, requirement_ids |
| solution | items: id(SOL), requirement_ids, response_mechanism, material_ids, evidence_ids, prerequisites, scope_in, scope_out, validation_method, unknowns；options, delivery_phases, value_method |
| outline | slides: slide_id, section, title, purpose, key_message, planned_content, requirement_ids, solution_ids, evidence_ids, material_ids, visual_type, duration_seconds；appendix |
| content | 见下节 |
| review | 见审核节 |
| delivery | 见PPT交接参考 |

evidence_type 使用 customer-statement/observed/inferred/proposed/unknown。客户说过不等于已经验证；“我们建议”不等于客户需求。

能力分类使用 standard/configuration/custom/third-party/roadmap/unsupported/unknown；适用性结论使用 verified/candidate/unusable。版本、主体或使用范围不明的资料不能标verified。

## 逐页内容包

data包含deck_id、purpose、audience、language、page_budget、duration_minutes、theme_profile、output_formats、story_arc、slides、appendix、citation_index、review_status及业务确认状态。所有实际使用的需求、方案、材料、大纲都在envelope.inputs中登记。每页artifact_ids必须位于这些精确hash绑定的直接或传递依赖中；不存在或未绑定的引用会被拒绝。evidence_ids等业务条目ID另由语义审核核对。

每页至少：

- slide_id（稳定且唯一）、section、title、key_message、supporting_points（真正上屏正文）、speaker_notes。
- requirement_ids、solution_ids、evidence_ids、material_ids、artifact_ids。引用为空时写清不适用理由，不能编造ID凑数。
- visual_type、diagram_spec/chart_spec（首版为经审核的纯文本关系/数据说明，不接任意嵌套对象）、layout_hint、经过授权的素材路径。
- visible_caveats（必须上屏）、locked_claims（术语、数字、产品版本、范围与条件不可改变）、review_status。

图的数据来源及单位明确；定性关系不得冒充测量数据。没有收益基线时给测量方法，不填百分比。每页完整实例见[内容包示例](../assets/content.example.json)。

## 审核记录

review的inputs精确绑定target；data必需mode(direction/content/delivery)、target_id、target_sha256、verdict(pass/conditional/fail/not_checked)、method、reviewer、findings、scope、unchecked。所有结论指向实际文件版本。

findings每项：finding_id、severity(blocking/major/minor)、status(open/closed)、object_ids、source、page、finding、impact、action、owner、resolution_evidence。关闭须说明复核的新证据；缺证据留open。影响关键范围、产品事实或可读性的错误定为blocking，不用总分抵消。

内容制作门槛：当前target和全部依赖有效，存在同hash的pass内容审核，method以independent-开头，标明实际独立Agent或人工审阅（例如independent-agent-source-review或independent-human-review）。machine-only和self-check不能冒充独立内容审核。conditional只支持明确范围的整改或候选讨论，不自动等同pass。

审核使用方必须核对执行身份与原始证据；CLI不认证reviewer字符串，也不判断一句话是否真的回应需求。独立审核记录可以留在envelope外部并绑定精确hash，避免“审核状态字段一更新就使被审核对象hash变化”。

## 变更与确认

任何源快照/成果/交付文件/渲染证据变更都要重新检查。status/validate以实际hash派生失效；下游必须重建输入引用并重新审核。每页ID不随简单改字变化；拆页/合页保留映射并更新内容包，不允许PPT阶段自行改变页数与承诺。

业务确认记录至少含status、actor、role、time、target_id、revision或sha256、scope、原始确认来源。没有实际证据保留unconfirmed。已授权的制作不反复询问，新增重大业务决定只澄清变化部分。
