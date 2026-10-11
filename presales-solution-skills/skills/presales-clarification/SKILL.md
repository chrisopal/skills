---
name: presales-clarification
description: 适用于售前材料冲突、方案前提不明、准备客户访谈问题、补充资料清单，或把新回答回写到需求与方案。
---

# 售前澄清与补答

先读[成果契约](../presales-orchestrator/references/artifact-contract.md)。输入为需求、脑图、方案差距及本次会议阶段。

## 执行

1. 合并同一对象的问题，按影响方案选择、事实可信度、一般补充分级。每个问题只问可回答的业务事实或决定。
2. 写Q-ID、question、rationale、impact_ids、priority、合适respondent、requested_material；说明不回答会影响哪项方案或哪页。
3. 提供简短访谈提纲或补资料清单。已经能由材料回答的问题先自行读取，不重复问用户。
4. 收到实际回答后登记其来源快照和EV定位，再写answer/answer_evidence_ids/decision，状态改answered。没有回答但获准按假设推进时标assumed，保留限定与影响，不能标answered。
5. 告知总控受影响REQ/SOL/SLIDE，更新对应成果revision和依赖；确认回答不等于批准整份大纲或方案。

## 完成与异常

问题有对象、原因、回答人和影响；关闭基于真实回答。无人回答时可继续无关分支或显式假设的内部讨论稿。影响关键范围、价格、工期或产品承诺的未知项，不能悄悄作为确定结论。这里只准备沟通内容；发送客户需要用户已有发送授权。
