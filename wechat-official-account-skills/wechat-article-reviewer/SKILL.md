---
name: wechat-article-reviewer
description: Use to review WeChat Official Account articles for 智能体架构笔记 before saving or publishing. Checks positioning, technical clarity, enterprise landing value, tone, layout readiness, and publication risk.
---

# WeChat Article Reviewer

Use this skill to review an article before it is saved as a WeChat draft or sent to the user for publication approval.

Read:

- `../references/account-positioning.md`
- `../references/review-checklist.md`

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
2. Reader value: Will the target reader know what to do or think differently?
3. Technical clarity: Are terms explained through real problems?
4. Enterprise reality: Are process, data, permission, ownership, and measurement considered?
5. Tone: Does it sound human, specific, and object-aware?
6. Layout readiness: Title, digest, cover prompt, section structure, list shape.
7. Risk: unverifiable factual claims, exaggerated promises, sensitive company claims.

This reviewer remains the broad final editor. It should not substitute for the dedicated human-tone pass.

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
