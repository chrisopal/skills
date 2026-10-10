# 验收测试

## 测试 1：证据隔离

给定一条管理层访谈观点和一组相反运营数据，系统必须保留冲突，不得将访谈自动写成事实。

## 测试 2：跨模型追溯

随机选择一个 Initiative，必须能追溯到 Gap、目标能力/流程、现状问题、KPI 和 Evidence。

## 测试 3：As-Is/To-Be 分离

As-Is AA 中不得出现未部署目标平台；目标架构不得伪装成现状。

## 测试 4：Operating Model 与 BA 单一源

同一 Capability、Process 和 KPI 在 Operating Model 与 BA View 中必须使用相同 Node ID；若名称、层级或 Owner 不一致，测试失败。

## 测试 5：4A 纵向追溯

随机选择一个目标 Application Service，必须能追溯到：

- BA Capability / Process / Business Service；
- IA Business Object / Information Flow / Data Product；
- TA Technology Service / Platform；
- Gap、Initiative 和 Roadmap Wave。

G4只强制前三项以及Owner、KPI/证据关系；Gap/Initiative在G5补齐，Roadmap Wave在G6补齐。G6整体验收缺少任一关键关系失败；不因G5/G6尚未执行阻断G4。

## 测试 6：IA 不是平台清单

若 IA 仅列出数据湖、数据仓库、主数据平台等产品，而没有信息域、业务对象、标准、责任和信息流，则测试失败。

## 测试 7：AA 不是系统堆叠

若 AA 只有系统盒子，没有 Application Service、能力/流程映射、业务对象和集成语义，则测试失败。

## 测试 8：TA 不是设备清单

若 TA 只有云、服务器、网络和产品清单，没有 Technology Service、NFR、运维、韧性和支撑关系，则测试失败。

## 测试 9：路线图依赖

一个依赖主数据治理、集成平台和 AI Runtime 的 Agent 场景不得排在基础举措之前，除非明确作为隔离 POC 并记录风险。

## 测试 10：Transition Architecture

每个 Roadmap Wave 必须记录阶段性 BA/IA/AA/TA 状态，以及新建、改造、整合、迁移和退役动作。

## 测试 11：商业论证

同一效率收益不能同时完整计入流程优化 Initiative 和 AI Initiative；必须拆分归因或去重。

## 测试 12：PPT 不创造结论

Slide Content Pack 中的每个数字、架构组件和 Initiative 必须存在于已批准 Artifact。

## 测试 13：详细流程范围

快速诊断工作流不得自动把全企业流程下钻到 L5。

## 测试 14：AI 4A 完整性

对一个关键 Agent 场景，必须同时存在 BA+AI、IA+AI、AA+AI、TA+AI 设计，以及阈值、人工升级、审计和回滚。

## 测试 15：无方法配置的新项目可启动

给定初始project-context、空artifact-register/gate-decisions/open-issues、选定workflow以及完整范围任务输入，总控应能创建engagement-scoping任务。architecture-framework-profile由该任务生成并与章程接受G0审查；缺客户范围输入仍阻塞，不得补造。

## 测试 16：企业规划四级流程

enterprise-planning中每个L4必须具有唯一L3父节点，递归到L2/L1；层级含义固定为业务域/流程组/流程/子流程，禁止孤儿节点、跳级和循环。范围覆盖表必须列未调查/未设计项；每个已完成L4有责任、输入输出、KPI、信息对象和应用映射。G7不适用，不代表L5已完成。

## 测试 17：组织与绩效可用

抽查跨集团/分公司/工厂决策，只有一个最终负责角色且有升级路径。KPI公式、来源、基线/目标状态、周期、Owner、汇总和反向约束齐全；未知基线不得用无来源数字填充。

## 测试 18：投资复算与路线图约束

重算年度现金流、总投资、收益去重和三情景；不能把工时与现金节省重复相加。每个Wave有前置依赖、资源和阶段4A状态，预算/资源超限须给出明确决策而非继续宣称可执行。

## 测试 19：模拟不冒充审批

给定simulation项目，所有合成数字标假设/模拟来源，成果保持draft、人工Gate未批准；汇报只能走simulation-draft-artifacts入口并显式标注。模拟检查即使通过，也不得改为客户已验收、真实收益或独立批准。

## 测试 20：变更影响重审

改变一个KPI基线或目标应用边界，必须定位受影响源版本、投资、路线图和汇报，生成修订版与重审任务；旧批准版保留，不能把旧批准标记直接复制到新版。
