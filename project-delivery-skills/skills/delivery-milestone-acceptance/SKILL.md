---
name: delivery-milestone-acceptance
description: 按合同与有效变更组织阶段交付和里程碑验收，精确绑定交付物、证据、确认范围与遗留项。
---

# 里程碑与验收

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为合同/变更义务、Master Plan 里程碑、需求/蓝图/版本、测试或交付证据和确认人授权；输出里程碑确认、验收包、交付清单、遗留项和付款触发条件核对。

## 处理

逐里程碑列 scope、criteria、deliverable_refs、需求/流程/页面/字段/权限/接口/验收场景覆盖、证据版本/hash、检查结果和 open_items。客户确认绑定精确 target、版本、范围、actor、role、date、channel、evidence_refs 与 origin；内部通过、客户审阅、有条件确认、全部确认、付款条件、开票和到账分开记录。

效果图、测试通过、文件存在或内部审核不能替代实际验收。条件确认保留未决范围和责任/期限，不升级为全部接受。实际签署/发送需要授权与结果，不由工具推断。付款触发条件只核对证据，不代替财务审批。

## 主责与完成

确认/验收主账由本 Skill 维护；需求、蓝图、测试和交付物由各自主账维护。完成要求每个标准有证据和结果，未完成项有责任人，确认人有角色依据，实际文件已读回。未知/缺证据时保持 blocked/conditional。`ready` 不是客户签署、验收通过或付款到账。

## 模板

使用 `../delivery-orchestrator/assets/templates/milestone-acceptance.md`、`deliverables.csv`、`actions.csv` 和 `template-field-guide.md`。

需要形成可评审文件时，使用总控的 `scripts/export_core_documents.py` 导出里程碑验收包。导出默认是 discussion draft，逐项保留交付物版本/hash、证据与确认来源；登记状态不等于客户签署、验收或付款触发。
