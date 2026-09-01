# 数字化与 AI 转型咨询 Skill Suite 总体规格

> Version 1.2 — Huawei 4A Enterprise Architecture aligned, runtime contracts hardened

## 1. 定位

本套件将企业数字化与 AI 转型咨询抽象为一条可重复、可审计、可分工、可测试的 Strategy-to-Execution 流水线：

`战略与价值议程`
→ `证据与 As-Is 诊断`
→ `To-Be Operating Model`
→ `华为 4A 企业架构（BA/IA/AA/TA）`
→ `AI 横向叠加`
→ `Gap 与 Initiative`
→ `Business Case 与投资组合`
→ `Transition Architecture 与 Roadmap`
→ `重点场景详细设计`
→ `Storyline 与 PPT 渲染`

它不是替代咨询顾问，而是把可标准化部分沉淀为 SOP、数据契约、分析步骤、模板、质量规则和知识包，让顾问把精力集中在关键判断、客户共识与取舍上。

## 2. 方法论总框架

本套件将不同方法放在清晰层级中，而不是混合成一个概念：

1. **战略与价值管理**：明确战略目标、价值驱动、业务结果和 KPI。
2. **Operating Model**：设计企业如何创造价值和运行，包括价值流、能力、流程、组织、治理、决策权、KPI、人才和工作方式。
3. **Enterprise Architecture**：采用华为 4A 作为统一主干，把 Operating Model 转换为 BA、IA、AA、TA 四类可治理架构资产。
4. **TOGAF/ADM**：提供 As-Is、To-Be、Gap、Transition Architecture、Roadmap、治理和迭代方法。
5. **AI Operating Model**：将 AI 作为贯穿战略、Operating Model 和 4A 的横向重构力量。
6. **咨询表达**：把经过批准的 Artifact 编排为管理层决策故事线和 PPT 内容包。

## 2.1 G0 Architecture Framework Profile

每个项目在范围阶段必须生成 `architecture-framework-profile`，把方法论选择从文字说明变成机器可校验的项目契约。至少定义：

- `canonical_model: huawei-4a`；
- BA、IA、AA、TA 各域的范围、最低深度、必须视图和 Owner；
- IA 与 TOGAF Data Architecture 的映射及客户展示别名；
- Integration、Security & Trust、AI & Knowledge、NFR & Resilience、Architecture Governance 横向视图；
- As-Is、To-Be、Transition Architecture 的覆盖要求；
- Operating Model 与 BA 共用 Node ID 的规则；
- AA→BA、AA→IA、TA→AA/IA 和 Objective→Roadmap 的最低追溯阈值；
- 允许裁剪的内容、例外机制和 G0 审批状态。

此 Profile 由 `engagement-scoping` 生成，由 Orchestrator、Enterprise Architecture Skills 和 Quality Review 共同消费，防止不同阶段采用不同架构口径。

## 2.2 运行契约与独立审查

方法论一致并不等于运行可审计。每次执行必须同时满足：

- Orchestrator 只生成一个符合 `task-card.schema.json` 的任务卡，明确唯一主 Skill、输入版本、预期输出、验收条件、Gate 和 Reviewer；
- 三种 Workflow 均在每个 Stage 结束后调用 `consulting-quality-review`；Reviewer 不得与候选 Artifact 的生成者相同；
- 质量报告符合 `quality-review-report.schema.json`，`pass` 不得带阻断项，`conditional-pass/fail` 必须给出 Owner 和可验证的返工动作；
- Skill 依赖必须无环，Workflow 中同一 Stage 内按声明顺序满足依赖；
- WorkBuddy、CLI 或其他运行时的“任务完成”状态不能替代 Artifact 回读和 Gate 证据。
- 4A Package、Slide Content Pack 等核心聚合产物必须嵌入可独立通过 `artifact-header.schema.json` 校验的 `artifact_header`。

## 3. Operating Model 与 4A 的关系

Operating Model 与 BA 高度相关，但不应重复建设两套业务模型。

- **Operating Model 是管理设计视角**：回答企业未来如何运行、由谁负责、如何协同、如何衡量和激励。
- **BA 是企业架构视角**：把价值流、能力、流程、业务服务、组织、治理、KPI 和信息需求结构化，并向 IA、AA、TA 建立可追溯关系。
- 同一业务对象只维护一次，通过不同 View 展示；不得分别维护一套“Operating Model 能力地图”和一套内容不一致的“BA 能力地图”。
- `to-be-operating-model` 先完成业务设计，`to-be-enterprise-architecture` 再将其正式化为 BA，并向 IA/AA/TA 逐层展开。

## 4. 华为 4A 企业架构主干

### 4.1 BA — Business Architecture，业务架构

回答“企业为了实现战略，需要具备什么业务能力，以什么方式创造价值和运营”。核心对象：

- 战略目标、价值驱动与 KPI；
- 客户、产品/服务、渠道与生态；
- 价值链、价值流与客户旅程；
- 业务能力、能力分层和能力 Owner；
- L0-L5 流程、业务服务、决策和控制；
- 组织、角色、职责、决策权和治理机制；
- 业务规则、政策、风险和业务连续性要求；
- 对信息、应用和技术的业务需求。

### 4.2 IA — Information Architecture，信息/数据架构

回答“业务运行需要什么信息，信息如何定义、产生、流动、共享、治理和消费”。核心对象：

- 信息域、数据域和业务对象；
- 概念/逻辑数据模型、主数据和参考数据；
- 信息流、数据血缘、数据交换和生命周期；
- 指标口径、语义、元数据、Ontology 和知识资产；
- 数据 Owner/Steward、标准、质量、安全分级和权限；
- 数据产品、分析主题和 AI 数据/知识准备度。

本套件将 TOGAF 的 Data Architecture 统一映射到 IA；“数据架构”可作为兼容术语，但正式 Artifact 使用 Information Architecture。

### 4.3 AA — Application Architecture，应用架构

回答“哪些应用服务和数字产品支撑业务能力、流程和信息处理”。核心对象：

- 应用域、业务应用、数字产品和应用服务；
- 应用能力、功能边界、共享平台和公共组件；
- 用户渠道、工作台、流程/规则能力和交互关系；
- API、事件、消息、批处理和集成服务；
- 应用与能力、流程、业务对象的映射；
- 应用 Owner、生命周期、技术债、利旧/整合/退役策略；
- AI 应用、Agent、Skill、Tool Connector 和模型服务消费关系。

### 4.4 TA — Technology Architecture，技术架构

回答“应用、信息和 AI 能力运行在什么技术底座上，并如何满足性能、安全和韧性要求”。核心对象：

- 云、边、端、数据中心、计算、存储和网络；
- 数据库、中间件、容器、集成与数据平台；
- AI 算力、模型训练/推理、模型网关与 Agent Runtime；
- DevSecOps、MLOps/LLMOps、发布、配置和环境；
- 监控、日志、Trace、可观测性、运维和 FinOps；
- 高可用、容灾、备份、容量、性能和技术标准；
- 技术产品生命周期、国产化/云化约束和技术风险。

## 5. 横向视图

以下内容贯穿 BA、IA、AA、TA，但不新增新的“A”：

- **Integration & Interoperability**：跨流程、跨应用、跨数据和跨技术的连接关系；
- **Security & Trust**：业务控制、数据安全、应用安全、基础设施安全、隐私、审计和 AI 安全；
- **AI & Knowledge**：人机协同、知识语义、AI 服务、模型平台、评测与治理；
- **NFR & Resilience**：性能、可用性、扩展性、连续性、可维护性和成本；
- **Architecture Governance**：原则、标准、例外、评审、合规检查和架构资产运营。

## 6. 统一咨询本体与 4A 追溯

核心追溯主链：

`Objective / Value Driver / KPI`
→ `BA: Value Stream / Capability / Process / Business Service / Role`
→ `IA: Information Domain / Business Object / Information Flow / Data Product`
→ `AA: Application Service / Application / Integration Service / AI Service`
→ `TA: Technology Service / Platform / Infrastructure / Runtime`
→ `Issue / Root Cause`
→ `Gap`
→ `Initiative / Work Package`
→ `Cost / Benefit`
→ `Transition Architecture / Roadmap Wave / Milestone`
→ `Slide / Deliverable`

BA 同时驱动 IA 与 AA；IA 与 AA 之间存在双向约束；TA 支撑 IA、AA 及其非功能要求。规划顺序可以自上而下，但模型必须允许反馈迭代。

所有图表和结论均应是同一 Transformation Graph 的不同投影，而不是互不相干的文档。

## 7. As-Is、To-Be、Gap 与 Transition Architecture

### As-Is

必须按 4A 建立现状：

- As-Is BA；
- As-Is IA；
- As-Is AA；
- As-Is TA；
- 4A Cross-Domain Traceability；
- 技术债、数据问题、流程断点、控制风险和能力成熟度。

### To-Be

必须按 4A 建立目标：

- Target BA；
- Target IA；
- Target AA；
- Target TA；
- 横向安全、集成、AI、NFR 和治理视图；
- Architecture Principles 与 Standards；
- 关键架构决策和备选方案。

### Gap

Gap 不能只按“系统缺失”识别，必须覆盖：

- BA：能力、流程、组织、治理、KPI、规则；
- IA：信息对象、标准、质量、责任、语义、共享；
- AA：应用服务、边界、集成、生命周期和技术债；
- TA：平台、基础设施、工程能力、韧性和标准；
- Cross-cutting：安全、AI、NFR、治理。

### Transition Architecture

三年 Roadmap 不只是项目清单，而是从 As-Is 4A 逐步演进到 To-Be 4A 的一组过渡状态。每个 Wave 必须说明：

- 该阶段的 BA/IA/AA/TA 目标状态；
- 新建、改造、整合、迁移、利旧和退役动作；
- 前置依赖、关键风险、资源和决策 Gate；
- 业务 KPI 与架构合规指标。

## 8. Operating Model 设计维度

1. Purpose 与 Value Agenda；
2. 客户、产品/服务与生态；
3. 价值链、价值流与旅程；
4. 业务能力与能力归属；
5. 流程、决策、规则与控制；
6. 组织、角色、责任与决策权；
7. 治理与协作机制；
8. KPI、激励与价值实现；
9. 人才、技能与工作方式；
10. 对 IA、AA、TA 和 AI 的业务需求。

## 9. AI 融入 4A

### BA + AI

- AI 场景、任务和决策机会；
- Human-Agent-System 流程；
- 岗位增强、责任边界、授权和人工升级；
- AI 业务 KPI、风险政策和价值归属。

### IA + AI

- 训练/推理/检索数据与知识资产；
- 多模态数据、Ontology、知识图谱、向量和语义层；
- 数据质量、血缘、权限、知识有效期和引用溯源；
- 评测集、反馈数据和模型风险数据。

### AA + AI

- AI 应用、Copilot、Agent、Skill 和 Workflow；
- Model Gateway、RAG、Memory、Tool Connector 和人工工作台；
- 传统系统与 Agent 的服务边界、API 和事件协同；
- 业务规则、评测服务、Trace 和人工接管入口。

### TA + AI

- 训练、微调、推理和向量/图计算基础设施；
- 模型服务、Agent Runtime、MLOps/LLMOps；
- AI 可观测性、成本、容量、弹性和性能；
- 模型、数据、Prompt、Tool 和供应链安全。

## 10. 流程层级

- L0：企业价值链；
- L1：价值流/业务域；
- L2：端到端流程；
- L3：流程组/阶段；
- L4：子流程；
- L5：活动、任务、决策、规则、异常和控制。

全企业规划通常建立到 L3；仅对优先灯塔场景或实施范围下钻到 L4-L5。

## 11. 项目阶段与人工 Gate

- G0 范围批准：章程、边界、交付物、关键问题清晰；
- G1 证据就绪：核心主题有足够证据，事实/假设分离；
- G2 As-Is 验证：Operating Model 与 As-Is 4A 经业务/IT Owner 验证；
- G3 诊断与北极星批准：核心问题、根因、价值议程达成共识；
- G4 To-Be 批准：目标 Operating Model 与 BA/IA/AA/TA 纵向一致，横向视图完整；
- G5 Portfolio 批准：Gap、Initiative、预算、收益和优先级可解释；
- G6 Roadmap 批准：Transition Architecture、依赖、资源、治理和价值实现可执行；
- G7 详细设计批准：重点场景可进入产品/项目实施；
- G8 Deck Content 批准：故事线、证据、4A 蓝图和管理决策请求清晰。

## 12. 标准化边界

可高度标准化：项目步骤、资料清单、访谈问题、Artifact 结构、4A 建模对象、映射规则、检查清单、成熟度判据、估算模型、Storyline 模式、图表规格和质量门禁。

必须保留专家判断：战略取舍、业务模式选择、组织政治、目标架构边界、业务与信息归属、应用拆分/整合、技术路线、风险接受、投资优先级、变革可行性和管理层共识。

## 13. PPT Skill 交接

咨询套件输出 `slide-content-pack.json`。默认推荐 `ppt-master-plus` 作为可替换的 PPT 渲染器；PPT Skill 只负责：

- 品牌模板与版式；
- 页面布局与视觉层级；
- 图标、图形、字体和配色；
- 按 `chart_spec` / `diagram_spec` 生成可编辑图形；
- 输出 PPTX/PDF/图片版。

典型 4A 页面包括：

- 4A 总体关系图；
- As-Is/To-Be BA；
- As-Is/To-Be IA；
- As-Is/To-Be AA；
- As-Is/To-Be TA；
- 4A 追溯矩阵；
- Gap 热力图；
- Transition Architecture 与 Roadmap。

PPT Skill 不得修改核心结论、数字、4A 架构对象、路线图顺序、Evidence 引用和审批状态。

## 14. WorkBuddy 专家运行

WorkBuddy 专家应挂载全部专业 Skill，并以 `dtx-consulting-orchestrator` 负责状态与任务路由，以 `consulting-quality-review` 负责独立审查。专家的能力说明可以引用 TOGAF、华为 4A 和公开咨询方法，但不得声称与华为、Accenture、McKinsey 或 Gartner 存在雇佣、认证或官方代表关系。

本地专家优先通过相对目录与软链接挂载源 Skill，保持版本同步；发布时必须复制为版本锁定的实体目录并重新校验。完整边界见 `shared/references/workbuddy-runtime-profile.md`。
