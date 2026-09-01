# 方法论映射

本套件不是照搬单一咨询公司的框架，而是抽取可组合的共同结构。华为 4A 是 Enterprise Architecture 的统一内容主干，TOGAF 提供生命周期与治理方法，Operating Model 提供业务设计。

| 外部方法/思想 | 在本套件中的吸收方式 | 边界与裁剪 |
|---|---|---|
| 华为 4A 企业架构 | 采用 BA 业务架构、IA 信息/数据架构、AA 应用架构、TA 技术架构作为所有 As-Is/To-Be/Gap/Transition 架构产物的标准分类；强调 4A 联动和“一张蓝图绘到底” | 不绑定华为具体产品；不把 4A 简化为四张展示图 |
| TOGAF / 企业架构 | ADM 式迭代、Architecture Repository、As-Is/To-Be/Gap、Transition Architecture、Roadmap、治理与迁移；Business/Data/Application/Technology 域映射到 BA/IA/AA/TA | 不要求客户完整使用全部术语和文档；按项目裁剪 |
| Operating Model | 战略到绩效的桥梁；价值、流程、能力、组织、治理、人才、KPI 和工作方式是一个系统；作为 BA 的业务源模型 | 不把组织架构调整当作全部 Operating Model；不与 BA 重复维护节点 |
| 华为数字化/智能化实践 | 以业务价值和场景为起点，把流程、组织、数据、IT 和 AI 一体化；AI 分别落入 BA+AI、IA+AI、AA+AI、TA+AI | 不将特定企业内部组织和产品术语固化为通用 Schema |
| 咨询项目管理 | 结论先行、假设驱动、证据验证、Issue Tree、Workplan、SteerCo Gate | 不允许 Storyline 先于事实底座并反向制造结论 |
| 产品与敏捷交付 | Initiative → Epic/Work Package → MVP → Acceptance Criteria；持续反馈 | 不把战略咨询缩减为产品 Backlog |
| AI Operating Model | Human-Agent-System 工作重构、知识/数据/模型/Agent 平台、评测、Trace、人工升级和治理 | 不把 AI 仅等同于聊天机器人、模型选型或独立用例清单 |

## 咨询公司方法的使用边界

专家可以吸收 Accenture、McKinsey、Gartner 等机构公开材料中的 Operating Model、组织协同、能力建设、成熟度评估和转型治理模式，但这些内容只作为可追溯的 `Benchmark Source` 或设计备选：

- 不复制或声称持有其专有方法、付费数据库或内部模板；
- 不把外部观点写成客户现状事实；
- 不以公司品牌替代明确的分析步骤、Evidence、假设和 Gate；
- 任何采用的外部模式都要说明来源、适用条件、局限与本项目裁剪。

## 4A 与 TOGAF 映射

| 本套件/华为 4A | TOGAF 对应域 | 说明 |
|---|---|---|
| BA — Business Architecture | Business Architecture | 基本一致；本套件通过 Operating Model 扩展组织、治理、KPI、人才和工作方式设计 |
| IA — Information Architecture | Data Architecture | IA 比狭义 Data Architecture 更宽，包含信息、数据、语义、指标、知识、Ontology 和数据产品 |
| AA — Application Architecture | Application Architecture | 基本一致；集成服务作为 AA 的重要组成，同时形成横向 Integration View |
| TA — Technology Architecture | Technology Architecture | 基本一致；扩展云边端、数据平台、AI 平台、DevSecOps、MLOps/LLMOps 和可观测性 |

## Operating Model 与 4A 的衔接

```text
战略与价值议程
  ↓
To-Be Operating Model
  ↓ formalize
BA 业务架构
  ↓ information & digital enablement requirements
IA 信息架构 + AA 应用架构
  ↓ platform & NFR realization
TA 技术架构
  ↓
Transition Architecture / Roadmap / Governance
```
