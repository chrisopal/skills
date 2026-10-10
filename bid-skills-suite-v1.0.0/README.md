# 投标编制 Skill 套件

**版本 1.16.0 · 2026-10-10 · 中文 · 16个业务技能 + 1个总控技能**

新增[质量闭环](docs/QUALITY_WORKFLOW.md)：逐条评分条件与共同事实、实际导出内容收据、能力预检和限次整改；优化继承评分篇幅及连续中文检索。所有语义和视觉结论仍须实际宿主核验。

新增[评审报告展示与打印](docs/REVIEW_PRESENTATION.md)：直接读取当前评审矩阵，统一概览、评分项、证据及整改版式；基础Word工作稿统一表格、图片、图注与页码字体。展示与排版不改变业务结论，正式交付门禁仍独立执行。

新增[核心逐项评审](docs/CORE_REVIEW.md)和[导出配置](docs/EXPORT_LAYOUT.md)：评分叶子、合规条款与材料组逐项核验，正式门禁拒绝漏审、证据漂移和关键未知；封面、多级目录、字体、缩进、行距、页边距与页眉页脚可配置。目录域仍须实际引擎刷新及逐页验收。

新增宿主子Agent按章节并行编写、独立提案、限次重试、恢复与协调者版本合并；任务状态与实际Agent身份落盘，不能以配置保存冒充已并行执行。详见[并行章节写作](docs/PARALLEL_WRITING.md)。

新增完整候选编标与宿主对话修订流程：固定表单、全部章节及逐项响应继续推进，缺失企业事实和报价留空。修改后作废旧审核/导出，重新核对当前版本、页码及实际文件；正式采纳与递交门禁保留。

新增有官方来源边界的可执行投标版式候选模板、项目覆盖记录及字号/缩进/段间距读回验证。配图方式可由用户选择，架构图默认SVG、系统界面示意默认Agent自带生图Skill。本次明确由配图Skill调用当前宿主实际生图能力，区分界面设计示意、SVG功能架构与真实系统截图；编辑器新增按章节展示实际图的预览和图源入口。保留可落盘配图配置、父子目录展开及同源HTML报告。保留目录到写作、覆盖检查、编辑保存、冲突历史、段落追溯及图文工作稿；配置不代表工具已可用或图片已生成。正式采纳仍需真实确认。HTML采用enterprise-ui-design规范。保留四类模板、公开语料、PaddleOCR、本地／宿主知识与项目Wiki。为保留已有安装链接，源码目录名称继续使用 `bid-skills-suite-v1.0.0`；实际版本以此处与registry为准。

将招标文件理解、响应策划、证据准备、编写、配图、排版、评审与导出整理为可复用技能。面向投标人侧，不包含招标人组织评标，也不是独立应用或后台服务。

排版来源与模板：[投标版式模板指南](docs/BID_LAYOUT_TEMPLATES.md)。以招标文件及有效补遗为权威，通用模板补齐未规定项；正式成稿仍需原有审核与交付门禁。

## 从哪里开始

1. 先读 `START_HERE_先读我.md`，按你的宿主选择整套目录或单技能ZIP。
2. 打开 `skills/bid-orchestrator/SKILL.md`，向智能体提供真实项目原件与工作目录。
3. 先做理解确认，再准备证据、设计方案与编写；不要将合成示例或模板当成实际投标结果。

## 包内内容

| 目录/文件 | 用途 |
|---|---|
| `skills/` | 17个标准目录，每个含SKILL.md、专项手册、契约、Schema、模板、示例、测试场景和本地校验器 |
| `installable-zips/` | 本地分发时生成的17个单独技能压缩包；运行`scripts/refresh_distribution.py`后与skills目录内容一致 |
| `registry.json` | 技能编号、依赖、输入说明、输出位置和人工确认点 |
| `profiles/` | 2个招采检查种子、5个行业领域种子、2个版式检查种子 |
| `assets/` | 四类提取模板与分类契约、人工确认空模板、基础文档生成输入示例 |
| `benchmarks/public-tenders/` | 公开原件来源清单、AI候选标注、可复跑验证说明；原件本地保存 |
| `scripts/` | 项目初始化、原件登记、原生／可选OCR解析、项目知识与Wiki、结构校验、评分与覆盖检查、快照、草稿DOCX/PDF、交付打包和本地分发包刷新 |
| `examples/` | 智能工厂17产物合成链 + 设备采购缺资料反例 |
| `docs/` | 安装、契约、场景组合、人工门禁、测试和工具限制说明 |
| `tests/` | 可在本地运行的工程检查，不调用真实模型 |
| `QA_REPORT.md` | 本次实际执行结果、通过范围和未验证部分 |

## 技能目录

| 编号 | 技能 | 标识 |
|---|---|---|
| 01 | 招标资料整理与原文解析 | `bid-source-intake` |
| 02 | 项目画像与场景适配 | `bid-project-profile` |
| 03 | 需求提取与结构化 | `bid-requirements` |
| 04 | 评分体系提取与分析 | `bid-scoring` |
| 05 | 资格、否决条件与提交要求提取 | `bid-compliance` |
| 06 | 强制目录与格式模板提取 | `bid-format-extraction` |
| 07 | 需求澄清与投标响应策划 | `bid-response-strategy` |
| 08 | 标书目录规划与覆盖映射 | `bid-outline-planning` |
| 09 | 企业素材与证明材料匹配 | `bid-evidence-matching` |
| 10 | 技术方案设计 | `bid-solution-design` |
| 11 | 技术标正文与响应表编写 | `bid-technical-writing` |
| 12 | 商务与资格文件编制 | `bid-commercial-documents` |
| 13 | 标书配图与图表制作 | `bid-visuals` |
| 14 | 标书排版与文档编排 | `bid-document-layout` |
| 15 | 综合评审与整改闭环 | `bid-review-remediation` |
| 16 | 导出与成稿验收 | `bid-export-acceptance` |
| 17 | 投标编制总控 | `bid-orchestrator` |

## 使用边界

这是完整编写的技能规程与辅助工具初版，不是“已在全部智能体平台和真实招标项目中验收通过”的产品。所有行业配置为待项目核验的种子。没有内置法定资格门槛、费用比例或最新法规结论；实际规则适用需按项目核验。

包内不含API密钥、真实客户原件、真实证照、字体文件或任何第三方模型。原生解析和项目知识脚本默认离线；仅显式启用 OCR 时请求已配置服务。宿主知识库由 Agent 调用本次实际开放的检索工具，再保存结果快照。本套件不自动安装推理环境、不发邮件、不签署、不递交标书。合成示例故意保留阻塞，不能拿示例通过结构测试当成业务通过。

分类与模板：[跨类别首次识别](docs/TENDER_ROUTING.md)。目录与写作：[执行、编辑保存及测试边界](docs/WRITING_WORKFLOW.md)。

配置与使用：[OCR 服务](docs/OCR_SETUP.md)、[本地／宿主知识与 Wiki](docs/KNOWLEDGE.md)。技术图默认SVG，可由用户改选；界面示意和概念图默认由宿主自带生图Skill执行。真实 OCR 模型质量与各宿主知识库连通情况必须分别验证。

本地确认JSON只是交接记录，无法认证批准人；真实授权需宿主审计或实际用户证据。正式投标文件仍需专业与授权人员审核。

## 可选工程测试

在有Python 3.10+的环境中，从本套件根目录执行：

```bash
python -m pip install -r requirements-core.txt
python scripts/check_suite.py
python -m unittest discover -s tests -v
```

文档脚本额外依赖见`requirements.txt`。PDF转换还需要系统已安装LibreOffice；没有时使用宿主导出工具，不会自动安装。

理解报告：[JSON/Markdown与HTML展示](docs/REPORTS.md)。运行质量：[执行复核](docs/EXECUTION_QUALITY.md)、[已发现问题与修复状态](docs/KNOWN_ISSUES.md)。

明确授权的模拟企业材料端到端测试参见 [SIMULATION_TESTING](docs/SIMULATION_TESTING.md)，模拟评审通过与正式发布授权保持分开。

## 技术图工具与模板

13新增可选择的[enterprise-diagrams](../enterprise-diagrams/SKILL.md)独立 Skill：八类结构、六套主题、JSON可编辑源和SVG矢量输出；配置diagram_engine=blueprint，PNG使用宿主已有CairoSVG。保留Draw.io/PlantUML/Mermaid与auto路由，SVG/PNG独立选择；系统界面仍默认使用宿主生图Skill。工具发现、版本化导出、对话修改与布局模板见[DIAGRAM_TOOLS.md](docs/DIAGRAM_TOOLS.md)。本地运行工具不是新增Python依赖；安装与宿主能力需实际核验。

章节设置与自动建议：[按评分条件推荐篇幅、逐章覆盖和系统界面图](docs/CHAPTER_WRITING_POLICY.md)。
