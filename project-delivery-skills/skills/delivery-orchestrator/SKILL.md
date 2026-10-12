---
name: delivery-orchestrator
description: 统筹软件定制与系统集成交付项目，恢复有效版本、拆解下一任务、登记产物与确认边界，并把工作路由到已安装的项目交付 Skills。
---

# 项目交付总控

先读[共享产物契约](../delivery-orchestrator/references/artifact-contract.md)。所有输入、输出和确认都绑定 `project_id`、`artifact_id`、`revision`、`sha256`、`visibility` 与来源版本。`ready` 只表示作者认为产物可用，不等于内部审核、客户确认或已外发。

## 输入与恢复

输入可以是新项目、已有项目目录、合同/交接材料、当前台账和本次任务。先用运行入口回读项目 `status`/`validate`，再读取实际文件和当前有效集合；聊天摘要、文件名和旧报告不替代读取。记录读取范围、未读附件、扫描页、未转录录音和外部链接缺口。来源、产物和确认分别保留精确版本，不能用最新文件名代替历史引用。

## 路由

路由以下已安装技能：`delivery-source-intake`、`delivery-contract-handover`、`delivery-initiation-kickoff`、`delivery-master-planning`、`delivery-discovery-planning`、`delivery-meeting-records`、`delivery-requirements-baseline`、`delivery-business-blueprint`、`delivery-progress-control`、`delivery-resource-timesheets`、`delivery-cost-expenses`、`delivery-risk-issue`、`delivery-change-control`、`delivery-reporting`、`delivery-milestone-acceptance`、`delivery-artifact-review`、`delivery-solution-design`、`delivery-ui-field-design`、`delivery-integration-data`、`delivery-work-package`、`delivery-quality-testing`、`delivery-go-live-transition`、`delivery-training-handover`、`delivery-closure-warranty`。专项技能组织设计与工程证据，实际开发/部署需调用已有专业工具并遵守本次任务授权。

| 本次任务 | 路由与契约 |
|---|---|
| 合同到培训运维移交 | 上述第一、二批专项技能；[实施契约](references/software-delivery.md) |
| 行政结项、质保与剩余义务 | `delivery-closure-warranty`；[收尾与复用契约](references/reuse-closure.md) |
| 固定/工时/混合计费配置 | 总控登记 `profile`，金额按币种保留；配置估计不代表收入或开票 |
| 客户模板适配 | 总控登记 `template_mapping`；绑定实际 JSON 字段规格，准备本地 JSON 草稿 |
| 多项目审查 | 总控 `portfolio`；只读当前 UTC 提取日的当前快照，显式人员身份映射和共享容量 |
| 任务/代码/财务/文档交换 | 总控登记 `exchange`；本地候选与收据核对，不发送、不自动应用业务主账 |

第三批任务先读[收尾与复用契约](references/reuse-closure.md)。保留行政结项、质保移交、质保结束和全部义务解除四个独立结果；真实收尾不得用未来截止日提前满足义务。组合视图不是历史重建，禁止合计不同币种或把同名人员自动视为同一人；模拟项目与真实项目不混汇。

按共享契约的项目阶段目录归档可阅读成果，内部财务单独保存；不能把仅登记 JSON 当成已生成 Word/Excel。

为每次路由生成任务卡：项目与目标、有效输入及精确版本、执行范围、处理要求、模板/输出位置、完成证据、未决问题、下游影响和写入责任。需求、蓝图、计划、资源、成本、变更、确认各自只有一个主账；总控只登记索引和版本集合，不代替领域判断。

## 完成与异常

只有读回登记结果、实际文件和引用后，才能报告完成。批准变更必须先标为“已批准、待应用”，由受影响领域完整写出候选版本，计划/资源/成本/验收映射更新后，再由总控回读全部对象并一次激活；任何缺失或失败都保留旧有效集合。缺来源、身份/授权不明、版本漂移、输出未读回时保留 `blocked`/待决状态，不能用推断填空。

## 模板

需要内容底稿时使用 `../delivery-orchestrator/assets/templates/index.json`，只加载当前任务相关模板。客户可见范围、确认范围和实际外发动作分开记录；模板占位内容不是项目事实。


## 实际使用与日常闭环

真实材料独立验证、六类核心文档导出，或进度/工时/风险/变更工作台任务，读[日常交付规程](references/daily-delivery.md)。先辨明真实/模拟来源；自动来源检查不替代语义审核。日常录入沿用项目主账，保留有效基线，工时先提交、变更仅申请；客户周报与内部财务分开。
