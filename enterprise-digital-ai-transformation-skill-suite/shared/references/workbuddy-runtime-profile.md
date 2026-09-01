# WorkBuddy Expert Runtime Profile

## 目的

把本 Skill Suite 作为一个可审计的 WorkBuddy 行业顾问专家能力包运行，同时保持源 Skill、项目 Artifact 和 PPT 渲染器之间的边界。

## 推荐专家结构

- Expert 类型：`agent`；
- Category：`12-IndustryConsultant`；
- 主编排能力：`dtx-consulting-orchestrator`；
- 专业能力：本仓库 `.agents/skills/` 下全部 17 个 Skill；
- 独立质量审查：`consulting-quality-review`；
- PPT 渲染器：`ppt-master-plus`，仅消费通过 G8 的 `slide-content-pack`。

## Skill 挂载规则

1. WorkBuddy `plugin.json.skills[]` 必须逐项指向包含 `SKILL.md` 的相对目录。
2. 本地运行优先使用指向源 Skill 的软链接，避免复制后版本漂移；发布或跨机器打包时再复制并锁定版本。
3. Agent frontmatter 可列出全部 Skill 名称用于路由，但不得把所有 Skill 同时当作一个任务执行。
4. 每次只允许一个主 Skill 修改核心 Artifact；`consulting-quality-review` 以独立角色在阶段结束后审查。
5. `ppt-master-plus` 不得读取未批准草稿并将其包装为正式结论。

## 运行状态与证据

- 每次运行记录 `skill_name`、`skill_version`、输入 Artifact 版本、输出 Artifact 版本、Gate 和 Reviewer。
- 任务卡使用 `task-card.schema.json`；质量报告使用 `quality-review-report.schema.json`。
- WorkBuddy 卡片可见、脚本退出码或 PPT 文件存在都不是业务完成证明；需要 Artifact 回读、结构校验和 Gate 决策。

## 发布边界

- 本地软链接专家包只能视为当前机器可用。
- 分享专家包前必须把软链接转为版本锁定的实体目录，并重新运行 WorkBuddy `validate_expert.py` 和打包测试。
- `ppt-master-plus` 体积较大时不得无审查复制进仓库；本地专家通过软链接使用，PPT 交付物作为 Artifact 保持不入库，除非用户明确要求。
