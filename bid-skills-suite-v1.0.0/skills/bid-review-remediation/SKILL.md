---
name: bid-review-remediation
description: 对当前确切版本进行合规、覆盖、评分、证据、一致性和版式评审，并驱动可追踪整改。 适用于：审核标书、废标检查、需求覆盖、评分自查、查错、整改复核、独立评审。
metadata:
  version: 1.1.0
  language: zh-CN
  sequence: '15'
  suite: bid-skills-suite
  title: 综合评审与整改闭环
---

# 15｜综合评审与整改闭环

对当前确切版本进行合规、覆盖、评分、证据、一致性和版式评审，并驱动可追踪整改。

运行条件：需支持读取项目文件；可选脚本需要 Python 3.10+，文档、视觉/OCR 与绘图能力由宿主提供。

## 触发与边界

当用户提出“审核标书、废标检查、需求覆盖、评分自查、查错、整改复核、独立评审。”时使用。不保证得分或中标，不替代法律／专业评标；不自行批准自己生成的承诺或隐去发现。

## 开始前

先读 [共同证据与安全约定](references/evidence-and-safety.md)。仅当需要细化操作时读 [专项操作手册](references/playbook.md)；输出字段与示例参见 [产物契约](references/output-contract.md)。

输入：03—14全部当前产物、原文与企业证据；独立评审模式还需既有投标书及可靠原文抽取。

上游技能：`bid-source-intake, bid-project-profile, bid-requirements, bid-scoring, bid-compliance, bid-format-extraction, bid-response-strategy, bid-outline-planning, bid-evidence-matching, bid-solution-design, bid-technical-writing, bid-commercial-documents, bid-visuals, bid-document-layout`。独立使用时接收用户提供的等价文件，记录实际输入，不要求虚构完整流程状态。检查原件和产物版本；缺关键信息时给出范围受限的草稿及缺口。

完整候选编标及宿主对话修订的保存、失效和重导出规则见[写作流程](references/WRITING_WORKFLOW.md)。

## 执行步骤

1. **步骤1**

   冻结评审输入集合与文件哈希，包括需求、评分、合规、目录、素材、正文、配图与排版规则；缺必需项时只能出限定范围报告。

   `last-review` hash与当前任一输入字节不一致时不得沿用结论或标ready；需求提取与评分输入分别复核。

2. **步骤2**

   先检查明确否决、资格、文件组成与提交要求，再检查强制需求、证据适用、评分支撑和正文质量；不要先挑错别字后漏掉否决。

3. **步骤3**

   逐项记录结论satisfied／partial／missing／unknown／not_applicable及证据；后两者必须说明原因，不能自动当通过。

4. **步骤4**

   评分自查展示按原规则的条件性判断或范围；主观分不伪装确定值，不计算未知竞价输入。

5. **步骤5**

   交叉核对参数、工期、公司名称、人员、价格、图表、响应表与方案一致性；表述充分不代表实际能力已被证明。

6. **步骤6**

   为每个FIND-ID记录受影响需求／评分／章节、严重度、原文依据、现稿位置、建议、责任人与是否必须人工处理。

7. **步骤7**

   整改交相关技能生成提案，由人采纳；重评确认改变范围，不因写出修复建议就关闭问题。输入有变更时旧评审标stale。

8. **步骤8**

   输出评审快照与未解决项。只有当前输入、无阻塞、必要人工确认齐备时才建议进入16；最终外发仍需要用户明确授权。

## 产物与交接

保存 `15-review.json`（机器可读）和同名 `.md`（可读报告），使用 [JSON模板](assets/output.template.json) 与 [报告模板](assets/report.template.md)。字段必须符合 [JSON Schema](assets/output.schema.json)。不要把模板空值直接当结果；详细演示见 [合成示例](assets/example.output.json)。

01—14产物放项目`artifacts/`，15放`reviews/`，16放`deliverables/`，17放`work/`。来源原件只读置于`inputs/`；图表置于`assets/`；规则配置置于`profiles/`。路径始终相对用户指定项目根，不写死本技能安装目录。

每个输出记录`project_id / artifact_id / revision / inputs / status`。`inputs`内SHA256从实际输入文件计算。缺依赖、未运行检查和待确认分别保留；不把模型产生结果等同于业务完成。

可选执行本技能目录内的校验器：

```bash
python scripts/validate_output.py /absolute/path/to/15-review.json
```

脚本只校验结构及部分一致性，不检查所有真实语义与授权。依赖不足可按清单人工检查，但必须写明“脚本未运行”。

## 验收检查

- [ ] 评审对应确切输入版本。
- [ ] 强制／否决项优先。
- [ ] 每个结论有支持证据。
- [ ] 整改关闭基于复核而非生成动作。
- [ ] 自评结论没有冒充正式评标结论。

## 人工确认点

阻塞项必须解决；一般警告的接受须真实授权人说明理由；接受风险不等于满足强制要求。

## 常见陷阱

- 没有检索到证据不等于确定不满足，需区分未知。
- 警告确认不能消除强制条件不满足。
- 正文更新一字也应重新核验评审快照身份。
- 评审脚本只能查结构，不能替代语义和真实性判断。

## 调用示例

> 请对当前版本做完整评审，逐条给证据、问题、严重度和整改动作；修改后只把有新证据且已复核的事项关闭。

示例原件 `assets/synthetic-tender.md` 和 `assets/synthetic-supplier.md` 全为合成资料，不能用作真实投标证据。场景配置参考 `assets/profile-catalog.json`，所有条目只是待项目核验的种子，不是已通过业务验收的行业规则。

## 失败与恢复

先保存已完成的产物、失败范围和下一步；原件变更或输入哈希变化时重核受影响内容。不要自动覆盖人工新版本，不代签批，不上传资料，不声称已在后台继续运行。测试建议见 `tests/cases.json`；这些是待执行的业务评测用例，不是已通过记录。
