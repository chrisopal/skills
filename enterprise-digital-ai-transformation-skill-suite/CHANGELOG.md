# Changelog

## 1.2.0 — Runtime contract hardening

- 新增可机器校验的 Task Card 与独立 Quality Review Report 契约。
- 校验 Reviewer 独立性、Skill 依赖无环和 Workflow 依赖顺序。
- 在 Full、Rapid、AI-First 三套 Workflow 中显式声明逐阶段质量审查。
- 新增 WorkBuddy 专家运行边界，并将 `ppt-master-plus` 配置为可替换的首选渲染器。
- 强制 4A Package 与 Slide Content Pack 嵌入 Artifact Header，并收紧 PPT 输出格式与 4A 页面追溯字段。
- 明确具名咨询公司方法仅作为公开 Benchmark Source，不表示隶属、认证或专有 IP。

## 1.1.0 — Huawei 4A alignment

- 将华为 4A 明确为 Enterprise Architecture 的统一主干：BA、IA、AA、TA。
- 明确华为 4A 与 TOGAF Business/Data/Application/Technology domains 的映射，其中 TOGAF Data Architecture 映射为 IA Information Architecture。
- 明确 Operating Model 与 BA 的边界：Operating Model 是业务设计源模型，BA 是面向 IA/AA/TA 的正式架构视图，禁止维护两套不一致业务模型。
- 将 Integration、Security & Trust、AI & Knowledge、NFR、Governance 定义为横向视图，不新增额外“A”。
- 更新 As-Is/To-Be Enterprise Architecture Skills、AI Overlay、Gap、Roadmap、Storyline 和 Quality Review。
- 新增 `huawei-4a-enterprise-architecture.md`、`architecture-view.schema.json`、`architecture-traceability.schema.json` 与 `four-a-architecture-package.schema.json`。
- 更新 Transformation Model、Artifact Header、Initiative 和 Slide Content Pack Schema。
- 新增 4A 完整性与纵向追溯验收测试。
- 统一 As-Is/Target 4A 聚合产物命名，并补充 `as-is-4a-issue-and-debt-register` 与 `architecture-change-package-map` 交接契约。
- 新增 `architecture-framework-profile.schema.json`，把华为 4A 的范围、深度、生命周期、横向视图和追溯规则固化到 G0 项目契约。
