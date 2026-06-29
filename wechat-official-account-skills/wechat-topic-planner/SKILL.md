---
name: wechat-topic-planner
description: Use to build high-conversion WeChat topic systems for 智能体架构笔记, especially industrial AI, intelligent manufacturing, industrial software, enterprise digitalization, AI personal entrepreneurship, and humanoid robotics opportunities. Produces scored topic candidates, priority topics, detailed article briefs, series judgment, and weekly publishing schedule.
---

# WeChat Topic Planner

Use this skill when selecting or refining topics for the WeChat Official Account `智能体架构笔记`.

Read `../references/account-positioning.md` before planning topics.

## Mission

Do not merely generate titles. Build a long-term topic system that can:

- sustain weekly publishing
- build personal influence
- show industrial and enterprise expertise
- attract manufacturing, industrial software, and digitalization readers
- create conversion opportunities for consulting, cooperation, community, course, tool, or service products

The account focuses on:

- 工业 AI
- 智能制造
- 工业软件
- 企业数字化
- AI 个人创业
- 人形机器人产业机会

“智能体” is the entry point, not the narrow boundary. Topics may cover large models, Agent, workflow, RAG, MCP, harness engineering, agent skill, tools, memory, evaluation, permissions, industrial software transformation, enterprise adoption, and AI-enabled business models.

## Input Fields

When inputs are provided, use them directly:

- 主题方向
- 目标读者
- 近期素材
- 内容目标
- 转化目标

If some fields are missing, infer reasonable defaults from account positioning and state the assumptions. Do not block topic generation unless the missing field changes the business direction materially.

## Workflow

1. Inspect recent drafts, published articles, operation plan, and user-provided inputs if available.
2. Generate 10 topic candidates.
3. For each topic, include one-sentence explanation and score it across five dimensions（五维评分）:
   - 目标读者价值，20 分
   - 专业壁垒，20 分
   - 传播潜力，20 分
   - 转化潜力，20 分
   - 可持续性，20 分
4. Sort or identify the strongest topics by total score and strategic fit.
5. Select the top 3 priority topics.
6. For each priority topic, produce a full article brief:
   - 推荐标题 3 个
   - 目标读者
   - 核心观点
   - 文章大纲
   - 可加入的案例或场景
   - 结尾转化方式
   - 建议故事开篇
   - 建议配图 2-4 张
7. Judge whether the topics should become a series.
8. Produce next-week publishing schedule.

## Proven Signals

When recent article signals exist, use them as hard steering input.

Current validated signal for this account:

- `真实公司 / 真实产品 / 真实流程 / 真实价值` 的工业落地案例
  明显强于纯架构解释文
- 抽象技术话题仍然可写，但应默认服务于真实场景，不应连续主导排期
- 标题不应连续复用“为什么……不是……”“先别急着……”这类判断句式；要定期切到 `具体公司 / 具体结果 / 具体方法`
- 首页封面应优先简洁、单画面、强主题；不要把封面做成缩小版方案白皮书

Default content priority should therefore be:

1. 真实工业企业案例
2. 真实 AI 产品或方案进入企业流程的案例
3. 服务于真实场景的技术解释

Do not let multiple consecutive abstract architecture pieces crowd out real landing stories.

## Topic Filters

Prefer topics that:

- start from a real company, real workflow, real industrial conflict, or real project tension when possible
- connect AI technology to real industrial or manufacturing workflows
- expose a management, sales, delivery, ROI, data, or organizational conflict
- help manufacturing bosses or industrial software leaders make a decision
- contain a concrete business scenario, failure review, or reusable pattern
- show professional barriers through process knowledge, system knowledge, delivery logic, and commercial judgment
- create natural conversion into consulting, cooperation, community, course, tool, or service product
- are valuable even if a specific AI tool becomes outdated
- have conflict, judgment, and forwarding value
- 容易长出 `案例名 + 结果数字 + 流程对象` 的标题抓手

Avoid topics that:

- stay at architecture, tooling, or concept level without a real workflow owner
- only summarize product releases
- only compare tools without a business implication
- promise AI replacement without discussing workflow and responsibility
- require facts that cannot be verified
- read like a generic AI tools recommendation account
- stay at “AI empowers manufacturing” slogan level
- use industrial terms without showing actual business process understanding
- have no conversion path or no clear reader owner

## Scoring Rubric

Score each dimension out of 20.

目标读者价值：

- 16-20: Directly solves a real decision, sales, delivery, or transformation pain.
- 11-15: Useful but not urgent.
- 0-10: Mostly curiosity or generic knowledge.

专业壁垒：

- 16-20: Requires industrial process, industrial software, manufacturing management, or AI architecture understanding.
- 11-15: Has some domain insight but easy to imitate.
- 0-10: Generic AI commentary.

传播潜力：

- 16-20: Has conflict, counterintuitive judgment, or identity relevance that readers may share.
- 11-15: Clear and useful but not strongly shareable.
- 0-10: Flat or internal-facing.

转化潜力：

- 16-20: Naturally leads to consulting, diagnosis, training, tool, community, solution, or cooperation.
- 11-15: Builds trust but conversion path is indirect.
- 0-10: Hard to connect to a business action.

可持续性：

- 16-20: Can extend into a series, cases, checklist, template, or follow-up debate.
- 11-15: Can produce 1-2 follow-ups.
- 0-10: One-off topic.

## Output Format

```markdown
## 输入假设

- 主题方向：
- 目标读者：
- 近期素材：
- 内容目标：
- 转化目标：

## 候选选题

| # | 选题 | 一句话说明 | 读者价值 | 专业壁垒 | 传播潜力 | 转化潜力 | 可持续性 | 总分 |
|---|---|---|---:|---:|---:|---:|---:|---:|

## 优先写的 3 个选题

### 选题 1：

- 推荐标题：
  1.
  2.
  3.
- 目标读者：
- 核心观点：
- 文章大纲：
- 可加入的案例或场景：
- 结尾转化方式：
- 建议故事开篇：
- 建议配图：

### 选题 2：

同上。

### 选题 3：

同上。

## 系列化判断

- 是否适合做成系列：
- 系列名称建议：
- 系列逻辑：
- 可延展篇目：

## 下一周内容排期

| 日期/节奏 | 内容类型 | 选题 | 目标 | 转化动作 |
|---|---|---|---|---|
```

## Quality Bar

Final output must:

- be specific to industrial AI, intelligent manufacturing, industrial software, enterprise digitalization, AI personal entrepreneurship, or humanoid robotics
- avoid generic AI tool recommendations
- prefer real companies, real AI products, real workflows, and real value evidence over abstract framing
- include industrial scenarios, business insight, and conversion logic
- show conflict, judgment, and forwarding value
- make the top 3 briefs immediately usable by `wechat-article-writer`
