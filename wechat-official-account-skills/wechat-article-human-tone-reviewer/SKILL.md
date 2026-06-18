---
name: wechat-article-human-tone-reviewer
description: Use when a WeChat article draft for 智能体架构笔记 is basically on-topic but still risks sounding AI-written, repetitive, weakly addressed to a concrete reader, or logically smooth without enough human judgment.
---

# WeChat Article Human Tone Reviewer

Use this skill after a first complete draft exists and before the final publication review.

Read:

- `../references/account-positioning.md`
- `../references/review-checklist.md`

## Mission

This reviewer is not the fact checker or the layout checker.

Its job is to catch the problems that make a technically correct article still feel like “AI 在写”:

- too smooth, too even, too generic
- every paragraph sounding like the previous one
- weak reader object
- logic that is not wrong but also not sharp
- repeated opening/transition/closing habits across articles

The goal is not to make the draft fancy.

The goal is to make it sound like one specific practitioner is talking to one specific reader about one specific business tension.

## Review Focus

Review for these failure modes first:

1. **AI 味**
   - polished but bloodless
   - all paragraphs equally complete and equally safe
   - abstract nouns replacing concrete scenes
   - generic transitions such as “首先 / 其次 / 最后” or “随着……发展”
   - consultant-report tone, summary tone, or keynote tone
2. **对象感不足**
   - reader exists only as a generic “企业”
   - no role pressure such as 老板、交付负责人、产品负责人、工厂负责人
   - no “你为什么现在要关心这件事”
3. **逻辑发虚**
   - conclusion is stated but not earned
   - mechanism is explained without enough business consequence
   - example appears but does not push the judgment forward
   - the article moves from concept to value too quickly
4. **表达同质化**
   - repeated article openings
   - repeated sentence stems across sections
   - repeated close-out formulas
   - the same “真正……不是……而是……” pattern used too many times
5. **人味不够**
   - no friction, no hesitation, no tradeoff
   - too many perfect full-sentence claims
   - not enough “这事为什么难”“大家通常会误判什么”

## Cross-Draft Anti-Repetition Rule

When the workspace has recent drafts from the same account, inspect `2-5` recent drafts before final judgment.

Specifically compare:

- opening paragraph shape
- title formula
- repeated judgment templates
- repeated endings
- overused pet phrases

Do not demand novelty for novelty's sake.

Flag repetition only when the current draft would feel like a lightly re-skinned version of the last few pieces.

## What Good Looks Like

The article should feel like:

- one person talking to one identifiable reader
- anchored in one concrete business scene
- willing to make one sharp judgment
- willing to say what does **not** work
- varied in rhythm, not uniformly “complete”

Good signs:

- at least one paragraph could only belong to this article, not any AI/Agent article
- the opening names a real workflow tension fast
- the middle explains mechanism through consequence
- the close leaves the reader with one repeatable line, not a generic summary

## Editing Standard

Prefer **surgical rewrite guidance** over full rewrite.

Ask for full rewrite only when:

- the opening is fundamentally generic
- the article has no stable reader object
- the logic chain is mostly assertion
- the whole piece reads like a model summary

Otherwise, identify the smallest high-leverage fixes:

- rewrite the opening
- sharpen 1-2 soft judgment paragraphs
- cut repeated transitions
- replace generic close with one stronger final line

## Output Format

```markdown
## 人味审稿结论

结论：通过 / 需要小修 / 需要重写

## AI 味与对象感问题

- [P1] ...
- [P2] ...

## 重复与表达问题

- ...

## 逻辑问题

- ...

## 建议改写

- 原句：
  问题：
  建议改写：

- 原句：
  问题：
  建议改写：

## 最终判断

- 这篇文章现在更像谁在对谁说话：
- 还缺的那一下判断力是什么：
- 是否建议进入最终通用审稿：
```

## Guardrails

- Do not polish the article into a more generic article.
- Do not reward empty顺滑.
- Do not encourage “金句堆积”.
- Do not remove strong judgment just because it is opinionated; only change it if it is weakly supported.
- Preserve the account voice: practical, direct, business-first, and slightly opinionated.
