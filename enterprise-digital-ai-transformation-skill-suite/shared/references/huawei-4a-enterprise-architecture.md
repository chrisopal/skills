# 华为 4A 企业架构建模规范

## 1. 定位

华为 4A 是本 Skill Suite 的 Enterprise Architecture 统一分类法和建模主干：

- `BA` — Business Architecture，业务架构；
- `IA` — Information Architecture，信息/数据架构；
- `AA` — Application Architecture，应用架构；
- `TA` — Technology Architecture，技术架构。

它与 TOGAF 的 Business、Data、Application、Technology 四个架构域一致。本套件采用华为命名，将 TOGAF Data Architecture 归入 IA，并把信息、数据、语义和知识统一建模。

## 2. 4A 不是四张独立图片

4A 的价值不在于分别生成四张图，而在于建立自战略到技术的连续追溯：

```text
战略目标 / KPI
  ↓
BA：价值流 → 能力 → 流程 → 业务服务 → 角色/治理
  ↓                 ↓
IA：信息域 → 业务对象 → 信息流 → 数据产品/知识资产
  ↓                 ↓
AA：应用服务 → 应用/数字产品 → 集成服务/AI服务
  ↓
TA：技术服务 → 平台 → 基础设施 → 运维与韧性
```

关系不是单向瀑布：BA 驱动 IA 和 AA，IA 与 AA 相互约束，TA 支撑 IA/AA；技术和数据约束也可能反馈到 BA 设计。

## 3. Operating Model 与 BA

### Operating Model 负责

- 企业如何创造价值；
- 价值流和端到端责任；
- 能力和能力归属；
- 流程、决策、规则和控制；
- 组织、角色、治理和协作；
- KPI、激励、人才和工作方式。

### BA 负责

- 将上述对象架构化、分层、编号和版本化；
- 定义业务服务和信息需求；
- 建立到 IA、AA、TA 的追溯；
- 支撑 As-Is/To-Be/Gap/Transition 比较；
- 进入企业架构治理和资产仓库。

### 复用规则

- 同一 Capability、Process、Role、KPI 只存在一个 Node ID；
- Operating Model 和 BA 通过 View 引用同一节点；
- 不允许两套能力地图、两套流程架构或两套 KPI 名称独立演进。

## 4. BA 建模规范

### 核心对象

- Objective、Value Driver、KPI；
- Customer/Partner、Product/Service、Channel；
- Value Chain、Value Stream、Journey；
- Capability、Business Service；
- Process、Activity、Decision、Business Rule、Control；
- Organization Unit、Role、RACI、Decision Right；
- Governance Mechanism、Policy、Risk；
- Business Information Requirement。

### 必要视图

- 战略—价值—KPI 关系图；
- 价值链/价值流图；
- 业务能力地图与热力图；
- L0-L3 流程架构；
- 组织/角色/治理/KPI 关系图；
- BA 到 IA/AA 的需求映射。

### 质量检查

- 能力不是部门名称；
- 流程必须体现端到端结果；
- 业务服务必须有消费者、Owner 和 SLA/Outcome；
- 每个关键能力至少关联一个流程、KPI 和信息需求；
- BA 设计必须回溯到战略和价值议程。

## 5. IA 建模规范

### 核心对象

- Information Domain / Data Domain；
- Business Object / Data Entity / Attribute；
- Conceptual/Logical Data Model；
- Master Data / Reference Data / Transaction Data；
- Information Flow / Data Lineage / Exchange Contract；
- Metric / Indicator / Semantic Definition；
- Metadata / Ontology / Knowledge Asset；
- Data Product / Analytical Dataset / Feature / Evaluation Set；
- Data Owner / Steward / Producer / Consumer；
- Data Standard / Quality Rule / Classification / Retention / Access Policy。

### 必要视图

- 信息域地图；
- 核心业务对象模型；
- 主数据与责任矩阵；
- 关键指标口径与血缘；
- 跨流程/应用信息流；
- 数据质量、标准、安全和生命周期视图；
- 数据产品、知识与 AI 数据准备度视图。

### 质量检查

- IA 不能退化为“数据中台建设清单”；
- 每个信息域必须有业务 Owner；
- 每个关键业务对象必须有权威来源、生命周期和质量规则；
- 指标必须定义口径、粒度、频率和责任；
- 数据共享必须说明用途、合法性、权限和消费方。

## 6. AA 建模规范

### 核心对象

- Application Domain；
- Application Capability；
- Application Service；
- Application / Digital Product / Platform；
- Module / Component；
- User Channel / Workspace；
- Workflow / Rule Service；
- API / Event / Message / Batch Interface；
- Integration Service；
- AI Application / Agent / Skill / Model Service Consumption；
- Application Owner / Lifecycle / Technical Debt。

### 必要视图

- 应用域与应用全景；
- Capability-to-Application 映射；
- Process-to-Application 映射；
- Business Object-to-Application CRUD/SoR 映射；
- 应用集成与交互图；
- 应用生命周期、利旧、整合、改造、新建和退役图；
- AI 应用、Agent 与传统应用协同图。

### 质量检查

- AA 不是系统名称堆叠；
- 每个应用服务必须支撑明确 BA 能力/流程并处理明确 IA 对象；
- 应用边界必须说明责任和耦合；
- 集成关系必须说明语义、方向、模式、频率和责任；
- 产品选型不得先于业务与架构需求。

## 7. TA 建模规范

### 核心对象

- Technology Service；
- Cloud / Data Center / Edge / Endpoint；
- Compute / Storage / Network；
- Database / Middleware / Container / Runtime；
- Data Platform / Integration Platform / AI Platform；
- Model Serving / Agent Runtime / Vector/Graph Engine；
- DevSecOps / MLOps / LLMOps；
- Observability / Logging / Trace / Operations；
- IAM / KMS / Security Platform；
- HA / DR / Backup / Capacity / Performance；
- Technology Standard / Product / Lifecycle。

### 必要视图

- 技术参考架构；
- 逻辑部署架构和物理部署架构；
- 云边端与网络拓扑；
- 平台服务目录；
- 环境、发布、运维和可观测性视图；
- 安全、容灾、备份和连续性视图；
- 技术标准、生命周期和风险视图。

### 质量检查

- TA 不是服务器和产品清单；
- 每个技术服务必须支撑 AA/IA 需求或 NFR；
- 必须给出容量、性能、可用性、安全、运维和成本要求；
- 目标技术必须有演进、迁移和退役路径；
- 关键产品选型必须记录 Architecture Decision。

## 8. 横向视图

### Integration & Interoperability

覆盖 BA 跨流程协同、IA 信息交换、AA 接口和事件、TA 集成平台与网络连接。

### Security & Trust

覆盖业务授权和职责分离、信息分级和隐私、应用身份/API 安全、基础设施和供应链安全、AI 风险与审计。

### AI & Knowledge

覆盖 BA 人机工作重构、IA 数据知识语义、AA Agent/Skill/AI 应用、TA AI 平台算力与工程化。

### NFR & Resilience

将性能、可用性、扩展性、连续性、可维护性、可观测性和成本要求分配到 4A 对象。

### Governance

管理原则、标准、例外、决策记录、合规检查、版本、Owner 和架构资产生命周期。

## 9. As-Is / To-Be / Gap / Transition 输出

### As-Is 4A Pack

1. As-Is BA Blueprint；
2. As-Is IA Blueprint；
3. As-Is AA Blueprint；
4. As-Is TA Blueprint；
5. 4A Traceability Matrix；
6. Cross-Cutting Views；
7. Issue、Risk、Debt 和 Evidence Overlay。

### Target 4A Pack

1. Target BA Blueprint；
2. Target IA Blueprint；
3. Target AA Blueprint；
4. Target TA Blueprint；
5. Target 4A Traceability Matrix；
6. Architecture Principles / Standards / Decisions；
7. Cross-Cutting Target Views；
8. Transition Architectures。

### 4A Gap Register

每个 Gap 至少记录：

- As-Is Node；
- To-Be Node；
- Architecture Domain；
- 业务影响；
- 严重度和风险；
- 前置依赖；
- 关闭该 Gap 的 Initiative；
- Evidence 与 Assumption。

## 10. AI 4A 检查矩阵

| 架构域 | 必答问题 |
|---|---|
| BA+AI | 哪些任务/决策由人、Agent、系统承担？责任、授权、KPI、异常和人工升级是什么？ |
| IA+AI | 需要哪些数据、知识、语义、评测集和反馈数据？其质量、权限、血缘和有效期如何治理？ |
| AA+AI | Agent、Skill、RAG、模型服务、工作台和传统系统如何分工与集成？ |
| TA+AI | 算力、模型服务、Runtime、MLOps/LLMOps、可观测性、安全、容量和成本如何满足要求？ |

## 11. 4A 追溯最低要求

随机选择一个目标 Application Service，必须能够回答：

1. 它支撑哪个 BA Capability / Process / Business Service？
2. 它创建、读取、更新或消费哪些 IA Business Object / Data Product？
3. 它依赖哪些 TA Technology Service / Platform？
4. 它关闭哪个 Gap、属于哪个 Initiative 和 Roadmap Wave？
5. 它的业务 KPI、架构指标、Evidence 和 Owner 是什么？

无法完整回答时，不得将目标架构升级为 `approved`。

## 12. 方法来源说明

- 华为公开材料将企业 4A 定义为 BA、IA、AA、TA，并将其用于数字化/智能化转型规划和架构治理。
- TOGAF 将 Enterprise Architecture 常用域划分为 Business、Data、Application、Technology。
- 本套件进行等价映射，并在 IA 中扩展信息、语义和知识内容，以适应数据与 AI 转型。
