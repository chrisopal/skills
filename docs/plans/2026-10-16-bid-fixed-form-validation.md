# 1.20.2 固定表单、篇幅整改与导出验证

## 需求与边界

按原招标要求保留材料格式，不能把表格文字层的读取顺序直接作为投标正文。缺少依据的字段在原填写位置提示；企业、人员和合同仍使用用户授权的合成测试材料，真实签章不生成。原件只读，客户原文、生成文件、截图和一次性脚本不纳入仓库。

## 实现与简化

- `scripts/fixed_form_tables.py` 集中校验和输出表格网格、合并、表头与缺项；Markdown 简单表使用管道语法，复杂表使用内嵌 HTML，不另造一套文本转表逻辑。
- `scripts/build_docx.py` 使用同一结构生成真正的可编辑 Word 表格。合并前设置逻辑列宽，合并后设置锚点总宽并清理合并产生的空段落；保留多行正文、重复表头、横向页和逐人分页。
- `scripts/export_checks.py` 核对实际 DOCX 合并结构、缺项文字/黄色高亮，以及表单路径和当前 SHA。允许同一章节包含多个表单，按声明顺序检查全部段落和表格；缺项、乱序、改合并均拒绝。Word 的垂直合并续格只计一次矩形。
- 06 保存原模板；12 增加可选且可空的 `section_id`、`template_path`、`filled_template_path`、`table_spec_path`。未声明时不伪造表单绑定；声明路径越界、缺文件、错章节或哈希过期均拒绝。未知字段保持 `value:null / state:missing`。
- 更新格式提取、商务材料、排版与导出 Skill，分发共用 helper 和 FIXED_FORMS 规程。保留此前批量写作修复：内部状态读取不重复计算全局篇幅建议，最终验收仍完整执行。

没有新增依赖、应用 API、数据库或部署；模型能力仍由宿主提供。选择共用结构而非逐份 PDF 硬编码导出；PDF 的表格重建仍需要宿主识别原页并目视确认，不宣称任意扫描件自动精确还原。

## 青草沙实际文件验收

- 原件 P56—73 的 19 个固定格式均有未填模板和填报 Markdown；9 类含表格的原格式保留列数、行数和合并，多行表头、脚注、签署区及原横向报价表保留。
- 当前 Word 经 Microsoft Word for Mac 更新整个目录并保存，打印质量 PDF 共 **160 页、37 章、35 张表（34 张正文表加封面表）、15 图**。
- 独立 Sol 读取原件规格、当前结构和实际文件：37 个 DOCX 目录缓存/链接、37 个 PDF 目录链接、8 行评分索引的 14 个页码全部对应实际章节；145 条逐项响应唯一且完整；15 张图源与 Word 嵌入哈希一致。
- 42 处缺失字段或签署在 Markdown 保留提示、Word 全部黄色高亮，PDF 全部可见。负责人及六名成员分别按人分页；两个项目经历分别保留各自金额，缺委托单位不自动猜测。
- 160 页缩略总览及代表页可读尺寸抽查通过。全部页无空白页、越界文字/图片/矢量对象；合并宽度错误和合并产生的多余空段落均为 0。不是每页逐字复读或逐像素复刻；横向报价表填报后跨三页并重复表头，人员汇总备用空行与脚注续页。PDF 未额外建立 outline 树，可见目录内链已验证。
- 原 21 条篇幅建议清零，37 章篇幅/配图策略检查无缺口；工期统一为 90 日历天，含春节 9 天不实施、不自动顺延，81 个实施日分配复算一致。
- 当前 9 项评分、30 项合规、37 组材料复审输入有效，自动引用错误为 0。AI 模拟技术分 **36/50**，价格 50 分缺全部有效报价而未知；模拟合同不计真实有效业绩。核心评审和正式发布继续阻塞，42 处缺项、真实证明和签署未被格式检查洗掉。
- 新增表单仅验证本地 Markdown/Word/PDF；已同步的飞书37章技术正文未改，不能将本轮表单说成已同步在线文档。

本地证据项目为 `bid-agent/output/tender-analysis/online-documents-20261016/qingcaosha-user-auth`；最终文件为 `qingcaosha-online-word-r18.docx/.pdf` 和 `qingcaosha-online-complete-r18.md`。核心证据：`export-fixed-forms-r18.json`、`independent-verification-r18.json`、`visual-fixed-forms-r18.json` 及当前评审/评分收据，均留本机。

## 工程检查

使用现有 `bid-agent/backend/.venv/bin/python`，未安装依赖：

```bash
python -m unittest discover -s tests -q
python scripts/refresh_distribution.py
python scripts/check_suite.py
python -m py_compile scripts/build_docx.py scripts/fixed_form_tables.py scripts/export_checks.py scripts/refresh_distribution.py scripts/writing_batch.py tests/test_export_checks.py tests/test_export_layout.py tests/test_writing_batch.py
ruff check scripts/fixed_form_tables.py scripts/export_checks.py
git diff --check
```

- 完整 unittest：**458 项运行，457 通过、1 跳过**；跳过项缺可选 CairoSVG，非本次固定表单路径。包含真实 OOXML、合并宽度/空段落、缺项高亮、乱序/缺表/错合并及多表单同章回归。
- `refresh_distribution.py`：17 ZIP、760 校验项；`check_suite.py`：17 Skill、34 Schema、0 错误。8 个 Python 文件编译、helper/checker Ruff、diff 检查通过。
- 对实际 r18 文件执行 `export_checks.py --spec ... --docx ... --pdf ... --project-root ...`，结果 `passed=true / findings=[]`；06/12/14/15/16 五份当前产物 Schema 通过，正式发布门禁拒绝符合预期。
- Codex、WorkBuddy 各 17 个完整安装目录、各 500 个文件 SHA 与分发源逐一一致；旧安装备份在 Skill 发现目录外。
- 全文件 `ruff check scripts/build_docx.py` 仍报告 23 条既有紧凑语法风格问题；HEAD 基线为33条。本轮未扩大为全文件风格清理，未将此检查描述为全绿。

## 未运行项与限制

未运行新一轮 WorkBuddy 模型执行、Windows、真人双账号并发、扫描 OCR 和真实投标签署/递交；应用前后端 lint/build 不适用。模拟评分是对候选正文和合成材料的判断，不是采购方专家评分或客户验收。仅源码、规程和验证说明提交，客户原件、文档 token、授权凭证和导出物不推送。
