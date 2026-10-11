---
name: presales-storyline
description: 适用于先形成售前方案脑图、整理汇报逻辑、按受众重组论点，或发现汇报缺口。
---

# 方案汇报脑图

先读[成果契约](../presales-orchestrator/references/artifact-contract.md)。脑图回答“需要讲清什么”，此阶段不固定每页怎么排。

## 执行

1. 读取受众、会议目的、期望决定、当前需求与澄清；未知受众先写明确假设。
2. 以建议结论与客户问题组织层级节点，覆盖适用的“为什么做、做什么、怎么做、凭什么、如何推进、请求什么决定”。不强制每个项目都用六章。
3. 每节点给NODE-ID、parent_id、customer_question、claim、requirement_ids、evidence_ids与gaps。把待澄清或待补材料挂到对应论点，不另造无关联清单。
4. 产出storyline JSON及由其派生的可编辑Markdown树；需要可视图时调用可用绘图能力并保留源文件。公司介绍与案例只在支撑客户结论时进入主线。
5. 登记storyline并给出core_message和decision_request。新增材料改变主结论时更新节点及方向确认范围。

## 完成与异常

每分支有客户关联、论点、依据或缺口，最后有明确下一步请求。脑图可以早于方案细节；不要把它当逐页大纲或已经批准的方案。主结论缺证据时交澄清/选材，保留候选分支。
