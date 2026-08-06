---
name: wechat-article-writer
description: Use when drafting WeChat articles for 智能体架构笔记 that need to turn AI architecture topics into enterprise-relevant judgments, especially when jargon-heavy topics must be rewritten around business conflict, workflow reality, and reader decisions.
---

# WeChat Article Writer

Use this skill to write or rewrite article drafts for `智能体架构笔记`.

Read `../references/account-positioning.md`, `../references/growth-playbook.md`, `../references/topic-pool-workflow.md`, and `../references/human-writing-playbook.md` before writing.

## Topic Identity Gate

Before drafting:

1. Resolve the article to an existing `topic_id` in the topic pool by ID, title, case name, and core question.
2. If it is a genuinely new user-directed topic, add one record only after duplicate screening.
3. Set the selected record to `DRAFTING` and record the Markdown path when the file is created.
4. When the local article is complete, set it to `READY_LOCAL`. The writer must not set `DRAFT_SAVED` or `PUBLISHED`; those states require external evidence handled by the pipeline/operator.
5. Sync the same record to the Get笔记 master index when available. Never create another master-index note.

## Writing Goal

Write like a thoughtful practitioner talking to a specific reader.

The article should help readers:

- first understand a real enterprise problem or workflow conflict
- then understand the AI concept or architecture decision behind it
- judge whether it applies to their enterprise scenario
- learn from success cases, failure reviews, or implementation patterns

Current operating preference for this account:

- prefer `真实公司 / 真实产品 / 真实流程 / 真实价值`
- tell the story through one concrete workflow, not through platform abstraction first
- explain the technical path only after the reader can already see the business scene
- if the user references a known living business writer, translate that into high-level writing traits rather than direct imitation
- when writing main industrial AI pieces, default to `AI 落地复盘与决策笔记`, not `工业 AI 信息号` or a setup-tutorial stream
- prefer `真实公司 / 真实流程 / 真实结果 / 清晰业务代价`; use `从 0 到 1` only for occasional method pieces, never as the default title engine

## Business-First Rule

Default to `企业问题优先，技术解释后置`.

That means:

1. Do not lead with jargon if the reader can first be pulled in by a business problem.
2. The first 3 paragraphs should answer:
   - 谁在什么流程里遇到了什么麻烦
   - 为什么这件事现在值得看
   - 这篇文章准备给出什么判断
3. Technical terms such as Agent, RAG, MCP, harness, context engineering, tool gateway, approval, trace, or state should appear only after the reader already understands the practical tension.
4. Every technical mechanism must be translated back into:
   - 哪个业务流程会受影响
   - 哪个角色会更轻松或更危险
   - 为什么企业需要为它付成本

Use jargon-first openings only when the term itself already carries strong mainstream meaning for this account and the title still contains a reader-facing conflict.

## Material Gate / 材料门槛

Before outlining a nonfiction long article, list at least five concrete pieces of material internally and record where each came from. A usable item is a verified company action, product capability, number, workflow step, role decision, failure, limitation, quote, or user-provided observation.

Five neighboring abstract opinions do not become five materials merely because they are expanded into purpose, impact, risk, and future implications. Invented “typical factory scenes,” common-sense speculation, decorative detail, and metaphors cannot carry article length.

If the material is insufficient:

1. research available public sources, prioritizing primary sources
2. ask up to three concentrated questions when the missing material is private experience
3. narrow the question or shorten the article if the gap remains

Never repeat an idea to hit a target word count. Article length must follow evidence density.

## Paragraph Progression Gate / 段落推进

Every prose paragraph must add at least one new fact, action, example, distinction, limitation, consequence, or supported judgment. A paraphrase of the previous paragraph is not progress.

During revision, label each paragraph internally with:

- the material that supports it
- the new information it contributes

Merge or delete paragraphs that can only be described as “further explanation.” Let the previous paragraph's object or consequence lead into the next paragraph instead of relying on insight signposts.

Run a compression test on long drafts. If removing one third leaves the facts, actions, and judgment unchanged, keep the shorter version.

## Title Strategy

Prefer `企业判断型标题` over `术语解释型标题`.

Priority order:

1. reader problem or management judgment
2. concrete workflow or business risk
3. then the underlying technical mechanism

Good title shapes:

- `最近这批工业 AI 项目，我只追问三件事：谁在用、怎么验收、为什么继续投`
- `POC 已经跑通，为什么老板还是不愿意批第二笔预算`
- `设备知识库上线半年，维修工为什么还在微信群里问老师傅`
- `同样叫 AI 质检，客户为什么愿意为一种方案付钱，另一种只看演示`
- `上市周期少了 10 天，Dos Pinos 先交给 AI 的为什么是包装校对`
- `10 周上线，90% 自动通过：……怎么做`
- `某家公司把……交给 AI，结果怎样`
- `一个具体流程，怎么从手工变成自动通过`

Avoid by default:

- `工业 AI 未来趋势如何`
- `智能体将重塑制造业`
- `企业为什么要拥抱 Agent`
- `X 技术为什么正在取代 Y 技术`
- `A、B、C、D 到底是什么关系`
- `为什么 X 突然成了热点`
- 连续使用 `怎么从 0 到 1 配一个……智能体`
- 连续多篇都复用同一套“为什么……不是……”或“先别急着……”句式
- 标题只有观点，没有公司、结果、流程对象这三个抓手里的任何一个

These can still be used when the article is explicitly trend-oriented, but only if the title also gives the reader a clear enterprise payoff.

When recent operational feedback suggests low first-screen clickthrough, prefer this title fallback order:

1. 具体结果数字
2. 具体公司或场景
3. 具体流程对象
4. 最后才是抽象判断

For WeChat recommendation and search, make the concrete workflow visible in the title whenever natural:

- `设备智能体`
- `设备知识库`
- `设备维修智能体`
- `设备点检智能体`
- `故障诊断智能体`
- `工单处理智能体`
- `MES / 工单 / 点检 / 运维 / 售后`

Do not stuff keywords. One clear, natural phrase is better than a title that reads like SEO.

## Case-First and Customer-Impact Rule

For case reviews and customer-attraction pieces, do not open with a definition, a generic factory role, or a made-up scene.

Open from one of these evidence-backed moments:

- a real cost, delay, quality escape, stoppage, or approval conflict
- a named company's decision and the workflow it changed
- a verified before/after result
- a sharp contradiction visible across several researched cases

Keep the case in the article after the opening. Explain who approved the change, what existing work was altered, how the result was measured, and what remains unknown. A case that appears only in the first two paragraphs is decoration, not the article's spine.

Customer attraction comes from recognition, not sales language. Make the reader see their own budget risk, adoption problem, acceptance gap, or supplier-choice problem before offering any method.

## Voice / 语气

Use Chinese by default.

Preferred tone:

- conversational but not loose
- direct, human, and opinionated
- practical, with enough technical precision
- more “我想跟你把这件事说清楚” than “本文将系统阐述”

For this account, a strong business-column tone usually means:

- open from one observed fact, case, result, or decision moment, not from a term definition
- explain like you are talking across a meeting table, not reading a report
- let the material determine the order; do not force every article through the same `问题 -> 原因 -> 机制 -> 动作` ladder
- vary section length and paragraph rhythm according to the evidence
- close where the argument naturally ends; do not manufacture a slogan for forwarding
- keep the structure sharp, but let the wording sound like something a real operator would actually say in conversation

If the user mentions a living writer such as 刘润:

- do not imitate that writer's exact wording, rhythm, or signature formulas
- do extract the broad qualities the user likely wants: business-first framing, conversational clarity, layered explanation, and strong takeaways

Do not prescribe reusable sentence shapes. Build sentences from the case's concrete nouns and actions: who approved, who reworked, what stopped, what changed, what was measured, and what remains unknown.

Avoid:

- consulting-report tone
- slogan-heavy paragraphs
- excessive acronyms without explanation
- long future topic lists
- exaggerated claims such as “彻底颠覆” or “一文讲透”
- 评论腔判断句，比如 `这条线很值得盯`、`更值得关注的是`、`这个信号是`、`下一步该补的是`

When writing a business explainer piece, preserve the explanatory structure but make the wording more natural and more speakable.

Avoid sentence frames that sound like detached commentary instead of a practitioner talking to a peer:

- `真正麻烦的地方是`
- `说白了`
- `你真要往前走，先看`
- `企业最后买单的，不是……而是……`
- `这条线很值得盯`
- `更值得关注的是`
- `这个信号是`
- `下一步该补的是`
- `真正值得企业学的是`

## Anti-Slop Writing Rules

When the draft is structurally correct but still reads like AI, fix the language before adding more content.

Hard requirements:

- Prefer short, spoken Chinese sentences over layered judgment sentences.
- Prefer one clear point per paragraph; do not stack `判断 + 转折 + 抽象总结` into one long sentence.
- Start from a concrete role or workflow scene whenever possible.
- Replace abstract summary words with visible work objects such as `报表`、`工单`、`审批`、`口径`、`日志`、`表结构`、`SQL`。
- Keep some friction in the prose. It is acceptable to say a thing is awkward, risky, or easy to误判.
- Let transitions feel like a business explainer guiding the reader through the issue, not a whitepaper enumerating sections.

High-frequency phrases to avoid repeating across the same article or across recent articles:

- `真正麻烦的地方是`
- `真正值得企业学的 / 抄的`
- `真正值钱的`
- `下一步该补的`
- `不是……而是……`
- `说白了`
- `这件事很容易被忽略`
- `最后买单的，不是……而是……`

These phrases are not banned forever. But once one of them appears, do not keep reusing the same formula as the article's main engine.

Do not stop at literal phrase matching. Check the rhetorical action: did the sentence invent a simplistic reader belief only to overturn it and make the next claim sound deeper? This includes variants such as `你以为 A，其实 B`、`看似 A，实则 B`、`A 不重要，重要的是 B`, and the same move split across two sentences.

Rewrite by stating the actual judgment directly and placing its evidence and limits nearby. Keep a change-of-mind passage only when the article has real material showing what the author first believed and what evidence changed that belief.

Preferred rewrite direction:

- from `抽象判断` to `具体场景`
- from `长句总括` to `短句直说`
- from `概念先行` to `先把谁在干什么讲清楚`
- from `正确但平` to `带一点取舍和边界`
- from `术语解释文` to `商业问题拆解文`

Sentence-level checks before handing off:

- If a sentence contains more than one of `真正 / 更值得 / 不是…而是 / 下一步 / 说白了`, rewrite it.
- If a paragraph can be split into two shorter spoken paragraphs, split it.
- If a judgment sentence could apply to almost any AI article, rewrite it until it belongs to this one.
- If the draft keeps explaining what the company `意味着什么`, add one line about what the team actually has to do differently.
- If a section has no crisp takeaway line, add one. The reader should be able to retell that section after one pass.
- If a closing judgment sounds like a commentator speaking from outside the work, rewrite it until it sounds like an operator giving a practical recommendation.
- If three or more neighboring clauses use the same grammatical frame, keep two and rewrite or delete the third.
- If sentences and paragraphs are nearly uniform in length, restore natural long-short variation according to information density.
- If conjunctions such as `因为 / 所以 / 但是 / 同时 / 此外` appear every few sentences, remove the ones that Chinese word order and causality can already carry.
- If a sentence nominalizes the work as `进行了优化 / 实现了提升`, restore the role, action, object, and measurable consequence.

## Article Structure

Default structure:

1. Opening: 80-150 words, name the reader, the workflow, and the business tension.
2. What is really going wrong: explain the practical consequence and common wrong fixes.
3. Mechanism: explain the technical idea in plain language after the reader already cares.
4. Enterprise reality: explain what changes in real workflows, roles, permissions, and maintenance.
5. Case or pattern: success, failure, or a reusable adoption pattern.
6. Closing: one grounded judgment that readers can repeat or forward.

When writing an industrial landing or real-company case, prefer this stronger structure:

1. 故事开篇：谁在什么流程里卡住了，为什么它值得老板/负责人现在看
2. 痛点展开：这条流程过去为什么慢、贵、乱、难复制
3. 方案切入：真实公司或真实产品到底改了哪一段
4. 技术路径：数据、模型、工作流、系统集成、人工确认分别怎么接
5. 业务价值：效率、质量、交付、成本、人员复制、响应速度拿到了什么变化
6. 洞见收尾：别的企业可以学什么，哪些条件不具备时别照抄

When writing a stage summary, use this structure:

1. 观察范围：这次总结基于哪些时间、行业或案例，不夸大样本
2. 共性发现：反复出现了什么，给出案例证据
3. 分歧与反例：哪些项目走了不同路径，为什么
4. 客户决策：老板、数字化负责人或供应商应该改变哪一个判断
5. 下一阶段：哪些问题值得继续跟踪，哪些结论仍未确认

When the editorial mix explicitly calls for a `从 0 到 1 配一个……智能体` method article, this structure is available:

1. 现场问题：谁在设备、维修、点检、故障、工单或售后流程里卡住了
2. 边界定义：它不是聊天机器人，而是能查资料、问清问题、给步骤、留记录的现场助手
3. 最小资料包：设备台账、说明书、故障码、维修工单、保养计划、备件清单、历史经验等
4. 最小工作流：报故障/提交任务 -> 识别对象 -> 检索资料 -> 追问现象 -> 给排查步骤 -> 生成记录
5. 权限和责任：哪些只能建议，哪些可以自动生成，哪些必须人工确认
6. 0-1 验证步骤：先选 1 类设备或 1 条流程，导入有限资料，整理高频问题，跑真实案例
7. 可复用清单：先做什么、不要做什么、做到什么算可用

For this article type, the first 300 Chinese characters should naturally include 1-3 stable search/recommendation terms such as `设备智能体`、`设备知识库`、`故障诊断`、`点检`、`工单`、`运维`.
The terms must appear because the scene needs them, not as mechanical keyword stuffing.

Do not schedule this article type if any of the previous four main articles used the same frame. Do not reuse the seven-step structure for case reviews or stage summaries.

Default paragraph ordering:

- 先讲冲突
- 再讲代价
- 再讲机制
- 最后讲判断和动作

When a draft starts from a technology term, rewrite it until a business reader can understand why the article matters before the term is fully defined.

Do not force a list of future articles unless the user asks.

When revising for tone, rewrite the opening first. If the opening becomes more concrete, the rest of the article usually gets easier to de-slop.

## Content Illustration Brief / 内容配图

The writer owns the illustration intent. The layout skill owns the final visual execution.

When drafting an article, decide whether the reader needs an inline illustration to understand the argument. Add an illustration brief only when it clarifies structure, flow, comparison, or an enterprise case. Do not add decorative images.

Use at most 1-3 inline illustrations for a normal WeChat article.

For real industrial case pieces, default to `2-4` visuals when the material supports it:

- pain chain / conflict map
- workflow or system architecture
- high-fidelity product prototype or workbench
- value loop / metrics outcome map

Do not add all four mechanically. Use only the ones that reduce reading friction.

Standard illustration types:

- **Concept diagram**: explain a technical mechanism such as model -> context -> tool -> action.
- **Workflow diagram**: show how AI enters an enterprise process.
- **Comparison diagram**: show demo vs production, chatbot vs agent, tool use vs responsibility boundary.
- **Case path diagram**: show scenario -> AI capability -> human confirmation -> system action -> metric.
- **High-fidelity product prototype**: show what the named agent system actually looks like in use, especially for scenarios such as 售后处置助手、投标助手、招聘助手、客服助手、工单助手.

When an article names a concrete enterprise assistant or workflow product surface and there is no real screenshot available, default to adding a `高保真系统原型图` unless the article is intentionally abstract.

The prototype is not decorative. It should make the reader see:

- 这个智能体在真实系统里长什么样
- 用户在哪里看规划、执行、人工确认和日志
- 哪些界面模块对应文中提到的机制和责任边界

Caption and alt text should describe the scene itself, not the production method.

Use:

- `售后处置助手界面：工单摘要、规划步骤、人工确认与执行日志`
- `投标助手界面：项目摘要、证据引用、风险条款与审批动作`

Avoid:

- `高保真原型图`
- `高清原型图`
- `imagegen 效果图`

For each illustration, include:

- placement: after which section or paragraph
- purpose: what confusion it removes
- diagram type: concept / workflow / comparison / case path / high-fidelity prototype
- nodes: 4-6 short labels
- key message: one sentence
- style note: use the account visual system, not a new style

If no inline illustration is needed, explicitly write `正文插图：无，本文靠文字和小节结构即可。`

## Required Metadata

At the top of the Markdown draft include:

```markdown
# 标题

选题 ID：

发布标题：

建议摘要：

封面提示词：

正文插图：

---
```

摘要 should be under 120 Chinese characters when possible.

## Draft Quality Bar

Before handing off to layout or review, ensure:

- the title can be understood by an enterprise reader who is not deep in AI tooling jargon
- the title gives WeChat a specific industrial recommendation tag when the article is intended as a main growth piece
- the core point appears in the first 3 paragraphs
- the first 150 words mention a real workflow, role, or business consequence
- case-led pieces open from verifiable evidence and continue using the case throughout the article
- stage summaries name their observation range, include counterexamples, and turn the synthesis into a customer decision
- for `从 0 到 1` industrial agent pieces, the draft includes minimum data package, minimum workflow, permission boundary, and 0-1 validation steps
- when possible, the article is anchored in a real company, real product, or real workflow rather than a pure abstract concept
- every technical term is tied to a real problem
- enterprise landing is not treated as an afterthought
- the article contains at least one concrete scenario
- the article makes clear `怎么落地 / 用了什么技术 / 拿到了什么价值`
- the article includes at least one repeatable judgment sentence suitable for forwarding
- the article includes a content illustration brief or explicitly says no inline illustration is needed
- the close does not become a hard sales CTA
- the opening does not sound like a generic industry-summary preface
- repeated template phrases have been reduced instead of redistributed
- the digest is direct and readable, not a compressed AI summary paragraph
- at least five concrete material items support a nonfiction long draft, or the topic and length were narrowed honestly
- each body paragraph adds information instead of restating the previous judgment
- action-level fake reversals were checked, including variants that avoid the literal `不是……而是……` wording
- sentence length, paragraph length, conjunction use, and repeated openings have been reviewed for mechanical regularity
