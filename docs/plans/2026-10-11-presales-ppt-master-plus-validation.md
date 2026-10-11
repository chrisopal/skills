# 售前流程模拟验证：本地 ppt-master-plus

日期：2026-10-11。依据：[流程设计](2026-10-10-presales-solution-skills-design.md)。

## 结论与范围

**一条模拟售前主线已跑通，并完成实际 PPT 文件回读。** 使用本地 `ppt-master-plus` 4.5.0 制作8页可编辑PPT，使用Microsoft PowerPoint实际打开并导出PDF。上游独立审核首次发现3项问题，修订2复核通过。

这是按设计执行的人工/Agent协同演练，不是10个新售前Skill的自动集成测试。售前Skill尚未实现或安装；全部角色、公司、产品及材料为模拟；业务确认仍为 `unconfirmed`。

## 输入与流程

虚构客户“澄川企业服务”、供应商“衡序软件”、产品“协同台2.4”，讨论客服支持组工单协同试点。

| 环节 | 实际输入/产物 | 验证结果 |
|---|---|---|
| 混合材料归集 | 客户DOCX、产品PDF、会议MD、模拟白板PNG、补答MD | 5份原件均有hash和读取范围；DOCX回读10段并渲染1页，PDF回读及渲染2页；图片目视读取 |
| 需求与澄清 | 需求矩阵、证据索引、澄清台账 | 全公司/单团队冲突由模拟补答收敛到客服支持组；接口与收益基线保持未知 |
| 脑图与方案 | 叙事脑图、材料匹配、方案蓝图 | 7个方案对象；标准、配置、定制/第三方、路线图能力分开 |
| 页面交接 | 逐页大纲、JSON/Markdown内容包修订2 | 8页；页到需求/证据/方案/素材/成果引用、locked_claims、可见限定完整 |
| 独立内容审核 | 独立Agent重新读取原件及版本链 | 首次FAIL，3项发现整改后PASS；保留两轮记录 |
| PPT制作 | 本地ppt-master-plus Default Generate；慧新产品方案模板 | 设计规范与执行锁、手工编写8页SVG、备注、原生DrawingML导出 |
| 实际文件审核 | PPTX、原生PDF、8页渲染、文本与备注对账 | SVG 8/8零错误零警告；导出postflight passed；113个原生文本对象；8页备注保留 |
| 编辑测试 | 复制PPT，修改一个原生文本对象，保存后重新读取 | 通过；原始交付PPT的hash未改变 |

图片是人工绘制的模拟白板，不是真实照片或OCR测试。15分钟是交流安排，未进行录音、自动配音或实测演讲时长。

## 发现与整改

1. **目标混入现状**：现状链原来出现“回访关闭”，原件只支持期望目标。改成“记录分散”，回访保留在目标页。
2. **原子字段遗漏**：只写“操作日志”未覆盖源需求“提交时间”。需求、方案与第3页显式保留“受理/提交时间”；二者是否同一时点仍待业务定义。
3. **方案版本无法追溯到页面**：补稳定方案对象ID、artifact输入版本/hash、逐页solution_ids/artifact_ids、locked_claims与来源索引，独立重算验证。
4. **预览器兼容差异**：LibreOffice替代字体且第4、5、7页出现额外换行。PowerPoint原生打开及本地打印质量PDF正常，PDF嵌入微软雅黑与Arial。原生PDF用于最终预览；LibreOffice兼容性未宣称通过。

首次SVG检查还纠正了背景ID、页角色、模块边界及资源状态枚举；未修改检查器或技能源码。

## 交接与验收约束

- 制作输入只传内容包Markdown；不把完整内部台账和客户原件交给PPT渲染环节。
- 内容包JSON审核后冻结；其中pending审核字段由绑定同一hash的外部独立报告补充。不能凭旧报告批准未来版本。
- 实际PPT全部文字与SVG逐项对账，原生PDF文字同样回读；备注逐页与源备注对账，均无缺失。可见限定不能仅藏在备注。
- 图形和文本为原生对象，品牌标识为图片；能力表/指标表采用可编辑文本与形状，不宣称原生PowerPoint表格或图表。
- 业务内容未确认不阻碍本次内部模拟制作；没有生成虚构确认回执，也没有对外发送。
- 本地技能依赖应显式选择已有Python环境：本机 `/opt/homebrew/bin/python3.13` 可运行预览/制作；默认Python缺Flask。未安装新依赖。

## 证据与复查位置

全部生成文件留在本地 `output/presales-validation-2026-10-11/`，不纳入Git。

| 路径（相对本地运行目录） | 内容 |
|---|---|
| `intake/` | 5份冻结模拟源文件 |
| `artifacts/` | 需求、证据、澄清、脑图、方案、材料、大纲、内容包、hash索引 |
| `review/upstream-independent-review.md` / `.json` | 独立初审与修订2复核 |
| `review/audit_delivery.py` / `delivery-audit.json` | 对实际PPT/PDF逐页文字、备注、编辑保存回读的脚本和结果 |
| `review/ppt-handoff-result.json` | 输入版本/hash、实际文件hash、页面映射及可编辑性边界 |
| `review/visual-verdict.json` | PowerPoint/PDF目视审核；94分，仅为Agent判断 |
| `presales-workorder-test_ppt169_20261011/validation/` | SVG检查与PPTX导出检查 |
| `presales-workorder-test_ppt169_20261011/review/native/` | 原生PDF逐页PNG、总览、文字回读 |
| `售前流程验证_工单协同模拟.pptx` | 可编辑演示文稿 |
| `售前流程验证_工单协同模拟.pdf` | PowerPoint本地打印质量导出 |

冻结内容包JSON SHA-256：`db0c52c58a3dc3b1c97bce2fe8ef5a4ff59d2d43f63e6537f1ca6746648d63ff`。

PPTX SHA-256：`50fd14127b364ed4f2dc7c971196326bba807a4edd3f7d72524fe51261f54d9f`。

原生PDF SHA-256：`b3cee483424c422273093645f8feb76e310e0ac050010b71c8e0fc40489bd7c6`。

本地复跑文件审核：`/opt/homebrew/bin/python3.13 output/presales-validation-2026-10-11/review/audit_delivery.py`。该脚本依赖本次本地生成文件，不是仓库通用验收器。

## 尚未验证

真实扫描件/OCR、模糊现场照片、真实客户资料、跨行业材料包、长篇大纲、自动Skill路由、自动变更失效传播、缺件恢复与真实客户确认均未验证。原生编辑测试覆盖一个文本对象；未穷尽所有对象或其他Office版本。没有把本次文件审核结论当成客户验收。

后续实现应先把本次已跑通主线固化成可调用Skill，再用真实脱敏项目及负向样本检验，不必增加新的PPT引擎。
