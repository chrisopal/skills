---
name: delivery-artifact-review
description: 在关键成果交付前复核范围、追溯、跨文档一致性、敏感信息、版本有效性和实际文件回读，形成整改与交付建议。
---

# 交付物审查

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为待审产物精确引用、目标交付范围、需求/蓝图/计划/确认/测试证据、客户模板与可见性规则；输出审查单、整改记录和版本化交付建议。

## 三层复核

分别执行结构检查（字段、格式、引用、哈希）、语义审查（需求覆盖、流程/页面/字段/权限/接口/验收一致性、承诺边界）和实际文件回读（打开、渲染、页码/表格/乱码/附件）。记录方法、读取范围、版本和未检查项；不能用结构通过代替语义正确，也不能用渲染成功代替客户接受。

审查 findings 使用稳定 ID、severity、status、resolution_evidence。核查 customer/internal visibility、内部财务和凭据泄露、来源漂移、候选版本是否混入有效基线。整改必须重新审查受影响范围；`ready`、内部 pass、客户审阅和 accepted 分开。

## 主责与完成

审查记录由本 Skill 维护，领域主账由对应 Skill 维护；本 Skill 不能代替业务授权、客户确认或变更应用。完成要求所有目标版本可回读、发现项有结论/证据、未检查项和交付模式明确。缺实际文件、引用、权限或渲染能力时报告限制并保留 conditional/fail。

## 模板

使用 `../delivery-orchestrator/assets/templates/artifact-review.md`、`deliverables.csv`、`changes.csv` 和 `template-field-guide.md`。
