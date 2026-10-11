---
name: opportunity-orchestrator
description: 管理同一 B 端商机从线索、需求、方案验证、报价谈判到合同签单；恢复已有商机、安排阶段任务、处理跟进反馈和核验阶段推进时使用。
---

# 商机全流程总控

先读[共享契约](references/lifecycle-contract.md)。总控管理商机推进；分析、方案、报价与谈判由对应业务 Skill 处理，正式状态统一交共享运行层保存。

## 启动与恢复

以下 RUN 指本目录 `scripts/run.py` 的绝对路径。数据放用户项目目录，不写入技能安装目录。DB 为项目 SQLite 的绝对路径。

```bash
python3 "$RUN" analyze --input /absolute/project/materials.json --db "$DB" --output-dir /absolute/project/views
python3 "$RUN" lifecycle --opportunity-id "$OPP" --db "$DB"
python3 "$RUN" detail --opportunity-id "$OPP" --db "$DB" --output-dir /absolute/project/views
```

新任务先确定客户、商机名称、负责人、采购路径和本次结果。恢复任务先查询并回读同一商机的 lifecycle、证据、未完成行动和成果版本；不能依据聊天中的“已完成”跳过核验。一个客户允许多个商机，不凭公司名称合并不同采购项目。

## 按任务调度

| 用户要完成的工作 | Skill | 交接结果 |
|---|---|---|
| 拜访/邮件/会议材料分析、资格判断与评估 | [opportunity-analysis-skill](../opportunity-analysis-skill/SKILL.md) | 事实、证据、建议阶段、评估与缺口 |
| 决策链、竞争策略、跟进与行动复盘 | [opportunity-pursuit](../opportunity-pursuit/SKILL.md) | 推进计划、行动与完成结果 |
| 需求方案、演示、POC与客户反馈 | [opportunity-solution-validation](../opportunity-solution-validation/SKILL.md) | 带版本的方案及验证结论 |
| 采购路径、报价与投标响应 | [opportunity-commercial](../opportunity-commercial/SKILL.md) | 报价/响应版本、提交记录及商务条件 |
| 价格、范围、付款与合同条款谈判 | [opportunity-negotiation](../opportunity-negotiation/SKILL.md) | 差异清单、授权与谈判结果 |
| 签署核验、签单/关闭及交付交接 | [opportunity-closeout](../opportunity-closeout/SKILL.md) | 签署事实、关闭原因、交接材料 |

只读取本次需要的技能。需求、预算、决策链并行完善；直销、招投标、续约按实际路径推进，不能强制补造没有发生的步骤。既有制作和操作授权沿用；新的价格让步、客户外发与实际签署按具体业务授权执行。

## 保存与推进

1. 新材料按既有 opportunity_id 增量分析，使用 request_id 和当前 expected_revision；先识别冲突、否定、条件和历史事实。
2. 子 Skill 交付证据与变更建议。推断只改变 suggested_stage，不直接变成正式阶段。
3. 依据原始材料核验事实、行动结果和成果文件；组装契约中的 manage 请求，由运行层一次事务提交。
4. 回读 revision、current_stage、history、actions、artifacts 和 contracts。失败时保留原正式状态；先处理明确错误，再用新 request_id 提交修订。
5. 范围、价格、方案或材料版本变化后重查受影响的阶段条件；历史记录保留，不通过覆盖旧记录隐藏变化。

```bash
python3 "$RUN" manage --input /absolute/project/change.json --db "$DB"
python3 "$RUN" lifecycle --opportunity-id "$OPP" --db "$DB"
```

## 完成与限制

汇报当前正式阶段、下一行动及负责人/期限、阻塞和本次保存版本。已签单必须读回实际签署材料及对应记录；内部审核、客户口头意向、中标、PO 模板和评分不能替代签署事实。业务批准、合同生效、回款和收入分别记录。

运行层核验结构、引用、版本和文件摘要，不认证 actor 身份、不判断证据语义、不替人审批或签约。证据不足时保留建议和未解决事项。外部售前/投标 Skill 缺失时按[集成边界](references/integrations.md)交付可恢复的交接包。
