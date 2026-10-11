---
name: delivery-meeting-records
description: 将调研会、周会和设计会的文字或转录整理为有来源的纪要、决策、行动项和待确认事项。
---

# 会议纪要与行动

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。输入是实际会议文字/转录、参会信息、调研计划、录音定位和历史行动项；输出会议纪要、决策记录、行动项和待确认包。

## 处理

先记录实际读取的转录范围、时间段和说话人可信度；未转录或听不清时保留缺口，不猜。把发言分为可引用事实、角色观点、建议、决策、条件决策、争议和待确认事项。每个决定关联 source_refs、会议版本、决定人/角色、范围和生效条件；行动项关联责任、期限、前置依赖和证据。

纪要草稿、内部通过、客户审阅、客户确认分开。参会不等于有权确认，发送纪要不等于客户接受；需要确认的内容进入 `confirmation` 或行动项。更新既有行动主账时使用稳定 ID，不重复创建。

## 主责与完成

会议纪要和行动项主账由本 Skill 维护；需求/蓝图 Skill 只引用已回读的证据。完成要求输入覆盖、定位、决策和行动回读完整；说话人/时间/结论未知则标出并阻塞依赖结论。`ready` 不是决策生效或客户批准。

## 模板

使用 `../delivery-orchestrator/assets/templates/meeting-record.md`、`actions.csv` 和 `template-field-guide.md`。
