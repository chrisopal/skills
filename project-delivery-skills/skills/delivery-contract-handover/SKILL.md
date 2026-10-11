---
name: delivery-contract-handover
description: 从售前和合同材料提取交付义务、范围边界、验收付款质保、客户配合与分歧，形成可执行的交接包。
---

# 合同与售前交接

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入包括已登记的合同、技术协议、报价/方案承诺和来源证据；输出为合同义务矩阵、交接清单和范围内外清单。每项都带精确来源版本、locator、验收依据和当前状态。

## 处理

实际读取合同正文、附件、补遗、技术响应和已批准的承诺，覆盖签署页、范围、交付物、日期、付款、验收、质保、客户配合、排除项、变更和责任限制。逐项区分合同明确要求、售前承诺、客户期望、内部建议和待确认解释。交叉文件冲突保留双方说法，不自行判断法律优先级；登记需要法务/业务授权的澄清。

## 输出与主责

`contract` 主账由本 Skill 维护：obligations、scope_in/out、customer_dependencies、acceptance 和 open_items。总控只登记索引；计划、需求和验收 Skill 消费义务 ID，不复制一套独立合同主账。交接包列出责任人、版本、缺口和下一动作。

## 完成与未知

所有已提供材料均有读取覆盖，义务有来源和验收落点，冲突与未提供附件显式列出后才算完成。缺签署页、附件、补遗、授权或无法确认的条款保持未知/阻塞。`ready` 只表示整理完成，不代表合同生效、客户确认或收入成立；口头承诺不能替代正式依据。

## 模板

使用 `../delivery-orchestrator/assets/templates/contract-handover.md` 和 `template-field-guide.md`；客户版不带内部费率、毛利和未授权判断。
