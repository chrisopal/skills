# 第一批验证记录 · 2026-10-11

版本 0.1.0，适用于软件定制开发与系统集成。实现 17 个兄弟 Skills，以及 29 项已登记模板：17 份 Markdown 文档和 12 份 CSV 台账。Office 导出为 17 个原生 DOCX 与一个含 12 张表的 XLSX。

## 验证结果

| 检查 | 结果与范围 |
|---|---|
| 自动检查 | 使用已有 Office 库的 Python，70 项 unittest 全部通过；普通 Python 无 Office 库时 2 项集成测试显式跳过 |
| 技能结构 | suite validator 通过；17 个 Skill Creator quick_validate、17 个 agents/openai.yaml 解析通过 |
| Python | 10 个源文件 AST 解析通过；无新增依赖，未配置额外 LSP/静态类型检查器 |
| 安装 | 安装到本机 ~/.codex/skills；17 个兄弟目录逐文件哈希一致，重复安装不覆盖用户差异 |
| 模拟项目 | 24 个当前登记对象、5 个有效基线；validate 的 ok/effective_ok 均为 true |
| 工程证据 | 本地工单模块实际执行 5 项测试，覆盖创建/保存回读、标题规则、资产桩映射/异常、创建权限与审批角色/状态分支 |
| 业务审阅 | 独立 Agent 对最终精确版本的 BP、WEEKLY、MILESTONE 复核通过；初次 conditional 报告保留 |
| 本地交付包 | discussion 模式生成 BP/WEEKLY/MILESTONE；confirmed 模式仅演练 BP/MILESTONE 的同版本模拟确认；文件清单及哈希回读通过，sent=false |
| Word | 17 个 DOCX 全部读取原生文本/表格；本机现有 LibreOffice 导出 17 个 PDF、共 25 页，检查整组缩略图及代表页，中文可读、表格未截断、表头与空白行不分离 |
| Excel | 12 张原生表的表头、冻结行、筛选和蓝色样式回读；未在 Microsoft Excel 中完成原生应用交互验收 |
| 审阅页 | Enterprise UI Design 蓝色规范；实际浏览器验证内部/客户过滤、搜索 3 条/空结果 0 条、导航清除过滤并定位、版本折叠、键盘访问及窄屏表格滚动；桌面/窄屏无页面横向溢出 |

Skill Creator 验证复用已有 Python 3.13 / PyYAML；Office 测试复用 Codex 内置 Python 的 python-docx/openpyxl。没有安装新依赖。内置 Word 预览器出现中文缺字，未接受该渲染结果，改用本机现有 LibreOffice 完成实际文件检查。跨机器字体替换和 Microsoft Word/Excel 的最终分页仍需按实际环境复验。

## 演练内容与边界

案例为 `DEMO-WORKORDER`，purpose=simulation。合同、调研逐字文本、决定、工时/费用均为清楚标记的模拟输入；没有实际录音。工程代码和测试实际运行，但资产接口是本地目录桩，不能证明真实第三方网络、认证或生产环境可用。

主线：合同义务 → 启动/调研计划 → 纪要/需求 → 业务及实施蓝图 → Master Plan → 审批范围变更 → 工时/成本/风险/周报 → 本地模块证据 → 里程碑与独立审核 → 本地准备包。

初次独立复核发现审批规则来源、设计映射、周报输入引用、测试定义/条目证据与费用来源缺口。整改补充明确标注的模拟原文，收窄映射，登记实际测试文件，补测访客审批拒绝/已拒绝状态的重复审批拒绝，并按场景绑定测试。已拒绝状态通过显式测试夹具设置，未声称实现拒绝操作 API。第二次独立复核仅对整改后的精确版本通过。

成本演练：内部人工 3,920，其他发生 2,100，采购承诺剩余 3,000，剩余人工估计 10,000；预测 19,020，对比模拟批准预算 22,000，差异 -2,980，币种 CNY。外包 5 小时只核验，不与供应商金额再次累加。成本与工时明确声明假设证据不足，complete=false；算术正确不代表真实财务凭证完备。

## 已修复并复测的问题

- 客户 HTML 的嵌套凭据/内部字段过滤，与本地客户包共用禁止字段集合。
- 当前候选不能仅凭 ID 被标为有效基线；采用运行工具的精确版本/hash 标志。
- 差旅/采购逻辑关联号的别名去重；已有成本行、稳定 ID、关联号跨版本保留，禁止删除后换号重记。第一批不支持采购部分发生拆账；纠错保留原行及依据。
- 模板输出拒绝悬空符号链接；先完整生成，再以排他方式发布；发布失败回滚本次输出。
- 实际浏览器检查发现中文化误改 JavaScript 变量导致搜索失败；修复并实际复测搜索、空结果和导航。
- Word 表格保持表头与首条内容相连，禁止行内跨页；合并重复元数据，保留可编辑空白底稿。

代码独立复核的原始 4 项问题及后续成本沿袭问题均已整改；最终专项复核无未解决的实质问题。

## 本地验证证据

生成物不纳入 Git，位于仓库 `output/project-delivery-validation-20261011/`：

- `project/`：不可变原件、产物登记、有效集合、阶段成果索引。
- `engineering/`、`materials/`、`build_case.py`：实际本地测试及明确模拟的案例输入。
- `independent-business-review.*`、`independent-business-rereview.*`：初次发现及精确版本复核。
- `template-kit-v1/`、`delivery-template-kit-v0.1.zip`：可编辑 Office 模板。
- `office-v1-render/`、`office-v1-montage.png`、`office-readback.json`：17 份文档、25 页实际渲染与回读。
- `review-internal.html`、`review-customer.html`、`review-*.png`：实际界面和截图。
- `customer-discussion-pack/`、`simulation-confirmed-pack/`：本地准备包及哈希清单。

视觉检查以 Enterprise UI Design 规范及 UI_BLUEPRINT 为依据；未提供参考图片，不声称像素级还原。深色媒体查询未实测。界面是生成时快照，没有审批、编辑台账或多人协作写入功能。

## 后续验证

真实合同/客户身份与确认、真实音频转录、第三方联调、生产发布、安全/性能、迁移、培训、质保和完整项目验收均未完成。跨投标/售前/咨询套件尚无自动适配器。本地运行只支持单写者，目录名称不能替代访问控制。模板与 JSON 由 Agent 映射，未实现双向同步。

下一步适合选择一份真实合同及技术协议，先完成交接、启动会与调研计划，再按实际材料修订模板和契约。
