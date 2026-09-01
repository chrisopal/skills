# 证据、事实底座与 4A 资料分类

- **Skill name**: `evidence-factbase`
- **Version**: `1.1.0`
- **类型**: 可复用咨询 SOP

## 目的

把文档、访谈、数据、观察和外部研究转化为可追溯的 Evidence、Fact、Assumption 与 Glossary，并按战略、Operating Model、BA、IA、AA、TA 和 cross-cutting 对资料进行分类。

## 适用场景

- 项目启动、资料整理、访谈记录、数据核验和后续结论追溯

## 必需输入

- `source-documents`
- `interview-notes`
- `data-extracts`
- `observation-notes`
- `external-sources`

## 标准输出

- `evidence-register`
- `fact-register`
- `assumption-register`
- `glossary`
- `evidence-coverage-matrix`
- `4a-evidence-coverage-map`
- `conflict-and-verification-log`

## 执行步骤

1. 为每个来源记录来源类型、日期、Owner、范围、可信度和访问限制
2. 把原始内容拆分为 Evidence Item，区分事实、观点、假设、建议和外部基准
3. 对 Evidence 标注涉及的战略主题、价值流、能力、流程和 4A 架构域
4. 规范术语和别名，包括 IA/DA、系统名、组织名、数据对象和流程名
5. 检测访谈之间、访谈与数据之间、现状资料之间的冲突
6. 建立证据覆盖矩阵，识别 BA/IA/AA/TA 的空白和待验证项
7. 为后续 Skill 输出可直接引用的 Fact、Assumption 和 Evidence ID

## 质量规则

- 访谈观点不能自动升级为事实
- 外部最佳实践不能当成客户现状
- 同一证据可以关联多个域，但必须标明主主题
- 资料缺失必须显式呈现，不能用通用行业内容补造客户事实
- IA/DA 等别名需要归一但保留客户原词

## 依赖 Skill

- `engagement-scoping`

## Artifact 规则

- Evidence 不因后续结论变化而覆盖；只能新增版本或修正记录。
- Fact 必须引用 Evidence；Assumption 必须有验证计划。
- `4a-evidence-coverage-map` 至少按 BA/IA/AA/TA 展示资料覆盖、置信度和关键缺口。

## 失败与降级

- 来源无法验证时降低可信度并标记限制。
- 结构化数据与访谈冲突时保留双方，不静默选择。

## 最小验收

- 任一核心诊断结论都可回溯到 Evidence ID。
- 能指出四个 4A 域中哪个域资料最薄弱，以及需要补充什么。
- 通过 `consulting-quality-review` 对应检查。
