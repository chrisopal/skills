# 投标编制 Skill 套件

**版本 1.0.0 · 2026-09-27 · 中文 · 16个业务技能 + 1个总控技能**

将招标文件理解、响应策划、证据准备、编写、配图、排版、评审与导出整理为可复用技能。面向投标人侧，不包含招标人组织评标，也不是独立应用或后台服务。

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
| `assets/` | 人工确认空模板、基础文档生成输入示例 |
| `scripts/` | 项目初始化、原件登记、解析辅助、结构校验、评分与覆盖检查、快照、草稿DOCX/PDF、交付打包和本地分发包刷新 |
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

包内不含API密钥、真实客户原件、真实证照、字体文件或任何第三方模型。脚本不自动联网、不安装软件、不发邮件、不签署、不递交标书。合成示例故意保留阻塞，不能拿示例通过结构测试当成业务通过。

本地确认JSON只是交接记录，无法认证批准人；真实授权需宿主审计或实际用户证据。正式投标文件仍需专业与授权人员审核。

## 可选工程测试

在有Python 3.10+的环境中，从本套件根目录执行：

```bash
python -m pip install -r requirements-core.txt
python scripts/check_suite.py
python -m unittest discover -s tests -v
```

文档脚本额外依赖见`requirements.txt`。PDF转换还需要系统已安装LibreOffice；没有时使用宿主导出工具，不会自动安装。
