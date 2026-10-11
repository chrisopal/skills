---
template_id: delivery-template-field-guide-v1
template_version: 0.1.0
visibility: internal
status: template
---

# 项目交付模板字段与口径指南

本目录的 Markdown/CSV 是可编辑底稿，空白或占位不构成事实。填写前保留 `project_id`、`artifact_id`、`revision`、`owner`、`source_refs`、`input_versions`、`content_hash`、`visibility`、`status`、`as_of`、`review_refs`、`confirmation_refs`。每次修订递增 revision，并回读登记文件和 SHA-256。

## 通用状态

`draft` 表示仍在整理；`ready` 表示作者认为可用；`blocked` 表示关键输入、权限、证据或决定缺失。`ready` 不等于内部审核、客户确认、验收或已外发。确认记录必须绑定精确版本、哈希、范围、确认人角色、日期、渠道和证据；条件确认保留未决项。

## 台账口径

- 日期同时区分 baseline、forecast、actual；未知值留空并写原因，不填零。
- 需求、流程、页面、字段/权限、接口/数据和验收场景使用稳定 ID，建立双向映射。
- 工时必须关联人员、日期、工作包和活动；未填报不是零，外包工时不自动计入内部人工。
- 成本的申请、发生、报销、付款是同一事项的状态/证据；`estimate`/`committed` 是剩余预计，`incurred` 是已发生，禁止双计。同一逻辑事项保持稳定 cost_id；travel_or_expense_ref、procurement_ref、external_ref 为同一关联号的别名，多个别名须一致，不同事项不得复用。第一批不支持采购部分发生拆账，使用单一汇总事项并明确依据。
- 风险与问题分开；关闭必须有关联处置和验证证据。
- 变更先记录实际批准，再由领域主账写候选版本，完整回读后一次激活；失败保留旧有效集合。

## 常用英文键的中文含义

| machine key | 中文含义 | 适用口径 |
|---|---|---|
| `project_id` / `artifact_id` / `revision` | 项目 ID / 产物 ID / 修订号 | ID 稳定；修订号递增，不覆写历史 |
| `source_refs` / `input_versions` / `evidence_refs` | 来源引用 / 输入版本 / 证据引用 | 绑定精确版本、哈希和定位 |
| `requirement_id` / `process_id` / `page_id` | 需求 / 流程 / 页面编号 | 用于需求到蓝图和验收的双向追溯 |
| `field_id` / `permission_id` / `interface_id` | 字段 / 权限 / 接口编号 | 不能只靠截图或接口连通证明完成 |
| `baseline_start` / `forecast_finish` / `actual_finish` | 基线开始 / 预测完成 / 实际完成 | 三种日期并列，预测不改基线 |
| `work_package_id` / `completion_rule` / `remaining_work` | 工作包 / 完成规则 / 剩余工作 | 完成必须有规则和证据，工时不等于完成度 |
| `state` / `amount` / `payment_status` | 成本状态 / 金额 / 付款状态 | 状态不改变发生金额；避免申请、报销、付款重复计费 |
| `type` / `owner` / `action` / `evidence_refs` | 风险问题类型 / 责任人 / 处置 / 关闭证据 | 风险、问题、质量分开，关闭需要验证 |
| `state` / `affected_ids` / `replacements` | 变更状态 / 受影响对象 / 候选替代版本 | 批准与生效分开，完整应用后一次激活 |
| `scope` / `actor` / `role` / `origin` | 确认范围 / 确认人 / 角色 / 来源类型 | `simulation` 仅限模拟项目；确认不由 ready 推断 |

## 可见性

`customer` 模板不得带内部费率、毛利、个人敏感信息、未授权判断或内部成本明细。模板元数据只提供使用指导，不能推断任何客户、合同或确认事实。
