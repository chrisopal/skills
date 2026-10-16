---
name: wechat-article-reviewer
description: Use to review WeChat Official Account articles for 智能体架构笔记 before saving or publishing. Checks positioning, technical clarity, enterprise landing value, tone, layout readiness, and publication risk.
---

# WeChat Article Reviewer

Use this skill to review an article before it is saved as a WeChat draft or sent to the user for publication approval.

Read:

- `../references/account-positioning.md`
- `../references/review-checklist.md`
- `../references/human-writing-playbook.md`

Use together with `../wechat-article-human-tone-reviewer/SKILL.md` when the draft may still sound AI-written, overly repetitive, or weakly addressed to a concrete reader. The human-tone reviewer should run first when both are used.

## Review Stance

Be a strict editor. Prioritize issues that would make the article:

- drift away from account positioning
- sound like generic AI content
- over-focus on tools rather than meaning
- lack enterprise landing value
- feel too stiff or report-like
- create publication risk

## Review Dimensions

1. Positioning: Does it serve “把 AI 技术讲明白 / 把企业真实发生讲清楚”?
2. Reader value: Will the target reader know what to do or think differently? If sharing is a goal, what concrete decision could they discuss with a colleague using this article?
3. Technical clarity: Are terms explained through real problems?
4. Enterprise reality: Are process, data, permission, ownership, and measurement considered?
5. Tone: Does it sound human, specific, and object-aware?
6. Layout readiness: Title, digest, cover prompt, section structure, list shape.
7. Risk: unverifiable factual claims, exaggerated promises, sensitive company claims.

In tone review, explicitly check for:

- overuse of `真正 / 最值得 / 下一步该补 / 不是……而是……`
- digest or opening paragraph that reads like a generic AI summary
- too many long, abstract judgment sentences in a row
- repeated formula lines that could belong to almost any enterprise-AI article
- whether the draft reads like a clear business explainer rather than a consultant memo
- whether the reader can retell the evidence and decision without every section ending in a forced takeaway slogan
- whether the structure follows the current material instead of reproducing a successful article's title frame, reversal and chapter order
- whether recommendation lines sound natural in spoken Chinese rather than like outside-in commentary
- whether phrases such as `这条线很值得盯`、`更值得关注的是`、`这个信号是`、`下一步该补的是` should be rewritten into more natural operator language
- whether each paragraph contributes new material instead of paraphrasing the previous paragraph
- whether a rhetorical reversal invents a reader misconception even when it avoids a known banned phrase
- whether the long-form article has enough verified material to justify its length
- whether sentence length, paragraph length, conjunctions, and repeated openers create a machine-like rhythm

This reviewer remains the broad final editor. It should not substitute for the dedicated human-tone pass.

Check the writer's internal reader card against the actual article. If the draft mainly lists what the author executed or what each Skill outputs, but does not help the target role make a recognizable decision, mark it `需要重写` even when its facts and screenshots are correct. Apply the audience-first storytelling rules in `../references/human-writing-playbook.md`; distinguish necessary capability limits from process detail that belongs in the audit package.

For practice reviews, verify that the original goal, observed cost, changed responsibilities, reused work, actual outputs and applicable limits are clear where relevant. Do not require a project reversal for tutorials or explanations. Reject generated prototypes presented as actual screenshots, exposed customer material, or blocked/demo artifacts presented as successful delivery. Treat engagement explanations as hypotheses unless the available comparisons support causality; a ratio of displayed shares to reads is not a unique-reader share rate.

## Output Format

```markdown
## 审稿结论

结论：通过 / 需要小修 / 需要重写

## 主要问题

- [P1] ...
- [P2] ...

## 建议修改

- ...

## 发布前检查

- 标题：
- 摘要：
- 封面：
- 排版：
- 风险：
```

If the article is acceptable, still provide 2-3 useful polish suggestions.
