---
name: delivery-risk-issue
description: 分开登记不确定风险、已发生问题和质量事项，跟踪触发、影响、措施、责任、升级与关闭证据。
---

# 风险、问题与质量

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入为会议/调研、计划、质量检查、依赖、变更和实际阻塞；输出风险/问题/质量台账、依赖清单和升级材料。

## 处理

每条记录使用稳定 ID、类型 `risk/issue/quality`、标题、来源、影响/概率或已知后果、触发信号、责任人、状态、处置、期限、升级路径和 evidence_refs。风险是尚未发生的不确定事件，问题是已经发生的阻塞；风险转问题保留关联和时间线。质量缺陷关联需求/版本/测试证据。

关闭必须有处置结果与验证证据；“已告知”“改了报告”或口头承诺不能关闭阻塞。分级阈值按项目约定记录，缺阈值不伪造评分。客户确认、内部通过、风险接受和变更批准分别记录。

## 主责与完成

风险/问题主账由本 Skill 维护；各领域提交关联 ID，不复制另一套事实。完成要求输入范围和截止日、责任/期限、升级状态和证据可回读；责任人或触发条件未知时保留 open/blocked。`ready` 不是风险接受、问题解决或客户批准。

## 模板

使用 `../delivery-orchestrator/assets/templates/risk-issue.md`、`risks-issues.csv`、`actions.csv` 和 `template-field-guide.md`。
