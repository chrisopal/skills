---
name: opportunity-solution-validation
description: 将商机需求交给售前方案能力，并管理演示、POC、客户反馈和方案验证结果；用于方案交流准备、验证安排和方案范围修订。
---

# 商机方案与验证

读取[共享契约](../opportunity-orchestrator/references/lifecycle-contract.md)及[售前集成](../opportunity-orchestrator/references/integrations.md)。输入同一商机 ID、需求/证据、当前方案、客户验证标准和本次授权。

## 处理

1. 回读需求、约束、采购路径和已有版本；区分客户要求、我方建议与未验证假设。
2. 调用可用的 presales-orchestrator 完成所需范围，不重复其需求/PPT引擎。交接成果 ID、版本、来源、条件和预期决策。
3. 演示或 POC 先明确场景、输入、环境、指标、双方配合、成本/时间授权、通过条件。没有基线时给测量方法，不生成收益百分比。
4. 对照真实结果逐项记录通过、失败、未验证和客户反馈；我方技术测试、内部审核、客户认可分别记录。
5. 范围变化保留版本差异、成本/工期影响和未解决项；将最新有效方案登记为 solution 产物，不覆盖旧版。每条客户意见以 record_review 保存需求编号、方案、负责人、期限和是否阻塞；整改复审用 resolve_review 绑定当前方案、具体结论与证据。新版本不能自动继承旧版关闭结果；需复核或重开意见。

## 输出与完成

交付可打开的方案/验证报告、证据、客户反馈、范围及条件、后续行动。按契约注册 solution 文件并登记 solution_scope 等有依据的事实；阶段变化交共享运行层核验。文件生成成功不代表客户认可或阶段完成。

没有售前能力或验证环境时，保留可恢复交接包和具体阻塞；未知能力标记待验证。不能把演示素材冒充实际客户 POC，也不能代客户确认验收。

## 真实售前联动

按[工作台与售前联动](../opportunity-orchestrator/references/workbench-presales.md)使用 `presales-export` 传递已选证据和明确需求。售前完成内容独立审核、PPT实际制作与文件回读后，用 `presales-receive` 登记新的方案版本；同时回读原客户意见是否需要重评。内部文件审核不等于客户批准或外发授权。
