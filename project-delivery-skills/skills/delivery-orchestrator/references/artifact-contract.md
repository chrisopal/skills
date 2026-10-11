# 第一批项目产物与工具契约

版本 0.1.0。项目单写；Agent 负责业务语义，工具负责来源/版本/引用和计算检查。

## 运行入口

所有技能作为兄弟目录安装。运行工具与公共模板位于 `delivery-orchestrator`，其他技能通过 `../delivery-orchestrator/` 引用。CLI 为 `scripts/runtime.py`，各命令用 `--help` 查精确参数。

`init PROJECT --project-id ID --purpose internal|simulation`；`source PROJECT FILE --id ID`；`register PROJECT ARTIFACT_JSON`；`status PROJECT`；`validate PROJECT`；`activate PROJECT ARTIFACT_ID...`；`apply-change PROJECT CHANGE_ID`；`prepare-customer PROJECT --ids ID... --out DIR --mode discussion|confirmed`。

init 不覆盖已有项目。原件保存快照，source 创建 kind=source 的产物。register 保存不可覆写的修订；inputs 引用精确版本和 register 返回的 SHA-256。status/validate 都回读实际内容。

## Envelope

```json
{
  "project_id": "DEMO-001",
  "artifact_id": "REQ",
  "revision": 1,
  "kind": "requirements",
  "visibility": "customer",
  "status": "ready",
  "inputs": [{"artifact_id": "CONTRACT", "revision": 1, "sha256": "使用登记命令返回值"}],
  "data": {"items": []}
}
```

visibility 为 internal/customer，status 为 draft/ready/blocked。ready 仅表示作者认为可用，不表示审核、客户认可或外发授权。每次修订递增一，产物 ID 不变。源原件及历史产物保存 hash；不手改已登记文件。

## kind 与业务字段

| kind | data 内容 |
|---|---|
| source | 工具维护快照 path、sha256、原始 name；语义读取范围在 evidence 记录 |
| evidence | items: id、source_id、locator、content、read_status；unread_scope |
| contract | obligations: id、statement、source_id、locator、acceptance；scope_in、scope_out、customer_dependencies |
| kickoff | goals、roles、milestones、customer_actions、open_items |
| discovery | sessions: id、customer_role、date、topic、questions、customer_inputs、expected_outputs、owner、status |
| minutes | meeting_date、participants、decisions、actions、open_items；决定保留 source_refs |
| requirements | items: id、statement、source_refs、acceptance、priority；open_items |
| blueprint | processes、pages、fields、interfaces、acceptance_scenarios、coverage、open_items；每个对象有 id；coverage 每行有 requirement_id、design_ids |
| plan | work_packages: id、title、owner、baseline_start、baseline_finish、forecast_finish、dependencies、requirement_ids、completion_rule、status；milestones |
| timesheets | items: id、person、date、work_package_id、hours、rate（未知用 null）、resource_type(internal/outsourced)、status(submitted/approved)；remaining_labor 可为空/数值 |
| costs | currency、budget、items: id（稳定成本事项 ID）、category(travel/purchase/outsourcing/other)、work_package_id、state(estimate/committed/incurred)、amount、basis、payment_status；other_remaining 可为空/数值 |
| risks | items: id、type(risk/issue/quality)、title、owner、status(open/closed)、action、due、evidence_refs |
| change | state(proposed/approved/rejected)、reason、affected_ids、baseline_refs、replacements（精确产物引用）、decision_refs、impact |
| weekly | period、as_of、completed、next、milestones、risks、decisions_required、coverage_gaps；全部依据在 inputs |
| milestone | milestone_id、scope、deliverable_refs、criteria、open_items；客户确认另建 confirmation |
| confirmation | target（精确引用）、state(accepted/conditional/rejected)、actor、role、date、scope、evidence_refs、origin(actual/simulation)、open_items |
| review | targets（精确引用列表）、verdict(pass/conditional/fail)、reviewer、method、findings、unchecked、scope；每项 findings 含 id、severity、status、resolution_evidence |

来源定位和条目级引用由 Agent 审核；JSON 结构通过不证明语义正确。标准字段可附加本项目需要的字段；生成客户包仍须审查自然语言和附件，不依赖字段名过滤完成脱敏。

## 基线、变更与确认

activate 仅用于初始有效版本集合，已存在的有效对象修订必须经 change。批次按明确范围登记，不强制先补造完整阶段历史。客户确认与内部基线是两个状态，初始 activate 不制造客户批准。

apply-change 仅接受 approved、实际决策来源完整且与候选修订有映射的变更。先检查旧基线、受影响对象、全部候选版本和依赖；通过后一次更新有效版本集合并登记应用收据。失败旧集合保持不变，变更仍待应用。源的新版本可使依赖旧源的产物过期；候选需求/蓝图不自动替换有效基线。

确认/审核必须同时写 target(s) 和 inputs，绑定同一 SHA-256；evidence_refs 关联输入范围内的真实来源产物，scope 说明模块/条件。origin=simulation 只用于 purpose=simulation，不能用于真实项目的确认门槛；工具核对绑定，不认证 actor 身份。

同一版本尚有 ready 的 rejected/conditional 确认或 fail/conditional 审核时，不能通过另建 ID 的 accepted/pass 绕过。整改后修订原确认/审核记录，保留处理依据；旧目标版本的记录仅用于历史追溯。

实施蓝图确认范围至少说明流程、页面/字段/权限、接口/数据、验收场景。条件确认保留 open_items，不能当全部确认。进入开发前由 Agent 核实具体批次确认或已授权先行安排。

## 工时与成本

内部人工按工时×内部费率估计；未审核工时计暂估并提示，未知费率/工时保留缺口。外包工时用于进度/结算核验，不自动加入内部人工。外包暂估或实际以 costs 中同一 id 的一个当前记录表达，暂估转结算修订原事项，禁止另起 ID 重复增加。

costs 中 estimate/committed 属于剩余预计，incurred 属于已发生；payment_status 不改变发生金额。同一逻辑事项保留稳定 id，修订同一行。travel_or_expense_ref、procurement_ref、external_ref 是同一个逻辑成本关联号的别名；同一行多个别名须一致，不同事项不得复用同一关联号，跨版本也不能换 id 重记、改变/删除关联号或移除已有行；作废/纠错保留原行，以有依据的零金额修订表达。第一批暂不支持同一采购的部分发生拆账，须使用一个汇总事项并明确状态/估计依据，避免重叠。remaining_labor 与 other_remaining 仅填不在已有事项里的剩余估计。

完工预测=内部人工发生估计+其他已发生+剩余预计；差异=完工预测−预算。币种、税和成本范围需统一；未知项存在时结果标注 incomplete，不冒充完整财务数据。显式 evidence_status=incomplete_business_evidence 会令 complete=false；外包工时没有同工作包的外包估计/结算项也保留缺口。complete 仅表示可检测字段与已声明缺口状态，不能认证发票、工时或审批真实性，仍需独立业务审核。

人工/费用发生读取最新有效内容的台账，不能被冻结在旧预算快照。若 costs 已登记批准基线，预算比较始终使用该基线预算；最新台账提出不同预算但未完成变更应用时，保留旧预算并提示差异。费用发生和付款状态更新无需伪造范围变更，预算变更才应进入批准与应用流程。

## 客户交付与审阅

prepare-customer 只准备本地包，不发送。只接受白名单业务 kind 与 visibility=customer 的明确选择；不复制来源、内部费用或整个依赖目录。每项需绑定当前有效的 pass 审核，confirmed 模式另需同版本 accepted 客户确认；讨论模式标注讨论稿。模拟项目的每个输出明确标注模拟。

审阅 API：`runtime.snapshot(project)` 返回 `project_id`、`purpose`、`artifacts`（当前候选，每项含 artifact_id/revision/kind/visibility/status/health/path/data）、`effective`（ID→精确引用）、`cost_summary`、`alerts`（字符串）、`gates`（blueprint/milestone 等，各含 ready/reasons）。该 API 为内部视图；对客审阅工具必须独立过滤内部对象与成本。

Office 模板导出入口 `scripts/export_templates.py --out DIR`；只读审阅 `scripts/render_review.py PROJECT --out FILE --view internal|customer`。这些脚本使用现有运行库；无 Office 库时保留 Markdown/CSV 模板并明确导出缺口。

## 项目归档目录

init 生成设计约定的阶段目录：01-contract-handover、02-initiation、03-plan、04-discovery、05-requirements-blueprint、06-design、07-development-integration、08-quality-uat、09-go-live-handover、10-project-control、11-milestone-acceptance、12-closure-warranty，以及 internal-finance、customer-deliverables、archive。后续阶段仅预留目录，不能据此宣称技能或工作完成。

Agent 将当前任务的 Markdown/Word/Excel、原型与已审核成果放入相应阶段目录，登记真实文件来源/位置和版本；大代码库/制品保留专业仓库引用。不可变原件快照只存 00-control/sources，各阶段引用同一版本。internal-finance 包含人员费率/成本，目录名不替代真实访问控制；对客交付从明确白名单另行准备，禁止压缩整个根目录。
