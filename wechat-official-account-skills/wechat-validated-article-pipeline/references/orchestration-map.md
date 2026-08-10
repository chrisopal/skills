# 公众号 Skill 编排表

## 阶段映射

| 阶段 | 调用的 Skill / 能力 | 输入 | 交接物 | 通过条件 |
|---|---|---|---|---|
| 选题身份 | `wechat-topic-planner` | 八项输入、近期内容、选题池 | `topic_id`、三个标题、文章 brief | 已查重，状态 `SELECTED` |
| 证据收集 | 当前 Skill + 真实工具 | 场景步骤、环境、验收标准 | case bundle、截图、产物、回读 | `--phase evidence` PASS |
| 正文 | `wechat-article-writer` | brief、材料、证据、限制 | Markdown、摘要、配图 brief | 状态 `DRAFTING` |
| 人味审稿 | `wechat-article-human-tone-reviewer` | Markdown、近期文章 | 人味结论、修改项 | `通过` |
| 配图排版 | `wechat-article-layout` + `imagegen` | Markdown、真实截图、配图 brief | 封面、正文图、HTML | 移动端和视觉 QA 通过 |
| 最终审核 | `wechat-article-reviewer` | Markdown、HTML、证据包 | 最终审稿结论 | `通过`，状态 `READY_LOCAL` |
| 草稿保存 | 微信草稿 helper + `wechat-daily-pipeline` 的保存约定 | HTML、封面、图片、已有 `media_id` | API 结果、`draft/get` | `--phase draft` PASS |
| 运营记录 | `wechat-account-operator` | 审计包、回读结果 | topic pool / Get笔记更新 | 状态 `DRAFT_SAVED` |

## 交接规则

### 选题规划 → 真实验证

传递：

- `topic_id`
- 目标读者和读者动作
- 核心观点
- 文章要证明的关键判断
- 真实场景和证据要求

不要传递已经写死的成功结论。

### 真实验证 → 写作

传递：

- 已验证材料清单
- 步骤、动作、结果和证据 ID
- 验收结果
- 原始证据与公开图路径
- 失败、限制和未验证边界

写作 Skill 只能从这些材料中产生事实性陈述。

### 写作 → 配图

传递：

- Markdown
- 封面提示词
- 每张正文图的用途、位置、类型、节点和主信息
- 哪些图必须使用真实截图
- 账号视觉系统

### 审核 → 草稿

传递：

- 终版 Markdown 与 HTML
- 封面与正文图路径
- 人味审稿和最终审稿结论
- 隐私/错误/链接/本地路径检查结果
- 已有 `media_id` 或新建理由

## 最终审计包

```markdown
## 微信公众号实证草稿

- 选题 ID：
- 标题：
- 摘要：
- 目标读者：
- 核心观点：
- 真实场景：
- 验收结论：
- 仍有限制：
- Markdown：
- HTML：
- 封面：
- 正文图：
- Case bundle：
- 人味审稿：
- 最终审稿：
- 草稿 media_id：
- draft/get：
- 选题池状态：
- Get笔记同步：

## 发布边界

已保存草稿，未发布。
```

任何完成证据缺失时，删除最后一句，改写为当前真实状态和下一阻塞项。
