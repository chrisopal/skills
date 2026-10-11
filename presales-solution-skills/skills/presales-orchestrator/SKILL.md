---
name: presales-orchestrator
description: 适用于完整 B 端售前方案、继续已有售前项目、按反馈修订方案，或安排需求、脑图、大纲、PPT 与方案审核的连续工作。
---

# 售前方案总控

将客户混合材料变成可解释的方案，再交外部 PPT Skill 制作并审核真实文件。通用 B 端为基线；行业包只补术语、材料和检查项。

## 启动与恢复

先读[交接契约](references/artifact-contract.md)。工作目录由用户指定；无指定时在当前工作区的 `projects/<简短项目名>` 建独立目录，不能写进技能目录。以下 `RUNTIME` 指本技能下 `scripts/runtime.py` 的绝对路径；`PROJECT` 指项目绝对路径，实际调用时替换它们。

```bash
python3 "$RUNTIME" init "$PROJECT" --project-id PROJECT-001 --purpose internal-draft
python3 "$RUNTIME" status "$PROJECT"
```

新项目选择 `internal-draft` 或 `customer-review`；后者表示审阅用途，不代表客户已同意或授权外发。恢复时读取索引和实际成果，先处理 stale/blocked；不凭聊天里的“已完成”跳过回读。

写 `brief` 成果，包含客户/供方、受众、目的、期望决策、会议时长、页数预算、材料范围、授权动作、未知项及行业补充材料路径。用户已授权的动作继续执行；业务内容缺少确认时可制作明确标记的候选稿，不能补造确认。

## 调度

按实际任务读所需技能，不一次加载全部入口。每个技能允许从等价的现有文件开始；先登记其来源和版本，不能伪造缺失流程历史。

| 要完成的结果 | 读取兄弟技能 | 成果 kind |
|---|---|---|
| 原件与证据 | [presales-source-intake](../presales-source-intake/SKILL.md) | evidence |
| 客户需求 | [presales-requirements](../presales-requirements/SKILL.md) | requirements |
| 澄清与补答 | [presales-clarification](../presales-clarification/SKILL.md) | clarification |
| 汇报逻辑脑图 | [presales-storyline](../presales-storyline/SKILL.md) | storyline |
| 产品/公司/案例证据 | [presales-material-matching](../presales-material-matching/SKILL.md) | materials |
| 方案机制与边界 | [presales-solution-design](../presales-solution-design/SKILL.md) | solution |
| 逐页内容计划 | [presales-outline-planning](../presales-outline-planning/SKILL.md) | outline |
| 完整制作内容 | [presales-content-authoring](../presales-content-authoring/SKILL.md) | content |
| 独立审核与复核 | [presales-solution-review](../presales-solution-review/SKILL.md) | review |

主线：简报 → 原件/证据 → 需求 → 脑图初稿 ↔ 澄清 → 选材/方案 → 方向审核 → 逐页大纲 → 内容包 → 内容审核 → PPT → 实际文件审核。澄清与选材可以回流；未受影响分支继续。

- `full`：完成主线至实际文件审核；未授权外发时交付本地文件。
- `discovery`：需求、脑图、澄清后停止；不要求PPT。
- `outline`：完成到可审阅逐页大纲。
- `review`：只调审核技能，明确能核验的范围。
- `revise`：登记新输入，检查依赖影响，只重做失效成果及审核。

## 登记与有效性

Agent 编写契约格式JSON，通过 `register` 验证并保存不可覆盖的修订；命令返回实际hash供下游引用。

```bash
python3 "$RUNTIME" register "$PROJECT" /absolute/path/to/artifact.json
python3 "$RUNTIME" validate "$PROJECT"
```

每个实际消费的上游成果都写进 `inputs`，不能为绕过失效检查漏记。status/validate会检测文件外改和传递失效；恢复时更新受影响成果revision和inputs，然后重新审核。旧版本保留供查证，不直接改登记文件。

## 确认与审核

集中呈现 A需求理解/方向、B逐页大纲、C实际交付版本三个可审阅结果。记录真正说过的确认、对象版本和使用范围；既有明确授权沿用。内部制作授权、内容审核、客户认可、外发授权分别记录。

内容审核交独立Agent或实际审阅人，给原始材料与候选稿，不把预期结论作为指令。工具能检查审核记录绑定和结构，不能验证审阅人身份或代替语义判断。无独立审核条件时记录自检和未检查项，不冒充通过制作门槛；仍可完成上游候选成果。

通过内容审核后按[PPT交接](references/ppt-master-plus.md)调用用户选定的 `ppt-master-plus`，并登记 `delivery` 和绑定实际文件的 `review`。不新造一套渲染器。

## 完成条件

交付用户可直接打开的文件和当前审核结论，指出剩余澄清、兼容限制及适用用途。只有真实文件回读、文本/限定核对、渲染检查完成才能报告文件审核完成。工具缺失时说明具体缺口并保留可复用成果；不能将结构检查通过写成客户验收。
