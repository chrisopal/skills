---
name: delivery-resource-timesheets
description: 管理项目人员容量、分配、实际工时和审核差异，区分内部与外包口径并保留剩余工作估算。
---

# 资源与工时

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为 Master Plan/WBS、人员角色与可用日历、外包安排、工时记录和内部费率版本；输出资源计划、工时台账、审核差异和剩余工作输入。

## 处理

第二批在 timesheets 同一主账增加 capacities、allocations 和 remaining_work，按人/周期核对可用容量与分配并提示超负荷。逐项剩余工时×内部费率推导剩余人工时，remaining_labor 必须为空，防止与旧汇总叠加。外包剩余工作只用于负荷与估计，成本仍由同工作包外包事项提供。

每条工时关联稳定记录 ID、人员、日期、项目/工作包、活动、正常/加班、小时、说明/证据、资源类型、填报/审核状态和费率版本。人员容量分开记录可用、分配、请假/驻场/替补；并行分配不能直接改变工期。外包工时可用于进度和结算核验，不自动加入内部人工成本。

拒绝同一时间重复计入多个工作包；申请、审核、拒绝和修订保留历史。未填报不是零，未知小时/费率保留缺口；内部费率仅 internal visibility。工时事实与完成度分开，交由进度 Skill 结合完成规则判断。

## 主责与完成

资源/工时主账由本 Skill 维护，计划读取容量，成本读取已审核/暂估工时。完成要求来源周期、人员口径、工作包关联和审核差异可回读；缺记录、重复、费率版本或外包边界时 blocked。`ready` 不是工时审核完成、付款批准或项目接受。

## 模板

使用 `../delivery-orchestrator/assets/templates/resource-timesheet.md`、`timesheets.csv`、`roles.csv`、`resources-capacity.csv` 和 `template-field-guide.md`。
