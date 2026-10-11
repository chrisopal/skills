---
name: delivery-discovery-planning
description: 设计客户调研计划、访谈提纲、资料清单与底稿，确保每场有目标、双方责任、来源覆盖和可交付结果。
---

# 客户调研计划

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入是交接范围、目标流程、关键人、已知需求/风险和可用来源；输出调研计划、访谈提纲、客户准备清单和可复用底稿。

## 处理

为每场登记调研 ID、主题、时间/方式、客户部门与角色、我方主持/记录/专业人员、目标问题、关联合同/需求、方法、预计输出和状态。问题覆盖现状流程、目标场景、业务规则、异常、数据/报表、权限、接口、非功能约束与验收；材料清单标明制度、表单、样本、系统演示、接口文档及提供责任人。

把“需要客户确认的事实”“参会者建议”“我方假设”分栏。关键人缺席、未排期、材料未交或录音未转录显式标记，不能以会议邀请或文件名证明调研已完成。底稿引用精确 source/evidence 版本和定位。

## 主责与完成

调研计划和底稿模板由本 Skill 维护；会议实际内容由 `delivery-meeting-records` 维护，需求和蓝图只消费已读证据。完成要求每场有目标、责任、输出和覆盖状态；未知事项有下一动作。`ready` 不是访谈完成、客户确认或需求基线。

## 模板

使用 `../delivery-orchestrator/assets/templates/discovery-plan.md`、`meeting-record.md` 和 `actions.csv`。
