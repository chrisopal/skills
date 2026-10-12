# 商机共享运行契约

共享运行入口为本 Skill 的 scripts/run.py；实际实现位于兄弟 opportunity-analysis-skill/src/opportunity_skill。七个 Skill 安装为同级目录。所有业务数据使用项目 DB 和输出目录，不写入技能源码。

## 权威与兼容

- opportunity_id 为稳定身份；同客户不同项目分别建商机。更新已有商机必须传 opportunity_id 和当前 expected_revision；新项目可引用已有 account_id。
- lifecycle.current_stage_id 为正式阶段；suggested_stage_id 为材料推断。旧 opportunity.stage/stage_id 保留分析建议语义，不能当正式阶段。
- legacy stage 过滤保留兼容用途，正式阶段查询使用 current_stage。已有记录没有可靠迁移证据时，不补造历史或已确认事实。
- owner 为商机负责人；分析输入明确指定 owner 时保存，省略时保留旧值。转派使用 set_owner 并记录 actor、reason、时间及前后负责人。
- HTML/Markdown 是派生视图。恢复和完成时回读 DB、文件版本和实际成果。

## 分析增量

输入沿用 evidence_list 或 materials。原始音视频、图片和文档先由宿主解析成文本/Evidence，保留原件与定位。示例：

```json
{
  "opportunity_id": "从既有结果取得的ID",
  "request_id": "一次输入批次的唯一ID",
  "expected_revision": 0,
  "owner": "销售负责人",
  "materials": [{"type": "meeting_note", "name": "跟进记录", "content": "客户希望下周讨论方案，尚未决定是否报价。"}]
}
```

expected_revision 必须换成回读值，不能照抄0。新材料用于增量保存及建议分析；材料冲突、历史描述、条件和否定不能直接成为阶段推进依据。评分是启发式参考，不是校准后的成交概率，不作为合同签署门槛。

商务确认回答含 dimension_id、rating、answer_text、answered_by。增量分析保留原回答，新回答按 dimension_id 覆盖；当前风险、决策链与建议行动为重新计算的当前投影，实际行动结果与历史单独保存在 lifecycle。已回复和事实已确认分别记录，未知回答不消除事实缺口。确认预算/范围/客户意愿等业务事实，仍须提交下面的 confirm_fact 并引用实际证据。

## 业务变更

```json
{
  "request_id": "REQ-001",
  "opportunity_id": "从既有结果取得的ID",
  "expected_revision": 0,
  "actor": "实际业务确认者",
  "operations": [
    {"type": "confirm_fact", "fact_id": "need_confirmed", "value": true, "evidence": ["从当前商机取得的证据ID"]},
    {"type": "add_action", "action_id": "ACT-001", "title": "组织方案评审", "owner": "售前负责人", "due_date": "2026-10-20"}
  ]
}
```

操作通过 manage --input CHANGE.json --db DB 提交。请求 ID 用于重试幂等；原请求内容改变时使用新 ID。expected_revision 防止覆盖较新的人工或 Agent 结果。一次请求要么全部成功，要么不改变正式状态。

| type | 主要字段 | 结果 |
|---|---|---|
| confirm_fact | fact_id、value、evidence；报价授权另含 artifact_id | 证据支持的事实修订；否定事实也保留，不能用未知满足阶段条件 |
| set_owner | owner、reason | 保存商机负责人和实际转派历史；内部安排不要求客户证据 |
| add_action | action_id（可选）、title、owner、due_date | 建立可执行行动 |
| complete_action | action_id、result、evidence | 保存真实完成结果 |
| register_artifact | artifact_id（可选）、kind、version、file_path、dependencies、evidence、metadata | 登记实际文件、版本和摘要 |
| record_review | review_id、title、requirement_ids、artifact_id、owner、due_date、blocking、evidence | 登记当前方案的客户意见与整改责任 |
| resolve_review | review_id、artifact_id、resolution、evidence | 绑定当前方案和关闭依据，保留处理历史 |
| reopen_review | review_id、reason、evidence | 重新打开意见，不删除历史关闭记录 |
| record_contract | contract_id（可选）、artifact_id、signing_date、parties、amount、currency、signature_facts、evidence | 对应合同版本的实际签署业务记录 |
| transition | to_stage、reason、evidence | 校验条件后记录真实阶段迁移 |
| set_status | status、reason、evidence | 暂停、恢复、丢单或取消，保留原因与历史 |

evidence 引用必须存在并属于同一商机；不能虚构ID。actor 记录业务来源，不认证身份。运行层无法证明引用的材料在语义上支持结论，Agent/负责人须实际核验。

## 阶段与条件

| to_stage | 正式推进所需条件 |
|---|---|
| customer_contacted | contact_established 事实 |
| needs_discovery | need_confirmed 事实 |
| opportunity_confirmed | need_confirmed、requirement_owner、continue_intent 事实 |
| solution_cocreation | solution_scope 事实和有效 solution 产物 |
| budget_project_confirmed | budget_confirmed 事实 |
| proposal_bidding | quote_authorized 事实和有效 quote 产物 |
| commercial_negotiation | 有效 negotiation 产物 |
| contract_signing | 有效 contract 产物 |
| won | 当前有效合同产物及完整签署记录 |

首阶段为 lead_identified。允许依据真实资料从等价现有成果开始；跳过的步骤不产生虚假完成记录。预算/立项可作为并行里程碑，客户路径不要求统一按序经过全部阶段。回退/更正写明原因和证据，不覆盖历史。失效商业成果允许有证据地退回较早的非商业阶段整改；回退只核验目标条件，后续商务推进仍须重新核验当前依据、授权和阻塞意见。active、paused、lost、cancelled 为业务状态，不能把暂停等同丢单。

quote_authorized=true 必须绑定 artifact_id 指向当前有效 quote 文件；运行层记录对应摘要。报价修订或文件变化后重新确认授权，不能把旧版批准自动移到新版。谈判、合同和实际签署登记必须沿依赖指向该授权报价；多份仍有效报价并存时，批准A不能作为B的批准。阶段历史保存实际使用的成果ID及摘要，避免其他有效候选掩盖依据失效。布尔条件只接受 true/false 或明确未知；requirement_owner、solution_scope 使用真实非空文本。旧事实被否定时保留版本和阻塞提示。

恢复丢单/取消使用有理由和证据的 set_status active，保留旧状态历史。已签单后可以转派负责人、登记交接文件与行动；若确需更正签署流程，显式恢复 active 会记录 won→contract_signing 的实际更正事件，不能静默抹除旧签单记录。

## 成果与签署

kind 为 solution / quote / negotiation / contract / handoff。file_path 指向可读的实际本地文件；version 为正整数，按运行层规则递增。dependencies 保存明确的依据版本绑定；metadata 保存来源、使用范围、税口径、有效期和授权等业务信息，不把内部候选稿当正式响应。

dependencies 为 `[{"artifact_id":"同一商机的上游成果ID","sha256":"回读的64位文件摘要"}]`。新 quote 必须依赖当前有效 solution；negotiation 依赖 quote；contract 依赖 quote，如本商机存在谈判成果也必须绑定有效 negotiation；有合同的 handoff 依赖当前 contract。登记顺序为方案→报价→谈判→合同→交接，同一请求可逐项登记。直接采购可以没有谈判成果，不能补造谈判。

依据版本不得指向已被替代、文件变化、未绑定或其上游失效的成果。报价先修订，再登记依据该报价的谈判纪要，最后重新确认报价授权。上游变化后下游派生 `dependency_invalid`；旧成果缺依赖显示 `unbound`，仍保留历史，但不能作为新的阶段推进依据。整改须以新版本重新登记和复核，不能修改旧记录以假装原批准仍有效。全局 `needs_review` 也包括非当前阶段的失效成果；正式阶段与已签署历史不会自动回退。

运行层保存文件 SHA-256；文件改动/丢失须在回读和阶段推进时显示失效。新范围或版本要重新核验受影响的事实和成果；旧签署记录不能自动迁移到新合同版本。

record_contract 的 signing_date 使用 YYYY-MM-DD；parties 至少包含双方真实主体；amount 是非负数（零金额项目须明确业务依据）；currency 使用真实币种。signature_facts 中 customer_signed 与 supplier_signed 必须是布尔 true，且有经核验的实际依据。合同编号、生效条件、税口径等在合同 metadata 保留，不能以签单记录替代法律审核。

签署文件存在、摘要一致和字段完整只证明运行层可核验的条件；不认证签署人、不判断签字真实与法律效力。中标、PO 模板、口头承诺不能提交为已签单。回款、收入、交付和客户验收另行记录。

## 客户评审闭环

每条意见使用稳定 review_id，明确 requirement_ids（需求编号）、被评审方案 artifact_id、title（客户意见）、owner、due_date（YYYY-MM-DD）、blocking（布尔）和当前商机 evidence。record_review 将方案摘要与来源同时保存。

resolve_review 必须提交与被评审方案相同 document_id 的当前有效版本、具体 resolution 和实际关闭 evidence；关闭只证明所登记范围的确认，演示通过不能扩大为生产验收。reopen_review 保留原关闭记录和新原因。已关闭方案被替代或文件变化后，意见仍保留 resolved 历史状态，但 verification_status 变为 needs_review，需用当前方案重新复核关闭。非阻塞意见不会阻止商业阶段推进，但保留待办和核验提示；阻塞意见未解决/未复核时，报价、谈判、签约、赢单推进均被拒绝。

恢复时回读 reviews 的 status、verification_status、closure、history，不能只凭“已关闭”文案跳过核验。业务客户认可的真实性仍需负责人核对证据，运行层不代客户批准。

## 失败与回读

冲突版本先读回新状态再整理差异，不能盲目覆盖。重复 manage 请求保留原变更回执 revision，lifecycle 和 current_revision 回读当前状态及文件有效性；不会再次执行操作。分析重试保留原保存回执并重新回读现状。改变请求内容不能借同一 ID 重放。证据错属、文件失效、缺少条件或请求非法时保留原正式状态。失败修订用新 request_id 和最新 revision。

最终回读 lifecycle 的 revision、current_stage_id、suggested_stage_id、status、facts、history、actions、reviews、artifacts、contracts，以及未解决阻塞。已完成行动、阶段完成、签单和客户验收分别汇报。
