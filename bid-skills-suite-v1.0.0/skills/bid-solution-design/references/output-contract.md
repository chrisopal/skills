# 技术方案设计｜输出契约

版本：1.0。完整机器约束见本技能 `assets/output.schema.json`，它自包含，不需要联网解析Schema。报告与JSON必须表达同一结果。

## 通用信封

| 字段 | 含义 |
|---|---|
| schema_version | 固定1.0，升级需明确兼容性 |
| skill_id | 固定bid-solution-design |
| project_id | 当前项目身份，不跨项目复用 |
| artifact_id / revision | 产物身份与版本；保留旧版本，不静默覆盖 |
| created_at | 实际生成时间，带时区，不借示例时间冒充执行 |
| status | draft / needs_review / blocked / ready；与人工审批无等价关系 |
| inputs | 实际上游文件、版本与SHA256；缺输入不能捏造哈希 |
| summary | 本次结果和范围 |
| data | 专项业务数据，见下表 |
| warnings / blockers | 提示与阻塞分别存储；ready不能有非空blockers |

## 专项字段

| 路径 | 类型 | 约束说明 |
|---|---|---|
| `data.decisions` | `array` | 数组项字段：id, title, requirement_ids, section_ids, approach, dependencies, evidence_ids, assumptions, acceptance, state, confirmation_ref |
| `data.scope_in` | `array` | 按schema填写；未知值仅在允许null的字段使用。 |
| `data.scope_out` | `array` | 按schema填写；未知值仅在允许null的字段使用。 |
| `data.milestones` | `array` | 数组项字段：name, duration_raw, deliverable, dependency |

## 引用与确认

sources中每条引用使用source_id、revision、sha256、location、quote、kind。`kind=synthetic`仅用于演示。来源文字与文档哈希都应与实际原件一致。`confirmation_ref`必须指向实际用户或宿主审计中存在的确认／复核记录，本地填一个非空字符串不构成可信授权。

## 提交前检查

先用`assets/output.template.json`建立结构，再填本次真实信息；不要把`REPLACE_ME`留给下游。运行`python scripts/validate_output.py 文件路径`，检查通过后仍按专项验收表进行人工／模型语义审核。空数组可能是模板或未提取，不自动代表没有相关要求。

## 示例的限制

`assets/example.output.json`只演示字段和关系。它使用合成原文，故保持needs_review或blocked，不伪造真实审批与交付。独立使用本技能时，可用用户给定材料替代上游产物，但inputs必须记录实际读取的材料。
