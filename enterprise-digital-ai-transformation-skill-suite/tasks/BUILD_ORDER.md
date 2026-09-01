# 推荐建设顺序

## Phase 0：先建共同底座与 4A Contract

1. `architecture-framework-profile.schema.json`；
2. `artifact-header.schema.json`；
3. `evidence-item.schema.json`；
4. `transformation-model.schema.json`；
5. `architecture-view.schema.json`；
6. `architecture-traceability.schema.json`；
7. `four-a-architecture-package.schema.json`；
8. Artifact Register、Evidence Register、Architecture Repository 和项目状态机；
9. `consulting-quality-review`；
10. `dtx-consulting-orchestrator`。

没有这一步，不要先写大量分析 Prompt；否则各 Skill 会输出不同术语、不同 4A 边界和不同格式。

## Phase 1：MVP 咨询闭环

1. `engagement-scoping`；
2. `evidence-factbase`；
3. `strategy-value-agenda`；
4. `as-is-operating-model`；
5. `as-is-enterprise-architecture`：先完成 As-Is BA/IA/AA/TA 与追溯；
6. `issue-root-cause-opportunity`；
7. `to-be-operating-model`；
8. `to-be-enterprise-architecture`：完成 Target BA/IA/AA/TA 与 Transition Architecture；
9. `gap-initiative-design`：按 4A 识别 Gap；
10. `roadmap-governance-change`；
11. `transformation-storyline-builder`。

目标：完成从资料到诊断、Operating Model、4A 蓝图、Gap、路线图和 PPT Content Pack 的最小闭环。

## Phase 2：增强商业决策

1. `external-benchmark-maturity`；
2. `portfolio-business-case`；
3. 预算/收益公式、资源容量和依赖算法；
4. 行业 Operating Model 与 4A Reference Pack；
5. 4A Architecture Pattern、Standard 和 Decision Library。

## Phase 3：AI 与实施级下钻

1. `ai-transformation-overlay`；
2. `scenario-process-detail-design`；
3. BA+AI / IA+AI / AA+AI / TA+AI 模板；
4. Human-Agent-System 模板；
5. AI 评测、Trace、治理和回滚模板；
6. 与产品 Spec、Codex 任务卡和 Figma/PPT Skill 的适配器。

## 开发纪律

- 每个任务卡只实现一个 Skill 或一个共享 Contract。
- 先由只读 Architect 检查边界与依赖，再实现、测试和 Reviewer 审查。
- 每个 4A Skill 至少有 2 个正向示例、2 个反例、1 个跨域追溯测试和 1 个冲突证据测试。
