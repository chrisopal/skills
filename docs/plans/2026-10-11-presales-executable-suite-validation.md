# 售前 Skill 套件 v0.1.0：实施与端到端验证

日期：2026-10-11。范围为通用 B 端售前，行业信息采用补充材料。用户授权实现、验证、本地安装并推送 Git。此前的八页设计演练不作为本轮实现验证；本轮从原始模拟资料重新生成六页方案。

## 已交付实现

发布目录：[presales-solution-skills](../../presales-solution-skills/README.md)。10个技能覆盖总控、混合材料、需求、澄清、脑图、资料匹配、方案、大纲、逐页内容及方向/内容/文件审核。每个技能可单独发现和调用；共享契约由总控技能携带，安装10个兄弟目录。

Agent负责语义判断；Python标准库CLI负责原件快照、定位提取、修订、精确hash依赖、审核门槛、白名单PPT交接、实际交付文件登记及失效检查。PPT继续使用用户指定的本地ppt-master-plus 4.5.0，不复制其引擎或模板，不增加依赖。

安装器在已有不同内容时拒绝覆盖。当前10个技能已安装至本机Codex技能目录，重复安装返回10个unchanged且hash核对一致。刷新技能列表或新开会话后可用 `$presales-orchestrator` 启动项目。

## 代码与包验证

- 47项单元测试通过：runtime 26项，提取13项，安装8项。
- 套件校验10个技能、0错误；10个入口均通过官方Skill Creator quick_validate。Python语法检查通过。
- 独立代码审查发现逐页artifact_ids原先只验证格式，可能漏掉依赖失效。修复后要求存在并位于直接或传递的精确hash依赖图中；先复现2项失败，再通过26项runtime测试和47项完整测试。
- 测试覆盖修改源/中间成果后审核失效、缺审核和旧审核拦截、路径越界、PPT页映射、文件与渲染证据改动、安装冲突，以及DOCX/PDF/图片读取缺口。业务语义和视觉结论由实际Agent复核，不由上述测试替代。

复跑：

```bash
python3 presales-solution-skills/scripts/validate_suite.py
python3 -m unittest discover -s presales-solution-skills/tests -v
python3 presales-solution-skills/scripts/install.py --dest "$HOME/.codex/skills"
```

本机官方校验器使用已有Python 3.13及PyYAML；本套件运行脚本不依赖PyYAML。没有为了验证安装新包。

## 新六页端到端执行

本地项目：`output/presales-suite-e2e-2026-10-11/`，ID为`PRESALES-E2E-001`，用途`internal-draft`。所有产物留本地，不提交Git。

1. 独立执行Agent仅读取5份原始模拟材料：DOCX、两页PDF、会议Markdown、人工测试白板PNG、模拟补答。图片经过实际查看；未把模拟PNG称作真实现场照片。
2. 新建19条证据、14条需求、5项澄清、汇报主线、5项材料和5项方案，形成6页/10分钟大纲和内容包。核心字段包含提交时间；第一阶段仅客服支持组；接口未知、配置待验证、路线图排除和无收益基线均保留。
3. 主Agent独立回读原件并审核内容。业务确认仍为unconfirmed，模拟补答不冒充用户批准。方向审核是大纲完成后的追溯核查，记录真实顺序，不伪造提前审核。
4. `prepare-ppt`依据当前内容hash与独立内容审核生成白名单Markdown及handoff.json；安装后的runtime也重新执行了交接命令。
5. 使用本地ppt-master-plus DefaultGenerate路线和huixin_product_solution模板，完成规格、执行锁、逐页SVG、讲稿拆分、质量门槛及PPTX导出。新作六页，未复用旧八页成稿。已有授权用于制作决定，没有构造UI确认回执。
6. PPTX具有104个原生文字对象、6个Logo图片、6页备注；全部SVG文字在PPTX和最终PDF中回读无遗漏。原生文字修改、保存、重开副本通过，原文件hash不变。
7. 登记DELIVERY、交付审核及六页实际渲染图hash，当前18项对象全部ready，`validate.ok=true`。该命令明确只证明结构和文件完整性；业务批准仍未确认。
8. 复制真实项目进行负向测试：修改会议原件副本使13项对象stale（含内容、交付及审核）；修改页图使DELIVERY和REVIEW-DELIVERY stale。原始快照只读，测试仅对副本开放写权限。原项目未改动。

## 实际文件及可视化核验

- PPTX：`deliverables/presales-solution.pptx`
- PDF：`deliverables/presales-solution.pdf`
- 内容包SHA-256：`bdb88ab8b19df134d79e701cf48b0336c95701af2ecd8491462ee4415bf29b25`
- PPTX SHA-256：`56177b0c2ab27f1aef0a6046c4ef7068bef141b8b3e39c6b0994ad06b17c0888`
- PDF SHA-256：`f5534ba4d6720586574d3d56006af46c89f50d12898bbeb4b2520b656edf19d2`
- 证据：项目内`reviews/delivery-audit.json`、`render-review.json`、`render/page-01.png`至`page-06.png`、`actual-invalidation-test.json`、`final-runtime-validation.json`。

SVG导出检查0错误、5条提示（多行标题边界与并列文字布局启发式），postflight为passed-with-warnings。实际六页全尺寸渲染均逐页查看，限定、正文、图形无可见遮挡或溢出。交付视觉检查由SVG作者自检，未伪称独立设计审核；上游内容审核者独立于内容作者。

首次LibreOffice渲染出现首屏限定换行及回退字体裁字。已拆分两个独立限定框并重新导出，使用项目局部字体配置再次渲染，最终PDF可读且文字无遗漏；失败版本保留为证据。最终PDF仍使用STSong/STSongti-TC-Bold等替代字体，**并未达到微软雅黑字体保真**。

本轮Mac锁屏，PowerPoint原生打开/导出未完成。备用渲染由LibreOffice 26.2.3.2实际导入PPTX后导出PDF，PyMuPDF转为页图。delivery的pass仅覆盖内部模拟候选稿的内容、可读性及上述文件检查，不覆盖PowerPoint兼容性和精确字体一致性。正式按模板字体交付前需在PowerPoint重做导出及审核；不得引用前一轮八页PowerPoint检查替代本轮。

## 使用范围与后续限制

已证明：新技能+安装后工具+本地PPT技能可以完成一条由Agent执行的混合输入至实际文件审核主线，并追踪变更失效。不是无需Agent即可自动运行的模型服务，也没有完成真实客户验收。

尚未证明：真实扫描件OCR、真实现场照片复杂识别、真实产品与案例核验、多项目并发和PowerPoint原生最终呈现。索引采用单写者；reviewer字符串不是身份认证；自然语言字段仍需人工或Agent审核，白名单不是自动脱敏。

提交范围仅包含可复用源码、测试和文档；生成PPTX/PDF、页图、临时副本及运行记录不纳入Git。当前分支按仓库规则提交并推送，远端HEAD核对结果在任务交付回复中报告。
