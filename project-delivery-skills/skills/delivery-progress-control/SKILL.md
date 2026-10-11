---
name: delivery-progress-control
description: 基于计划基线、实际交付、剩余工作和依赖更新进度预测，分析偏差并提出可执行纠偏选项。
---

# 进度控制

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为 Master Plan 版本、工作包完成证据、实际日期、剩余工作、工时/资源和风险问题；输出进度台账、里程碑预测、偏差分析和纠偏建议。

## 处理

逐工作包对照原始/当前批准基线、最新预测和实际，引用完成规则与证据；区分未开始、进行中、阻塞、已完成。预测必须说明统计截止日、估算依据、依赖和不确定性。工时消耗不等于完成度，负责人自报百分比不能替代交付证据。仅在依赖、工期、日历可靠时计算关键路径，否则输出待核链路。

延期分析需列受影响里程碑、依赖、客户配合、风险/变更和选项（顺序、资源、批次、范围或日期）。纠偏决策回写计划/变更主账，不在周报中悄悄改基线。

## 主责与完成

本 Skill 维护进度视图和预测，不拥有 Master Plan、工时或成本主账。完成要求事实来源可回读、预测和基线分开、未知显式保留。`ready` 不是计划批准、工作包完成或里程碑验收。

## 模板

使用 `../delivery-orchestrator/assets/templates/progress-control.md`、`master-plan.csv`、`milestones.csv`（如项目已有）和 `template-field-guide.md`。
