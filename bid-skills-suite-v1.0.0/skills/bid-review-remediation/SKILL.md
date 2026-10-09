---
name: bid-review-remediation
description: 逐项审核评分条件、关键材料完整性和资格／否决条件，记录原文、正文与证明材料，复核整改后再形成当前版本的交付建议。
metadata:
  version: 1.3.0
  language: zh-CN
  sequence: '15'
  suite: bid-skills-suite
  title: 综合评审与整改闭环
---

# 15｜综合评审与整改闭环

审核顺序：资格／明确否决条件 → 关键证明材料 → 评分条件及失分风险 → 需求、一致性和版式。结构映射、材料存在、章节有文字，均不能直接当作满足。

## 输入与范围

读取招标原文及有效补遗、当前03—14产物和企业证明原件。独立评审可使用等价文件，但须说明实际范围。先读[证据约定](references/evidence-and-safety.md)与[逐项业务评审](references/CORE_REVIEW.md)。目录到写作的版本规则见[写作流程](references/WRITING_WORKFLOW.md)。

原文评分与资格／否决条款必须独立回查，不能仅审核03提取结果。补遗、参数冲突、选项适用性、缺失页面和OCR异常未解决时，保留待核验范围。

用户明确授权的模拟测试按[合成测试](references/SIMULATION_TESTING.md)执行；模拟材料只证明测试流程，不认证真实资格、签章或实际得分。

## 逐项执行

按[章节篇幅与界面图](references/CHAPTER_WRITING_POLICY.md)核对当前策略和原文冲突；推荐篇幅为建议，明确字数与必配图缺口进入整改门禁。设置绑定当前快照；结构通过不代表专业性或评分满足。

1. 冻结原文、评分、合规、材料、目录、正文、图片和排版配置的输入哈希。只要内容变化就重新评审，旧结论标过期。
2. 按05的每条条款核对适用条件、作用阶段和原文后果。明确否决、资格不满足或关键条件未知阻止正式交付。履约违约、普通技术要求、失分和招标失败不能混为废标。
3. 按09的每个材料选用组核对主体、有效期、类别／适用范围、独立数量、完整证明页、所需签章、入稿位置和真实性确认。读取完整材料，不只读取知识库摘要。合同多页、同一合同的不同扫描不算独立业绩；多份证明登记原件中的独立合同／证书身份。
4. 按04的全部计分叶子逐项检查档次、计分次数、封顶、互斥、AND／OR条件及证明材料，并回读实际正文段落。写出已支撑条件、未支撑条件和具体失分原因。客观分须有计算依据；主观分与未知竞价输入不得伪装确定得分。得分未知不等于评分条件未审。
5. 将结果写入 `data.core_matrix` 的 `compliance/materials/scoring` 三张表。每行有目标ID、结论、理由、原文／材料来源、实际正文定位和问题ID。材料逐维记录；任何未查项保留unknown，不自动填passed。满足／部分满足结论必须有正文引用。not_applicable须有具体条件和适用性复核记录。
6. 对未满足、部分满足、未知和不适用项创建FIND-ID，关联目标、来源、现稿位置、影响和整改。评分缺口按失分风险处理；不得把接受风险当成满足强制条件。跨表核对公司、人员、合同、价格、工期和参数。
7. 交相关写作／材料技能提出修订；既有授权范围内的修改可直接推进，涉及真实承诺、资格或价格的新增决定由对应授权人处理。回读新版本及新证据后再关闭问题，不因生成修复建议而关闭。
8. 重算版本并核对三张表覆盖全集；输出JSON及可读报告。未完成逐项评审、关键缺口或版本过期时不得建议正式交付；正式外发授权仍独立。

## 工具与产物

保存 `reviews/15-review.json` 与同名Markdown，使用[产物契约](references/output-contract.md)、[JSON模板](assets/output.template.json)和[报告模板](assets/report.template.md)。详细字段见[Schema](assets/output.schema.json)。

```bash
python scripts/review_checks.py prepare --project /project --out reviews/core-review-plan-r1.json
python scripts/validate_output.py /project/reviews/15-review.json
python scripts/review_checks.py check --project /project \
  --review /project/reviews/15-review.json --snapshot /project/reviews/input-snapshot.json
```

`prepare`只建立全部待核验行，不生成通过结论。`check`验证当前集合、文件哈希、具体引文、检查结果和正式阻塞；不判断全部语义，不认证真实性或审批人。正文引用用JSON Pointer或实际行号，不能引用整个JSON或评审报告自证。缺OCR、图片证据回读或专业判断能力时保留unknown并说明范围。

本技能可独立安装，包含快照与核心检查脚本。来源只读放inputs，正文与分析放artifacts，正式图和排版配置放assets/profiles，试验记录放work；评审放reviews以免自引用。旧报告缺核心矩阵时须重新评审，不继承历史ready。

需要可读界面、截图或PDF时，按[评审展示与打印](references/REVIEW_PRESENTATION.md)使用`render_review_report.py`生成当前JSON的HTML：概览、逐项理由、证据、整改及范围分区，正文和标签字号统一。长引文可展开，打印全部保留；不做一个新的手写卡片页面替代真实评审数据。导出PDF后逐页查看。

## 验收

- 每个计分叶子、合规条款和材料选用组均有唯一结论。
- 原文条件、实际正文和证明原件可回读；支持性证据与合成测试明确区分。
- 关键缺口阻止正式交付；评分损失单列，未知和不适用有依据。
- 整改关闭有实际新证据／复核；对外建议对应当前确切版本。
