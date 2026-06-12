---
name: wechat-article-writer
description: Use to draft articles for the WeChat Official Account 智能体架构笔记. Writes conversational, technically clear Chinese articles about AI technology, enterprise landing, success cases, failure reviews, and model or workflow innovation.
---

# WeChat Article Writer

Use this skill to write or rewrite article drafts for `智能体架构笔记`.

Read `../references/account-positioning.md` before writing.

## Writing Goal

Write like a thoughtful practitioner talking to a specific reader.

The article should help readers:

- understand an AI concept or architecture decision
- judge whether it applies to their enterprise scenario
- learn from success cases, failure reviews, or implementation patterns

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

Avoid:

- consulting-report tone
- slogan-heavy paragraphs
- excessive acronyms without explanation
- long future topic lists
- exaggerated claims such as “彻底颠覆” or “一文讲透”

## Article Structure

Default structure:

1. Opening: 80-150 words, name the tension or reader pain.
2. Why it matters: explain the business or engineering consequence.
3. Mechanism: explain the technical idea in plain language.
4. Enterprise reality: explain what changes in real workflows.
5. Case or pattern: success, failure, or a reusable adoption pattern.
6. Closing: one grounded takeaway and a soft continuation.

Do not force a list of future articles unless the user asks.

## Required Metadata

At the top of the Markdown draft include:

```markdown
# 标题

发布标题：

建议摘要：

封面提示词：

---
```

摘要 should be under 120 Chinese characters when possible.

## Draft Quality Bar

Before handing off to layout or review, ensure:

- the core point appears in the first 3 paragraphs
- every technical term is tied to a real problem
- enterprise landing is not treated as an afterthought
- the article contains at least one concrete scenario
- the close does not become a hard sales CTA
