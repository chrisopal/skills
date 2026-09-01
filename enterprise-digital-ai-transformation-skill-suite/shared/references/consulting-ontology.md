# Transformation Consulting Ontology

## 1. 核心实体

### 战略与价值

- `Objective`：战略目标；
- `ValueDriver`：价值驱动因素；
- `KPI`：结果与过程指标；
- `ArchitecturePrinciple`：指导架构取舍的原则；
- `ArchitectureDecision`：关键架构决策、备选方案和依据。

### BA — 业务架构

- `ValueChain` / `ValueStream` / `Journey`；
- `Capability`：企业能够稳定完成某类工作的能力；
- `BusinessService`：向内部或外部消费者提供可定义结果的业务服务；
- `Process` / `Activity`：实现能力和结果的流程层级；
- `Decision` / `BusinessRule` / `Control`；
- `OrganizationUnit` / `Role` / `Responsibility`；
- `GovernanceMechanism` / `Policy` / `Risk`；
- `BusinessInformationRequirement`。

### IA — 信息/数据架构

- `InformationDomain` / `DataDomain`；
- `BusinessObject` / `DataEntity` / `Attribute`；
- `InformationFlow` / `DataLineage`；
- `MasterData` / `ReferenceData`；
- `MetricDefinition` / `SemanticDefinition`；
- `DataProduct` / `AnalyticalDataset` / `EvaluationDataset`；
- `MetadataAsset` / `Ontology` / `KnowledgeAsset`；
- `DataStandard` / `DataQualityRule` / `DataPolicy`；
- `DataOwner` / `DataSteward`。

### AA — 应用架构

- `ApplicationDomain` / `ApplicationCapability`；
- `ApplicationService` / `Application` / `DigitalProduct`；
- `ApplicationComponent` / `WorkflowService` / `RuleService`；
- `IntegrationService` / `API` / `Event` / `Message`；
- `AIApplication` / `Agent` / `Skill` / `ToolConnector`；
- `ApplicationOwner` / `ApplicationLifecycle` / `TechnicalDebt`。

### TA — 技术架构

- `TechnologyService` / `TechnologyComponent` / `Platform`；
- `Compute` / `Storage` / `Network` / `Cloud` / `Edge`；
- `Database` / `Middleware` / `Runtime`；
- `DataPlatform` / `IntegrationPlatform` / `AIPlatform`；
- `ModelService` / `AgentRuntime` / `VectorEngine` / `GraphEngine`；
- `DevSecOpsCapability` / `MLOpsCapability` / `ObservabilityCapability`；
- `SecurityControl` / `ResilienceControl` / `TechnologyStandard`。

### 转型与实施

- `Issue` / `RootCause`：问题与根因；
- `Gap`：As-Is 与 To-Be 的差异；
- `Initiative` / `WorkPackage`：关闭 Gap 的转型举措；
- `Cost` / `Benefit`：成本与收益；
- `TransitionArchitecture`：阶段性 4A 目标状态；
- `RoadmapWave` / `Milestone`：时间与里程碑；
- `Evidence` / `Assumption`：证据与假设；
- `Slide` / `Deliverable`：表达与交付物。

## 2. Architecture Domain 标签

每个架构节点可带：

- `BA`；
- `IA`；
- `AA`；
- `TA`；
- `cross-cutting`；
- `none`。

同一实体可以出现在多个 View，但必须只有一个主域和一个唯一 Node ID。

## 3. 关键关系

### 战略到 BA

- Objective `driven_by` ValueDriver；
- Objective `measured_by` KPI；
- ValueStream `requires` Capability；
- Capability `exposed_as` BusinessService；
- Capability `realized_by` Process；
- Process `performed_by` Role；
- Process `governed_by` GovernanceMechanism；
- Process `requires_information` BusinessObject。

### BA 到 IA

- BusinessService `creates_or_consumes` BusinessObject；
- Process `creates_reads_updates_deletes` BusinessObject；
- BusinessObject `belongs_to` InformationDomain；
- InformationFlow `connects` Process/Application/DataProduct；
- DataProduct `serves` Capability/Decision/KPI；
- KnowledgeAsset `supports` Process/Decision/Agent。

### BA/IA 到 AA

- ApplicationService `supports` Capability/BusinessService/Process；
- ApplicationService `manages` BusinessObject；
- Application `realizes` ApplicationService；
- IntegrationService `exchanges` BusinessObject；
- Agent/Skill `augments_or_automates` Process/Decision/Role；
- AIApplication `uses` DataProduct/KnowledgeAsset/ModelService。

### AA/IA 到 TA

- ApplicationService `runs_on` TechnologyService；
- Application `deployed_on` Platform/Compute；
- DataProduct `hosted_on` DataPlatform；
- ModelService `runs_on` AIPlatform；
- TechnologyService `satisfies` NFR/SecurityControl。

### 转型链

- Issue `affects` 任意业务或架构实体；
- RootCause `causes` Issue；
- Gap `compares` As-Is Entity 与 To-Be Entity；
- Initiative `closes` Gap；
- Initiative `enables` Objective/KPI；
- Initiative `changes` BA/IA/AA/TA Entity；
- Initiative `depends_on` Initiative/WorkPackage；
- Benefit `measured_by` KPI；
- TransitionArchitecture `contains` BA/IA/AA/TA Target State；
- RoadmapWave `implements` TransitionArchitecture；
- Slide `communicates` Artifact，并 `cites` Evidence。

## 4. 状态

所有 Artifact 与核心实体建议使用：

- `draft`：生成但未验证；
- `assumed`：基于显式假设；
- `validated`：经业务/IT Owner 核验；
- `approved`：经项目 Gate 批准；
- `superseded`：被新版本替代；
- `rejected`：不采用但保留历史。
