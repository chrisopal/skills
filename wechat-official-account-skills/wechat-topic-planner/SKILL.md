---
name: wechat-topic-planner
description: Use to build high-conversion WeChat topic systems for 智能体架构笔记, especially industrial AI, intelligent manufacturing, industrial software, enterprise digitalization, AI personal entrepreneurship, and humanoid robotics opportunities. Produces scored topic candidates, priority topics, detailed article briefs, series judgment, and weekly publishing schedule.
---

# WeChat Topic Planner

Use this skill when selecting or refining topics for the WeChat Official Account `智能体架构笔记`.

Read `../references/account-positioning.md`, `../references/growth-playbook.md`, and `../references/topic-pool-workflow.md` before planning topics.

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

1. Run the topic-pool gate:
   - read the local topic pool and, when Get笔记 is available, its `公众号选题库` master-index note
   - reconcile by stable `topic_id`; never infer `PUBLISHED` from a local file or a draft-save response
   - exclude semantic duplicates already in `DRAFTING`, `READY_LOCAL`, `DRAFT_SAVED`, or `PUBLISHED`
   - prefer existing `SELECTED` and P0 `BACKLOG` topics before inventing new candidates
2. Inspect recent drafts, published articles, operation plan, and user-provided inputs if available.
3. Generate up to 10 topic candidates. Reuse the existing `topic_id` for candidates already in the pool. Assign a new series-scoped ID only after duplicate screening when the topic is genuinely new.
4. For each topic, include one-sentence explanation and score it across five dimensions（五维评分）:
   - 目标读者价值，20 分
   - 专业壁垒，20 分
   - 传播潜力，20 分
   - 转化潜力，20 分
   - 可持续性，20 分
5. Sort or identify the strongest topics by total score and strategic fit.
6. Select the top 3 priority topics. Mark the recommended next article `SELECTED` in the local pool and sync the same record to Get笔记. Do not mark the other two selected unless they enter an actual schedule.
7. For each priority topic, produce a full article brief:
   - 推荐标题 3 个
   - 目标读者
   - 核心观点
   - 文章大纲
   - 可加入的案例或场景
   - 结尾转化方式
   - 建议故事开篇
   - 建议配图 2-4 张
8. Judge whether the topics should become a series.
9. Produce next-week publishing schedule.

## Topic Pool Contract

Every selected topic must carry:

- `topic_id`
- series
- current status
- target reader
- business line (`培训咨询` / `产品` / `双线`)
- conversion target
- evidence requirement

The near-term schedule should default to approximately `培训咨询 60% / 产品 40%`. Training and consulting topics primarily serve manufacturing digital departments; product topics primarily support the AI project-management platform, AI bid agent, and AI consulting platform.

## Proven Signals

When recent article signals exist, use them as hard steering input.

Current validated signal for this account:

- The strongest repeatable pattern is `真实公司 / 真实流程 / 真实结果 / 清晰业务代价`.
- 《怎么从 0 到 1 配一个设备知识库智能体》 was a recommendation hit, but it is one article-level signal. Do not treat `从 0 到 1` as a reusable breakout formula.
- The account should lean from `工业 AI 信息号` toward `AI 落地复盘与决策笔记`, not toward a stream of setup tutorials.
- Topic planning should help WeChat recognize stable industrial tags such as `设备`、`质量`、`维修`、`工单`、`MES`、`运维`, while varying the editorial question and article structure.
- Recommendation traffic matters more than old-subscriber opening for breakout pieces.
  A topic should be easy for WeChat to match to a specific reader/job/scenario, not merely interesting to existing followers.
- Search traffic is still weak, so durable series topics should include stable search phrases in titles and early paragraphs.
- `真实公司 / 真实产品 / 真实流程 / 真实价值` 的工业落地案例
  明显强于纯架构解释文
- 抽象技术话题仍然可写，但应默认服务于真实场景，不应连续主导排期
- 标题不应连续复用“为什么……不是……”“先别急着……”这类判断句式；要定期切到 `具体公司 / 具体结果 / 具体方法`
- 首页封面应优先简洁、单画面、强主题；不要把封面做成缩小版方案白皮书

Default content priority should therefore be:

1. 真实工业企业案例复盘：投入、流程变化、结果、边界
2. 阶段总结与横向比较：从一组案例中形成可争辩、可复述的判断
3. 失败复盘与客户决策：预算、验收、使用率、供应商选择、ROI
4. 服务于明确需求的方法与架构拆解

Do not let multiple consecutive abstract architecture pieces crowd out real landing stories.

## Topic Filters

Prefer topics that:

- name one concrete customer, role, industrial object, or workflow owner
- expose a decision the reader is currently facing: whether to invest, how to verify, why adoption failed, or which solution to choose
- contain at least one evidence anchor: a named company, a verifiable result, an actual workflow change, or an explicitly labeled unknown
- have practical value: decision questions, failure signals, acceptance criteria, comparison dimensions, or a reusable operating pattern
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

- stay at `工业 AI 趋势` or `Agent 趋势` without a specific factory role, system, device, or workflow
- only chase broad AI news that WeChat will classify into a generic AI content pool
- repeat `怎么从 0 到 1 配一个……` when any of the previous four main articles used that frame
- start with a fictionalized case or fill evidence gaps with plausible but unverified details
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

- 16-20: Has conflict, counterintuitive judgment, identity relevance, or a clear WeChat recommendation tag around one concrete industrial scenario.
- 11-15: Clear and useful but not strongly shareable.
- 0-10: Flat or internal-facing.

转化潜力：

- 16-20: Naturally leads to consulting, diagnosis, training, tool, community, solution, or cooperation.
- 11-15: Builds trust but conversion path is indirect.
- 0-10: Hard to connect to a business action.

可持续性：

- 16-20: Can extend into a series, cases, checklist, template, search keyword cluster, or follow-up debate.
- 11-15: Can produce 1-2 follow-ups.
- 0-10: One-off topic.

## Recommended Series Tracks

When no stronger user direction is provided, rotate among these series tracks:

- `项目复盘账本`: 一个真实项目为什么启动、改了哪段流程、拿到什么结果、哪些条件不能照抄。
- `老板的 AI 决策题`: 预算、ROI、验收、第二阶段投资、供应商选择和责任归属。
- `工业 AI 阶段结论`: 从近期一组案例中总结共性、分歧、失败边界和下一步变化。
- `落地后的第二天`: 系统上线以后，谁在用、谁不用、为什么绕开、怎样进入日常经营。
- `方法工具箱`: 少量架构、清单和实施方法，用来承接已经有明确需求的读者。

For each priority topic, ensure the brief includes:

- 客户对象：谁会因为这个问题停下来读
- 业务代价：不解决时正在损失什么
- 证据锚点：真实公司、结果数字、流程变化或明确的未知边界
- 决策价值：读完后能改变哪一个判断或动作
- 转化动作：与正文问题直接相关的案例征集、诊断清单、方案对照或咨询入口
- 内容类型：案例复盘 / 阶段总结 / 失败复盘 / 决策文 / 方法文

## Output Format

```markdown
## 输入假设

- 主题方向：
- 目标读者：
- 近期素材：
- 内容目标：
- 转化目标：

## 候选选题

| # | topic_id | 选题 | 当前状态 | 业务线 | 一句话说明 | 读者价值 | 专业壁垒 | 传播潜力 | 转化潜力 | 可持续性 | 总分 |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|---:|

## 优先写的 3 个选题

### 选题 1：

- topic_id：
- 当前状态：
- 业务线：
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
