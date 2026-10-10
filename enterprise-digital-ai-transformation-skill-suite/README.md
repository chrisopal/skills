# Enterprise Digital & AI Transformation Skill Suite

> Version 1.4 — Enterprise planning with document and HTML review surfaces

一个面向企业数字化转型与 AI 转型咨询的多 Skill 操作系统骨架。

## 核心思想

- **方法论不是一个大 Prompt**：端到端咨询由主编排 Skill、专业子 Skill、统一 Artifact/Schemas、人工 Gate 和独立 QA 共同完成。
- **华为 4A 是企业架构主干**：所有 Enterprise Architecture 产物统一按 `BA 业务架构 / IA 信息/数据架构 / AA 应用架构 / TA 技术架构` 组织。
- **Operating Model 是 4A 的业务设计上游**：Operating Model 负责价值流、能力、流程、组织、治理、KPI、人才与工作方式；BA 将其转换为可连接 IA、AA、TA 的正式企业架构视图。
- **结构化中间产物是唯一真相源**：正式交付消费已审批的 Artifact，不从零生成结论；候选HTML和过程报告允许显示草案供审阅，不改变批准状态。
- **主 Skill 只编排**：`dtx-consulting-orchestrator` 不承担专业分析，避免上下文膨胀、结论漂移和不可测试。
- **证据优先**：事实、访谈观点、假设和建议必须分离；所有重要结论均可追溯到 Evidence ID。
- **AI 是贯穿 4A 的横向叠加层**：AI 同时进入 BA 的人机工作重构、IA 的数据知识语义、AA 的 Agent/Skill/应用服务、TA 的算力平台与工程治理。

## 体系构成

- 1 个主编排 Skill
- 16 个专业子 Skill
- 华为 4A 企业架构统一模型
- 统一咨询本体与 Artifact 数据契约
- Enterprise Planning、Full、Rapid、AI-First 四种工作流
- 阶段 Gate、质量审查与验收测试
- 面向外部 PPT 生成 Skill 的 `slide-content-pack` 交接协议
- 文档写作Skill、Enterprise UI Design HTML过程审阅和PPT确认页，独立于17个业务Skill
- 可机器校验的 Task Card、独立 Quality Review Report 与 WorkBuddy 运行配置

## 推荐入口

第一阶段企业规划选择 `shared/workflows/enterprise-planning.yaml`，先读
[规划交付约定](shared/references/phase-one-planning.md)和
[制造业工作底稿](shared/references/manufacturing-planning-toolkit.md)。
交付诊断、L1—L4流程、组织绩效、完整4A、投资和路线图，不包含G7实施级详细设计。
公开案例和模拟数据不能替代客户事实与人工审批。

1. 先阅读根目录 `AGENTS.md`。
2. 阅读 `shared/references/huawei-4a-enterprise-architecture.md`，确认 4A 的边界、对象和输出规范。
3. 使用 `examples/sample-project/project-context.yaml` 创建项目工作区。
4. 由 `dtx-consulting-orchestrator` 选择工作流并生成第一个任务卡。
5. 每次只执行一个任务卡，产物登记后调用 `consulting-quality-review`。
6. 分析产物全部通过 Gate 后，再调用 `transformation-storyline-builder`。
7. 将 `slide-content-pack.json` 交给独立 PPT 模板/渲染 Skill。

## 目录

- `.agents/skills/`：各 Skill 的 `SKILL.md` 与 `manifest.yaml`
- `shared/references/`：4A 方法论、公开来源登记、咨询本体、产物目录、Gate、PPT 交接
- `shared/schemas/`：核心 JSON Schema，包括 Architecture View 与 4A Traceability
- `shared/workflows/`：三种标准工作流
- `scripts/render_review_workbench.py`：显式输入文件生成离线HTML审阅页
- `shared/evaluation/`：全局质量规则与验收测试
- `tasks/`：推荐建设顺序
- `examples/`：项目上下文与示例 Artifact

WorkBuddy 本地专家挂载与发布边界见 `shared/references/workbuddy-runtime-profile.md`。默认 PPT 渲染器可配置为 `ppt-master-plus`，但渲染器不得改写已审批结论。

过程报告、L1—L4流程、4A、组织绩效、投资路线图和逐页PPT草稿的HTML阅读，见[文档与HTML审阅契约](shared/references/document-and-html-review-contract.md)。用户指定图片PPT时采用`consulting-ppt-image`；审阅UI采用`enterprise-ui-design`，内容/样式实际确认前不生成正式图片PPT。

流程图复用同仓库的`enterprise-diagrams`：层级图展示L1—L4包含关系，执行图只绘制底稿显式关系；HTML内直接显示SVG并保留JSON/SVG图源。独立安装可通过`--diagram-engine`指定该Skill的`diagram_svg.py`路径。

## 本地校验

```bash
pip install -r requirements-dev.txt
python scripts/validate_suite.py
```

校验覆盖 JSON/YAML 语法、JSON Schema、4A 示例、Skill/Manifest 契约以及 Workflow 引用。

规划底稿另行运行：

```bash
python scripts/validate_planning_pack.py /path/to/planning-pack.json
python -m unittest discover -s scripts -p 'test_*.py'
```

底稿约定见 [planning-pack-contract.md](shared/references/planning-pack-contract.md)。校验只证明引用和算术一致，不能证明现场事实、设计可行性或客户验收。
