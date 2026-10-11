# 第二批验证记录 · 2026-10-11

版本 0.2.0。第二批新增 7 个 Skills、7 份文档模板和 11 张 CSV 台账；总计 24 个 Skills、47 套模板（24 Markdown、23 CSV）。可编辑 Office 包为 24 个 DOCX 和一个含 23 张表的 XLSX。质保收尾与外部系统适配按原设计保留第三批。

## 分段结果

| 模块 | 本轮验证 |
|---|---|
| 实施方案 | 组件覆盖需求、决策状态及依据；方案目标与实际测量分开 |
| 页面/字段/权限 | 字段类型/长度/精度/单位/校验齐备；拒绝跨页权限和未知状态；逐页检查设计覆盖，缺项只能有依据地声明不适用 |
| 接口/迁移 | 本机 HTTP 资产服务实际调用；HTTP 200 但业务键错误仍拒绝；数量与业务键对账、同构建/环境核验、SQLite 原子迁移与备份恢复 |
| 工程工作包 | 绑定计划工作包、需求范围和设计版本；完成需精确构建与证据，计划状态不能冒充已实现 |
| 测试/缺陷/UAT | 未执行与通过分开；实际步骤/预期/结果/证据；关闭缺陷需本构建 passing 复测；模拟确认不能进入真实项目 |
| 上线/回滚 | 五项核心准入（备份/回滚/窗口/监控/授权）及同构建测试；未执行、执行成功与回滚恢复分开；失败后旧准入不能授权重试 |
| 培训/移交 | 逐类对象验证能力、责任人/手册/资产版本/接收证据；签到不等于掌握；模拟培训不能算真实用户受训 |
| 资源/成本/付款 | 16 项计算测试及运行集成：人员期间容量、逐工作包分配和剩余工时；未知估算保留缺口；外包不叠加内部人工；采购部分发生拆为发生额和承诺余额，付款不再加一次成本 |

全量 126 项 unittest 使用已有 Office 库的 Codex 内置 Python，全部通过、无跳过：runtime 55、software_delivery 30、economics 16、local_engineering 6、install 6、review 5、exports 4、suite 4。套件结构、24 个 Skill Creator quick_validate、24 个 YAML 元数据、Python 编译及 git diff --check 通过。未配置应用 lint/typecheck/LSP，不把编译当成静态类型检查。

## 实际演练与证据边界

可复用入口 `scripts/verify_phase_two.py` 在新输出目录实际运行 6 个本地工程测试，再保存来源、需求/计划及七类专项对象，总计 15 个当前产物、6 个来源快照。项目 purpose=simulation，validate 的 ok/effective_ok 为 true；本演练没有激活业务基线（effective=0），不补造审批历史。

实际动作包括 loopback HTTP 调用、SQLite 创建/保存回读、幂等冲突、未授权操作拒绝、主管审批状态变化、失败迁移原子保护、迁移前后数量/业务键核对和备份恢复。回读为迁移前 `{O1}`、迁移后 `{O1,O2}`、恢复后 `{O1}`，恢复结果与原始数据相同。构建引用绑定实际夹具代码 SHA-256，原始运行日志和操作结果分别登记；独立复核回读了来源快照与哈希。

release r1 仅模拟 `ready_to_execute=true`、`ready=false`；r2 记录本地 rolled_back，二者均 false。回滚恢复不算交付成功。UAT accepted、training competency pass、handover 接收均由 automated fixture/simulation 产生。没有真实用户培训、客户签署、生产执行或客户交付包。

页面规格在本轮案例中为概念设计，工程夹具只实现 Python/HTTP/SQLite 行为，没有交付该业务系统的可操作前端。静态审阅页用于阅读产物，不是业务系统界面。

## 独立复核与整改

独立代码/证据复核首次发现四项实质问题，增加可复现回归后修复，最终 APPROVE、无未解决 material issues：

- 嵌套 private_key/apiKey/refreshToken/Authorization 等凭据变体漏拦：统一归一化谓词，客户包拒绝、客户 HTML 过滤；自然语言及附件仍须人工复核。
- 旧通过与另一构建新失败同时存在仍绿：当前接口对账必须同环境、同构建且全部通过，历史执行保留在旧不可变修订。
- 付款条件修订中可消失或改挂：稳定 ID/成本归属跨修订保留，已付金额/状态纠错需要理由和证据。
- 某页面缺详细设计但被其他页面抵消：逐页核验字段、权限、状态；显式不适用理由不能替代业务合理性审查。

门槛核对字段、引用、覆盖和一致性，不认证证据真实性、审批人身份、设计合理性或远端制品存在。

## 模板、界面与安装

24 个 DOCX 的实际原生文本/表格和 23 张 XLSX 的全部表头逐项回读。CSV 保留机器字段名及空白输入行；Word 用中文分组表，每个第二批表最多四列，保持相邻表格分隔和表头/首条同行。修复拥挤英文表头、重复标题、继承边框和末页孤行后，本机现有 LibreOffice 实际渲染 24 文档、37 页；所有页有可读中文文本，7 个新增文档共 14 页逐页目视复核，并检查全套缩略图及代表页。23 张 Excel 用现有 artifact-tool 渲染，各表冻结 A2、筛选和蓝色表头回读一致。

审阅页沿用 Enterprise UI Design 企业蓝色；实际浏览器检查新增阶段导航、业务检索仅显示匹配 UI 对象、清空恢复 62 条记录、1280/390 两种视口无页面横向溢出，宽表在容器内滚动，无浏览器 error 日志。未提供参考图片，以规范检查，不声称像素还原；深色模式未在本轮实测。

安装前将已有 17 个目录逐文件比对已提交第一批，确认无用户修改；完整备份后升级并安装新增 7 个。24 个安装目录与源码逐文件哈希一致，安装入口重跑全部 unchanged；安装版 runtime 实际校验本轮演练通过。安装版仍采用单写者文件，目录名不构成访问控制。刷新 Skills 列表或新建会话后可发现新技能。

## 本地证据

生成物保留在仓库 `output/project-delivery-phase-two-validation-20261011/`，不纳入 Git：

- `full-tests-final.log`、`case-final/`：126 项原始日志、分段报告、6 项工程日志、操作回读与登记快照。
- `template-kit-delivery/`、`project-delivery-templates-v0.2.0.zip`：最终可编辑 Office 模板。
- `office-delivery-render/`：24 个 PDF、37 页 PNG、readback.json 和新增文档逐页拼图。
- `spreadsheet-render/`：23 张表实际渲染和表头/空行/冻结/筛选回读。
- `ui-desktop.png`、`ui-mobile.png`：实际审阅界面截图。
- `installation.json`、`installed-first-batch-backup/`：安装回执与原 17 个技能备份。

最终 HTML 位于 `output/project-delivery-validation-20261011/review-phase-two-final.html`，复用既有本地审阅服务。初始导出/演练保留用于追溯，以上 delivery/final 目录为本轮最终证据。

## 未验证范围

真实合同和授权、实际客户 UAT、外部系统认证/联调、生产上线、真实数据迁移、真实人员培训、安全/性能、质保收尾和完整客户项目验收尚未验证。Microsoft Word/Excel 原生交互及其他机器字体/分页需按交付环境复验。模板与 JSON 由 Agent 映射，没有自动双向同步；Excel 是空白台账，不带财务公式或审批系统。未新增依赖、后台服务或自动生产动作。
