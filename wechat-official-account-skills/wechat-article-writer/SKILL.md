---
name: wechat-article-writer
description: Use when drafting WeChat articles for 智能体架构笔记 that need to turn AI architecture topics into enterprise-relevant judgments, especially when jargon-heavy topics must be rewritten around business conflict, workflow reality, and reader decisions.
---

# WeChat Article Writer

Use this skill to write or rewrite article drafts for `智能体架构笔记`.

Read `../references/account-positioning.md` before writing.

## Writing Goal

Write like a thoughtful practitioner talking to a specific reader.

The article should help readers:

- first understand a real enterprise problem or workflow conflict
- then understand the AI concept or architecture decision behind it
- judge whether it applies to their enterprise scenario
- learn from success cases, failure reviews, or implementation patterns

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

## Title Strategy

Prefer `企业判断型标题` over `术语解释型标题`.

Priority order:

1. reader problem or management judgment
2. concrete workflow or business risk
3. then the underlying technical mechanism

Good title shapes:

- `企业做 Agent，为什么……`
- `为什么很多 AI 项目……`
- `AI 应用一上线，真正卡住它的不是……`
- `如果你在做企业 AI，先别急着……`

Avoid by default:

- `X 技术为什么正在取代 Y 技术`
- `A、B、C、D 到底是什么关系`
- `为什么 X 突然成了热点`

These can still be used when the article is explicitly trend-oriented, but only if the title also gives the reader a clear enterprise payoff.

## Voice / 语气

Use Chinese by default.

Preferred tone:

- conversational but not loose
- direct, human, and opinionated
- practical, with enough technical precision
- more “我想跟你把这件事说清楚” than “本文将系统阐述”

Useful sentence shapes:

- “真正麻烦的地方是……”
- “看 demo 的时候，这件事很容易被忽略。”
- “说白了，这不是一个模型问题，而是一个流程问题。”
- “这事不丢人，很多项目都会卡在这里。”
- “如果你是业务负责人/交付负责人/产品负责人，你真正会担心的是……”
- “企业最后买单的，不是这个概念，而是它能不能进流程。”

Avoid:

- consulting-report tone
- slogan-heavy paragraphs
- excessive acronyms without explanation
- long future topic lists
- exaggerated claims such as “彻底颠覆” or “一文讲透”

## Article Structure

Default structure:

1. Opening: 80-150 words, name the reader, the workflow, and the business tension.
2. What is really going wrong: explain the practical consequence and common wrong fixes.
3. Mechanism: explain the technical idea in plain language after the reader already cares.
4. Enterprise reality: explain what changes in real workflows, roles, permissions, and maintenance.
5. Case or pattern: success, failure, or a reusable adoption pattern.
6. Closing: one grounded judgment that readers can repeat or forward.

Default paragraph ordering:

- 先讲冲突
- 再讲代价
- 再讲机制
- 最后讲判断和动作

When a draft starts from a technology term, rewrite it until a business reader can understand why the article matters before the term is fully defined.

Do not force a list of future articles unless the user asks.

## Content Illustration Brief / 内容配图

The writer owns the illustration intent. The layout skill owns the final visual execution.

When drafting an article, decide whether the reader needs an inline illustration to understand the argument. Add an illustration brief only when it clarifies structure, flow, comparison, or an enterprise case. Do not add decorative images.

Use at most 1-3 inline illustrations for a normal WeChat article:

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
- the core point appears in the first 3 paragraphs
- the first 150 words mention a real workflow, role, or business consequence
- every technical term is tied to a real problem
- enterprise landing is not treated as an afterthought
- the article contains at least one concrete scenario
- the article includes at least one repeatable judgment sentence suitable for forwarding
- the article includes a content illustration brief or explicitly says no inline illustration is needed
- the close does not become a hard sales CTA
