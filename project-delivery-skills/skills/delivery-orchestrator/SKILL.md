---
name: delivery-orchestrator
description: 统筹软件定制与系统集成交付项目，恢复有效版本、拆解下一任务、登记产物与确认边界，并把工作路由到已安装的项目交付 Skills。
---

# 项目交付总控

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。所有输入、输出和确认都绑定 `project_id`、`artifact_id`、`revision`、`sha256`、`visibility` 与来源版本。`ready` 只表示作者认为产物可用，不等于内部审核、客户确认或已外发。

## 输入与恢复

输入可以是新项目、已有项目目录、合同/交接材料、当前台账和本次任务。先用运行入口回读项目 `status`/`validate`，再读取实际文件和当前有效集合；聊天摘要、文件名和旧报告不替代读取。记录读取范围、未读附件、扫描页、未转录录音和外部链接缺口。来源、产物和确认分别保留精确版本，不能用最新文件名代替历史引用。

## 路由

本阶段只路由以下已安装技能：`delivery-source-intake`、`delivery-contract-handover`、`delivery-initiation-kickoff`、`delivery-master-planning`、`delivery-discovery-planning`、`delivery-meeting-records`、`delivery-requirements-baseline`、`delivery-business-blueprint`、`delivery-progress-control`、`delivery-resource-timesheets`、`delivery-cost-expenses`、`delivery-risk-issue`、`delivery-change-control`、`delivery-reporting`、`delivery-milestone-acceptance`、`delivery-artifact-review`。专业实施、质量测试、上线、培训、收尾等后续技能在本阶段明确延期，不得路由或宣称已实现。

按共享契约的项目阶段目录归档可阅读成果，内部财务单独保存；不能把仅登记 JSON 当成已生成 Word/Excel。

为每次路由生成任务卡：项目与目标、有效输入及精确版本、执行范围、处理要求、模板/输出位置、完成证据、未决问题、下游影响和写入责任。需求、蓝图、计划、资源、成本、变更、确认各自只有一个主账；总控只登记索引和版本集合，不代替领域判断。

## 完成与异常

只有读回登记结果、实际文件和引用后，才能报告完成。批准变更必须先标为“已批准、待应用”，由受影响领域完整写出候选版本，计划/资源/成本/验收映射更新后，再由总控回读全部对象并一次激活；任何缺失或失败都保留旧有效集合。缺来源、身份/授权不明、版本漂移、输出未读回时保留 `blocked`/待决状态，不能用推断填空。

## 模板

需要内容底稿时使用 `../delivery-orchestrator/assets/templates/index.json`，只加载当前任务相关模板。客户可见范围、确认范围和实际外发动作分开记录；模板占位内容不是项目事实。
