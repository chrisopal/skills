# Opportunity Stage Management Design

## Context

`opportunity-analysis-skill` already extracts an opportunity `stage`, stores it in SQLite, and renders it in the detail page and kanban board. The current stage behavior is lightweight: a few keyword rules infer one stage string, and the kanban groups cards by a fixed stage list.

The next improvement is not a full CRM workflow engine. The skill needs a clear, business-readable stage definition from first lead to final win or loss, a more explainable current-stage judgment, and a detail-page visualization that makes the current stage obvious.

## Goals

- Define a standard enterprise-service opportunity stage model inside the skill.
- Identify where an opportunity becomes a confirmed opportunity, not just a lead.
- Output the current stage, stage reason, stage confidence, and confirmed-opportunity state.
- Show the stage model clearly in the opportunity detail page.
- Refresh the top opportunity metrics for score, win probability, and risk level so they match the new stage section visually.
- Keep the implementation portable, static HTML based, and compatible with the existing SQLite records.

## Non-Goals

- Do not implement stage history, stage duration, manual stage movement, or rollback.
- Do not implement strict stage gate validation or block progression.
- Do not add a next-step rules engine.
- Do not add JavaScript, a frontend framework, or an interactive CRM UI.
- Do not break existing `stage` queries or stored opportunity rows.

## Stage Model

The standard stages are:

1. `lead_identified` / 线索识别
2. `customer_contacted` / 客户接触
3. `needs_discovery` / 需求澄清
4. `opportunity_confirmed` / 商机确认
5. `solution_cocreation` / 方案共创
6. `budget_project_confirmed` / 预算/立项确认
7. `proposal_bidding` / 报价/投标
8. `commercial_negotiation` / 商务谈判
9. `won` / 赢单
10. `lost` / 丢单

`商机确认` is the business milestone between early discovery and a real opportunity worth presales or solution resources.

An opportunity is considered confirmed when the current stage is `opportunity_confirmed` or any later stage, including terminal `won` or `lost`. A lost deal can still be a confirmed opportunity; it simply ended unsuccessfully. Budget confirmation is not required for opportunity confirmation; budget belongs to the later `预算/立项确认` stage.

Each stage definition should include:

- `stage_id`
- `name`
- `order`
- `description`
- `signals`
- `is_terminal`
- `is_opportunity_confirmed`

## Stage Judgment

Stage judgment should remain deterministic and explainable. It should scan source text and extracted fields for stage signals, then choose the latest matching stage by priority.

Judgment priority runs from terminal or late-stage signals backward:

- `won`: 中标、已签约、合同已签、PO、成交。
- `lost`: 未中标、客户选择其他供应商、项目暂停、项目取消、预算取消。
- `commercial_negotiation`: 合同条款、价格谈判、付款方式、交付边界、法务、采购谈判。
- `proposal_bidding`: 报价、投标、招标、比选、询价、RFP。
- `budget_project_confirmed`: 预算已批、技改预算、立项、采购计划、审批流程、明确时间窗口。
- `solution_cocreation`: 方案交流、技术交流、演示、接口讨论、POC、设备选型、范围讨论。
- `opportunity_confirmed`: 明确客户对象、明确业务问题或核心需求、客户侧负责人或推进人、继续推进意愿。
- `needs_discovery`: 有需求方向和痛点，但负责人、推进意愿或资源投入还不够明确。
- `customer_contacted`: 有客户联系人或发生初步沟通，但需求模糊。
- `lead_identified`: 只有客户、行业、潜在方向或零散线索。

The output should include:

- `stage_id`
- `stage`
- `stage_reason`
- `stage_confidence`
- `stage_signal_hits`
- `opportunity_confirmed`

The existing `stage` field remains the Chinese stage name so old query and display behavior continues to work. Add nullable storage columns for `stage_id`, `stage_confidence`, `stage_signal_hits`, and `opportunity_confirmed`; older rows without these fields must render through a fallback derived from the existing `stage` value.

## Detail Page UX

Add a `商机阶段` module directly below the opportunity summary card and above the commercial assessment.

The module contains:

- A horizontal stage progress bar with the full stage path.
- Completed stages in muted green.
- Current stage highlighted with the strongest visual weight.
- Future stages in light gray.
- `商机确认` marked as a key milestone.
- A status badge: `已确认商机` or `尚未确认商机`.

Below the stage path, show concise judgment facts:

- 当前阶段
- 判断依据
- 阶段可信度
- 商机状态

For the Huachen example, the likely current stage is `方案共创` unless budget approval is explicit enough to advance it to `预算/立项确认`. The stage reason should cite signals such as 方案确认、技术交流、检测点位讨论、MES 对接、预算区间确认.

## Top Metrics UX

Refresh the top opportunity summary metrics to match the stage section:

- `商机评分`: large numeric score with a short score-level note.
- `赢单概率`: percentage value with a confidence or assessment note.
- `风险等级`: Chinese risk label `低` / `中` / `高` with a compact risk badge.

Use the existing visual direction: white background, dark green primary emphasis, light gray separators, and orange only for warning or uncertainty. The metrics should read as one summary strip instead of scattered text tags.

## Kanban UX

Update the kanban stage columns to the new stage model:

- 线索识别
- 客户接触
- 需求澄清
- 商机确认
- 方案共创
- 预算/立项确认
- 报价/投标
- 商务谈判
- 赢单
- 丢单

Each card should show whether the opportunity is confirmed:

- `已确认商机`
- `未确认商机`

The board summary should include confirmed opportunity count. The kanban remains a static rendered view; it does not support drag-and-drop or manual stage changes in this scope.

## Data Flow

1. `opportunity_analysis` evaluates source text and extracted account/contact/opportunity fields.
2. The stage model maps signal hits into a stage result.
3. The opportunity payload carries both legacy `stage` and new stage metadata.
4. SQLite persists legacy fields plus nullable stage metadata columns.
5. The renderer consumes the stage metadata to build the detail stage module and the kanban stage columns.
6. Query filters by `stage` continue to use the Chinese stage name.

## Error Handling

- If no stage signals are found, default to `线索识别` with low confidence.
- If both won and lost signals appear, choose the latest explicit terminal signal when evidence order is available; otherwise mark confidence low and include both signals in the reason.
- If new metadata is missing in an old stored row, render a fallback from the existing `stage` string.
- If a stored stage is unknown, show it as current in an `未归类阶段` fallback rather than failing rendering.

## Testing

Validation should cover:

- Stage model contains all standard stages in order.
- Huachen-like input renders the stage module and marks the opportunity as confirmed.
- Existing `stage` string remains present in output and query results.
- Kanban renders the new stage columns.
- Detail page renders the refreshed score, win probability, and risk metrics.
- Old detail data without `stage_id` still renders through fallback behavior.
- Template safety remains script-free.

## Rollout

Implement this as a small extension of the existing closed-loop skill:

1. Add the stage model and judgment helper.
2. Extend opportunity output and storage compatibility.
3. Update detail and kanban renderers.
4. Update docs, schemas, examples, and validator.
5. Regenerate the Huachen detail HTML and verify desktop/mobile rendering.
