---
name: presales-content-authoring
description: 适用于按售前逐页大纲写完整页面正文、讲稿、图规格，准备外部 PPT Skill 输入，或修订具体页面内容。
---

# 售前逐页内容编写

先读[成果契约的内容包段](../presales-orchestrator/references/artifact-contract.md)及[完整示例](../presales-orchestrator/assets/content.example.json)。输入为有效大纲、方案、材料及语言要求。

## 执行

1. 按SLIDE-ID逐页写title、key_message、supporting_points和speaker_notes；标题、结论与论据相互支持。正文能直接排版，不把写作留给PPT工具。
2. 给visual_type与完整图规格：数据图有数据/单位/来源，流程图有节点/连接/条件，系统图区分当前与候选边界。素材用实际授权文件及来源。
3. 每页必填requirement_ids、solution_ids、evidence_ids、material_ids、artifact_ids、visible_caveats、locked_claims和review_status。所有实际上游成果绑定envelope.inputs；禁止只有源文件hash而缺方案版本链。
4. visible_caveats写给观众看的必要限定，locked_claims明确不能改的范围、版本、数字、条件；两者不能只放讲稿。受理/提交等时点需要单独保留，口径未定就明确待核对。
5. 写全局受众、目的、页数、时长、主题建议、story_arc、appendix与citation_index；语言与项目用词统一。内部销售判断与客户内容分别保存，避免经自由文本进入交接包。
6. 登记content后交审核技能；审核记录绑定冻结hash。审核通过后由总控prepare-ppt生成制作输入，不能自己把review_status改pass替代审核。

## 完成与异常

业务结论、文字、关系和限定已完整，制作方只需做视觉呈现。发现方案缺口返回方案设计，材料缺口返回选材，事实疑问返回澄清。更新内容提高revision并重审；排版压缩不能悄悄扩大承诺或删除限制。
