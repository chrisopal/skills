# AGENTS.md

## 工作方式

1. 先读取 `project-context.yaml`、`artifact-register.yaml`、适用 workflow、`shared/references/huawei-4a-enterprise-architecture.md` 和目标 Skill 的 `SKILL.md`。
2. 一次只执行一个任务卡；任务卡必须指定单一主 Skill、输入 Artifact、输出 Artifact 和验收标准。
3. 先进行只读分析，再生成或修改 Artifact；不得在缺少输入时静默补造客户事实。
4. 所有核心产物必须使用 Artifact Header，并记录 `generated_by`、版本、状态、上游 Artifact、Evidence ID、假设和 Reviewer。
5. 事实、观点、假设、建议分开；`assumed` 不得被下游当作 `validated`。
6. Skill 是可复用业务 SOP；Tool 是可审计动作；Artifact 是可持续维护成果。
7. Skill 不直接访问任意数据库或路径；只通过项目允许的工具、连接器和受控文件读取数据。
8. 主编排 Skill 只做状态、依赖、任务和 Gate 管理，不做专业分析。
9. `transformation-storyline-builder` 只编排已审批内容；PPT 渲染 Skill 不得改变数据与结论。
10. 每个阶段结束必须运行 `consulting-quality-review`，通过人工 Gate 后才能进入下一阶段。

## 4A 强制规则

1. Enterprise Architecture 的标准域固定为：`BA`、`IA`、`AA`、`TA`。
2. `BA` = Business Architecture；`IA` = Information Architecture；`AA` = Application Architecture；`TA` = Technology Architecture。
3. TOGAF 的 Data Architecture 在本套件中映射到华为 IA；文件名可保留兼容别名，但正式产物统一使用 `information-architecture`。
4. Operating Model 不与 BA 重复建模：同一价值流、能力、流程、组织、治理和 KPI 节点只维护一份，BA 作为这些节点面向 4A 追溯的架构视图。
5. Integration、Security & Trust、AI & Knowledge、NFR、Governance 是贯穿 4A 的横向视图，不得包装成第 5 个或第 6 个“A”。
6. 每个 AA 组件必须能够追溯到 BA 能力/流程/业务服务和 IA 信息对象；每个 TA 组件必须能够追溯到其支撑的 AA/IA 需求。
7. As-Is、To-Be 和 Transition 的 4A 模型必须分离；未经批准的目标组件不得进入 As-Is。
8. 目标架构必须给出利旧、改造、新建、整合、迁移和退役策略。
9. AI 设计必须明确落入 BA+AI、IA+AI、AA+AI、TA+AI 的具体变化，并配置跨域评测、安全、审计和人工兜底。

## 命名与版本

- Skill 目录名、Manifest 名称和调用名称必须一致，使用小写、数字和连字符。
- Artifact ID 使用：`{project}-{domain}-{type}-{sequence}`。
- 架构域字段使用：`BA | IA | AA | TA | cross-cutting | none`。
- 每次修改创建新版本，禁止覆盖已批准版本。
- 运行记录保存 `skill_name`、`skill_version`、输入版本、输出版本和 Gate 结果。

## 禁止事项

- 禁止一个 Skill 同时完成诊断、蓝图、路线图和 PPT。
- 禁止以部门列表替代能力地图，以系统列表替代应用架构，以模块名替代转型 Initiative。
- 禁止只画 4A 四张图而不建立跨域追溯关系。
- 禁止把“数据平台”当作 IA，把“系统清单”当作 AA，把“服务器清单”当作 TA。
- 禁止为填满模板而制造数字、案例、系统、流程或成熟度评分。
- 禁止全企业流程无选择地下钻到 L5；只对优先场景详细设计。
- 禁止将 AI 用例与数据、流程、组织、评测、风险和人工兜底分离。
