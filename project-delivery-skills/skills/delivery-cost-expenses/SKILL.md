---
name: delivery-cost-expenses
description: 归集预算、人工、采购、外包、差旅和其他成本，提供不重复的发生、承诺与完工预测。
---

# 成本与费用

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为预算版本、已审核/暂估工时、采购/外包记录、差旅申请与凭证、付款条件和财务授权来源；输出预算、费用台账、成本预测、偏差和付款条件跟踪。

## 核算规则

区分 `estimate`/`committed`（剩余预计）和 `incurred`（已发生），记录币种、税口径、工作包、类别、金额、依据和 payment_status。申请、发生、报销、付款是同一成本事项的状态/证据，不得重复计成本；第一批采购使用单一汇总事项，不支持部分发生拆账；外包暂估转结算修订原 ID。travel_or_expense_ref、procurement_ref、external_ref 是同一逻辑成本号的别名，别名必须一致，同一关联号不得重复建行或跨版本换 ID。内部人工按审核工时×内部费率估计，未知费率/工时保留缺口；外包工时不自动加入内部人工。

完工预测=内部人工发生估计+其他已发生+剩余预计；差异=完工预测−预算。没有完整来源时标 `incomplete`，不能用零填平未知，也不能把付款状态推断为发生金额或收入。

## 主责与完成

成本主账由本 Skill 维护；报告只生成视图，财务系统维护正式记账。完成要求每项唯一、口径统一、来源和截止日可回读；重复关联、币种/税未知或财务授权缺失时保留阻塞。`ready` 不是财务审批、开票、到账或客户确认。

## 模板

使用 `../delivery-orchestrator/assets/templates/cost-expenses.md`、`costs.csv`、`timesheets.csv` 和 `template-field-guide.md`。个人费率和内部毛利不进入客户版。
