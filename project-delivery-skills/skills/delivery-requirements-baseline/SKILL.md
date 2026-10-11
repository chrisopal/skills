---
name: delivery-requirements-baseline
description: 从合同、证据和会议材料提炼原子需求、规则、优先级、来源与验收标准，形成可复核的需求基线。
---

# 需求基线

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为合同义务、已覆盖的 evidence、纪要/调研底稿、既有需求版本和客户约束；输出需求规格、需求台账、覆盖矩阵、澄清问题和确认/变更记录。

## 处理

每条需求使用稳定 ID，保持原文 statement、source_refs/locator、角色、范围、优先级、业务规则、依赖、排除项、验收条件和状态。区分合同要求、客户期望、建议、推断与缺失；不同角色冲突并列记录，不能择一抹平。需求必须可映射至流程/页面/字段/权限/接口/验收场景，映射不完整就列缺口。

基线前的新需求、修改和删除进入变更评估；不直接覆盖已确认版本。确认记录绑定精确 revision/hash、范围、确认人角色、日期、渠道和遗留意见。`ready` 只表示整理可用，绝不等于客户确认或允许开发。

## 主责与完成

需求主账由本 Skill 维护；蓝图消费需求 ID 并提交候选映射，变更 Skill 协调修订。完成要求来源覆盖记录可回读、原子条目可验收、冲突/缺口/假设有责任人和下一步。原件未读、定位缺失或验收未知时保留 blocked。

## 模板

使用 `../delivery-orchestrator/assets/templates/requirements-baseline.md`、`requirements.csv`、`actions.csv` 和 `template-field-guide.md`。
