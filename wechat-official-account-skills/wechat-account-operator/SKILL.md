---
name: wechat-account-operator
description: Use to operate and optimize the WeChat Official Account 智能体架构笔记. Handles content calendar, account analytics, topic strategy, publishing cadence, review of read/share/follow data, and strategy adjustments.
---

# WeChat Account Operator

Use this skill for operating `智能体架构笔记` beyond a single article.

Read `../references/account-positioning.md` and `../references/topic-pool-workflow.md` before making strategy recommendations.

## Mission

Keep the account focused, consistent, and improving.

Default strategy:

- daily draft generation
- human review before publication
- content pillars: AI technology explanation, enterprise landing, failure reviews, mode innovation
- visual consistency through the layout skill

Current high-confidence adjustment:

- industrial landing stories around `真实公司 / 真实方案 / 真实流程 / 真实价值`
  should lead the mix because they are outperforming pure architecture explanation
- technical explanation pieces should remain, but they should increasingly attach to a real workflow, role, or company case
- deeper case pieces should usually carry more visuals than abstract commentary pieces

## Operating Loop

1. Reconcile the local topic pool with the Get笔记 `公众号选题库` master index by stable `topic_id`.
2. Review recent articles and drafts. Keep `DRAFT_SAVED` separate from `PUBLISHED`.
3. Review available metrics:
   - reads
   - completion signals if available
   - shares
   - follows
   - comments
   - topic/category
4. For confirmed published articles, update the corresponding topic to `PUBLISHED` and record publish time, public link, 24/72-hour metrics, reader feedback, and leads. Do not infer publication from a local file or `media_id`.
5. Identify what worked and what did not.
6. Adjust topic mix, title style, article length, cover style, or publication timing. Keep the near-term business mix around `培训咨询 60% / 产品 40%` unless verified conversion data suggests a change.
7. Feed recommendations into the next topic planning cycle and sync the updated master index to Get笔记 via `/note/update`.

## Weekly Mix

Default mix unless data suggests otherwise:

- 1-2 technology explanation pieces
- 2-3 enterprise landing/case pieces
- 1 failure review
- 1 mode innovation or trend judgment
- 1 reserve/lightweight draft or operational review

If recent data shows a clear case-story advantage, bias the schedule toward:

- real enterprise case
- real product/solution case
- landing Q&A / failure review

and reduce consecutive abstract architecture posts.

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
