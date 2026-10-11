---
name: delivery-business-blueprint
description: 组织现状与目标业务流程、角色、系统边界、规则、例外和覆盖评审，并形成带模块确认范围的业务蓝图。
---

# 业务蓝图

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为有效需求、调研证据、会议决策、合同边界和系统清单；输出业务蓝图、流程/覆盖矩阵、评审问题与确认包。

## 处理

逐流程描述入口/出口、触发、角色、正常/异常分支、审批、单据和报表，明确现状问题、目标流程、系统边界、数据对象、接口、客户配合和排除项。每条关键需求必须有流程落点和验收条件。业务蓝图可引用实施附件，但不能把效果图或讨论稿当功能实现。

蓝图确认包要区分讨论稿、内部通过、客户审阅、有条件确认和全部确认，并绑定精确文档 ID/revision/hash、适用模块、`processes`、`pages`、`fields`、`permissions`、`interfaces`、`data`、`acceptance` 七项范围、确认人/角色/日期/渠道和 open_items。模块确认可以分批，未确认模块保持独立；条件确认只能推进不受未决项影响的工作。

## 主责与完成

第一批由本 Skill 维护业务蓝图及最小实施附件：页面/交互、字段类型长度精度/必填默认/校验/显隐读写权限、接口双方与字段映射/认证错误处理，以及可测试验收场景。复用现有工程和原型能力提供细节，明确未验证范围，不等待尚未安装的后续技能。专项架构、完整接口工程等超出本次材料时保留缺口；后续专业技能安装后再显式移交对象主责，不能并建第二套台账。

完成要求每条需求、流程、页面字段/权限、接口和验收场景有映射，评审意见已回读；关键人/规则/边界未知则列阻塞。`ready` 不等于内部批准、客户确认或开发授权。

## 模板

使用 `../delivery-orchestrator/assets/templates/business-blueprint.md`、`implementation-blueprint.md`、`requirements.csv`、`fields.csv`、`interfaces.csv` 和 `template-field-guide.md`。
