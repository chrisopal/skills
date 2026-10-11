---
name: delivery-change-control
description: 评估范围、设计、进度、成本与验收变化，登记授权决策，并协调各主账完整应用后更新有效版本集合。
---

# 变更控制

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为有效基线、变更申请、来源/决策证据、受影响需求/蓝图/计划/资源/成本/验收和候选修订；输出变更记录、影响分析、决策和应用收据。

## 处理

登记稳定 change ID、原因、申请人、范围、影响对象、baseline_refs、方案、范围/进度/成本/质量/风险/合同影响、依赖和待决问题。区分 proposed、approved、rejected 与“已批准、待应用”；批准本身不改变有效基线。候选版本必须精确映射受影响对象，不涉及对象不被改写。

应用顺序：回读实际决策来源 → 领域 Skill 写出候选修订 → 更新受影响计划/资源/预算/验收映射 → 交付审查回读全部候选及依赖 → 总控一次激活并登记应用收据。任何领域写入失败都保留旧有效集合，记录已写/待写对象和恢复点；不得部分激活或把未批准项混入基线。重复应用按 change/revision 幂等检查。

## 主责与完成

变更决策主账由本 Skill 维护；各领域维护各自对象主账。完成要求实际决策、影响依据、候选映射、完整应用和复核证据均可回读。授权、范围、版本、依赖或身份不明时保持待决。`ready` 不是批准、生效、开发授权或客户接受。

## 模板

使用 `../delivery-orchestrator/assets/templates/change-request.md`、`changes.csv`、`actions.csv` 和 `template-field-guide.md`。
