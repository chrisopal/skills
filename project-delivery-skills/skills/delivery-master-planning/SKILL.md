---
name: delivery-master-planning
description: 将合同范围、需求、资源和依赖分解为可追踪的 WBS、Master Plan、里程碑与近期滚动计划。
---

# Master Plan 与里程碑计划

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为合同义务、需求/蓝图版本、资源约束、工作日历、外部依赖和授权日期；输出计划主账、WBS、里程碑、资源需求和计划版本。

## 处理

按交付物/工作包拆解任务，绑定需求、负责人、参与方、完成规则、前置依赖、日历、基线起止、当前计划、实际起止、剩余工作和证据。原始批准基线、当前批准基线、最新预测和实际日期并列保存；重排产生新修订，不覆盖原基线。日期未知保持待定，不能用今天或零填充。

工作日历、工期、人时和并行关系分开；多人投入不自动缩短工期。只有依赖、工期和日历可靠时才计算关键链路，否则标为待核。计划变更需要关联变更/决策和授权，近期细化不能悄悄改合同里程碑。

## 主责与完成

计划主账由本 Skill 维护；进度 Skill 只读取并提出预测，资源/成本 Skill 维护事实台账。完成要求所有工作包有完成规则、责任、依赖和来源版本，里程碑有验收/交付物落点；缺输入显式登记。`ready` 不是执行完成、内部批准或客户确认。

## 模板

使用 `../delivery-orchestrator/assets/templates/master-plan.csv`、`milestone-acceptance.md` 和 `template-field-guide.md`。

需要形成可评审文件时，使用总控的 `scripts/export_core_documents.py` 导出 Master Plan 与 WBS。导出并列显示基线、当前计划、实际日期、剩余工作和预测；缺少日历或工期依据时保持待确认。
