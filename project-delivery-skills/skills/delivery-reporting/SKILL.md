---
name: delivery-reporting
description: 从项目主账生成按截止日可追溯的内部/客户周报、周会议程与管理摘要，区分事实、预测和待决项。
---

# 项目报告

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为指定统计期间、计划/进度、交付物、风险问题、变更、资源/成本和确认记录；输出客户版周报、内部版周报、周会议程/内容包和管理摘要。

## 处理

固定 `period` 与 `as_of`，从主账提取事实、预测、来源版本、覆盖缺口和待决项；不在报告里另建一套事实主账。客户版列总体判断依据、上周计划/实际、交付物及确认情况、里程碑偏差、本周/下周、风险、客户配合和需要决策的责任/期限。内部版在此基础上增加资源负荷、发生/预测成本、预算差异、变更损益、外包和应收条件风险。

草稿、未核实数据和预测必须显式标记；内部/客户 visibility 分开。报告生成或发送不等于客户确认，实际外发需要独立授权和结果记录。周会议程聚焦决策与阻塞，纪要行动回写行动主账，不复制状态。

## 主责与完成

报告是事实视图，由本 Skill 维护版本与引用；计划、成本、确认主账由对应 Skill 维护。完成要求截止日、来源、事实/预测边界和外发范围可回读；缺数据保留 unknown/coverage_gaps。`ready` 不是内部批准、实际发送或客户接受。

## 模板

使用 `../delivery-orchestrator/assets/templates/weekly-internal.md`、`weekly-customer.md`、`actions.csv` 和 `template-field-guide.md`。
