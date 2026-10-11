# 商机全流程 Skill 实施与验收计划

用户已确认 2026-10-11 的分析方案。本计划直接执行，不再设置重复审批。

## 目标与架构决策

把现有分析入口扩展为同一商机从线索到签单的持续工作流：一个薄总控、六个业务 Skill（包含现有分析入口）、单一共享运行层。保留 Python 标准库、SQLite、HTML/Markdown；不新增依赖或 CRM 服务。

ADR-001（Accepted）：业务 Skill 按任务而非销售阶段拆分。总控恢复和调度，子 Skill 产出事实及变更建议，共享运行层校验、事务保存并回读。相比一个大入口需要维护交接契约，但避免复制存储和阶段规则。暂不建设完整 CRM。

ADR-002（Accepted）：材料推断只产生建议阶段；正式阶段由带证据的业务变更推进。中标为里程碑，合同签署为单独阶段；暂停、丢单、取消分别记录。历史仅展示真实迁移，不按阶段序号推造完成记录。

ADR-003（Accepted）：复用已存在的 presales-orchestrator 和投标套件；对接成果 ID、版本、文件及反馈，不复制方案/PPT 引擎。外部能力缺失时保留明确的交接包。

约束：保留 unrelated WIP；生成示例、SQLite、截图和运行日志仅留 output/ 或临时目录，不提交。所有外部客户发送、报价授权和实际签署仍依具体业务授权执行；本工具登记事实，不替人签约。不把评分换算称为校准预测，不把测试通过称为客户验收。

## 工作分工与接口

- 运行层：src/opportunity_skill/ 的生命周期、存储、增量分析、CLI、阶段/评估修复；相关 schema、workflow、运行层回归测试。保留 analyze/query/detail。
- 展示层：renderer.py、display/、UI 回归测试；只读取结构化数据，不负责业务写入。
- 主执行：总控及五个新增业务 Skill、契约与安装/验证工具、集成样例、文档和 STATUS.md、完整验收与提交推送。

详情保留现有结构，并在顶层增加 lifecycle 对象：current_stage_id、suggested_stage_id、status、revision、facts、history、actions、artifacts、contracts。history 只含真实的 from_stage/to_stage、时间、操作者、理由和证据；actions 包含负责人、期限、结果与完成证据。展示对旧数据作待确认回退，不伪造历史。

## UI Blueprint

- Keep：企灵品牌、客户/联系人/决策链、维度评分及雷达、风险、原件、证据、HTML/Markdown 输出。
- Adapt：语义 Token 映射为 enterprise-ui-design 蓝色/灰阶、浅深主题、小圆角、可见焦点和窄屏布局。详情首屏显示当前阶段、建议阶段、负责人、下一行动及阻塞；阶段与行动记录优先于重复评分。
- Retire：静态 span 假操作、默认序号完成勾选、赢单后接丢单的线性轨迹、重复定义和错误的“成交意向”指标名。
- 新列表为默认查询视图，看板仍可选；静态 HTML 仅提供真实导航、材料链接和原生 details 展开，不增设没有运行入口的写操作。

## 实施与验收

- [x] 先运行现有验证脚本，记录基线；用回归用例复现未来报价、PO 模板、未知回答、重复分析问题。
- [x] 实现同一商机增量更新、稳定 ID、输入幂等、版本冲突、事实证据、行动结果、真实阶段历史和签单门槛；一次变更事务保存。
- [x] 更新蓝色企业展示，保留证据与评分；列表、详情、看板、客户、风险、行动视图支持浅深主题和窄屏。
- [x] 编写 opportunity-orchestrator、pursuit、solution-validation、commercial、negotiation、closeout；保留 opportunity-analysis-skill。提供共享运行入口和契约，安装时不覆盖不同内容。
- [x] 在隔离目录用模拟原始材料执行新增交流→同一商机更新→行动完成→方案反馈→报价版本→谈判结果→签署文件→已签单回读。
- [x] 负向验收：未知回答、不存在/错属证据、重复请求、冲突版本、缺签署材料、材料改动、暂停恢复、失败事务不改变正式状态。
- [x] 运行旧验证、全部新增 unittest、Skill 入口/套件检查、Python 语法和 diff 检查；无独立 lint/typecheck/build 配置时记录实际使用的对应检查。
- [x] 实际浏览器检查浅深、桌面与390px，涵盖有数据、长内容、空状态、键盘焦点、材料导航；每轮记录视觉 verdict，未验证项明确说明。
- [x] 独立审查实质变更，修复问题后只复跑受影响检查及最终完整门槛。
- [x] 更新 STATUS.md 和验收报告；仅暂存本任务源码/文档，按 Lore 提交、推送配置分支并核对远端 SHA。

验收证据与限制见[实施验收](2026-10-11-opportunity-lifecycle-validation.md)。
