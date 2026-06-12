---
name: wechat-account-operator
description: Use to operate and optimize the WeChat Official Account 智能体架构笔记. Handles content calendar, account analytics, topic strategy, publishing cadence, review of read/share/follow data, and strategy adjustments.
---

# WeChat Account Operator

Use this skill for operating `智能体架构笔记` beyond a single article.

Read `../references/account-positioning.md` before making strategy recommendations.

## Mission

Keep the account focused, consistent, and improving.

Default strategy:

- daily draft generation
- human review before publication
- content pillars: AI technology explanation, enterprise landing, failure reviews, mode innovation
- visual consistency through the layout skill

## Operating Loop

1. Review recent articles and drafts.
2. Review available metrics:
   - reads
   - completion signals if available
   - shares
   - follows
   - comments
   - topic/category
3. Identify what worked and what did not.
4. Adjust topic mix, title style, article length, cover style, or publication timing.
5. Feed recommendations into the next topic planning cycle.

## Weekly Mix

Default mix unless data suggests otherwise:

- 2 technology explanation pieces
- 2 enterprise landing/case pieces
- 1 failure review
- 1 mode innovation or trend judgment
- 1 reserve/lightweight draft or operational review

## Strategy Output

```markdown
## 运营判断

- 本周有效信号：
- 风险/偏移：
- 下周重点：

## 选题调整

- 增加：
- 减少：
- 保持：

## 风格调整

- 标题：
- 正文：
- 封面/插图：

## 下一步动作

- ...
```

## Guardrails

- Do not publish automatically.
- Do not chase irrelevant hot topics.
- Do not recommend a strategy only from one weak metric.
- Prefer small, testable adjustments over sweeping repositioning.

