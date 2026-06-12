---
name: wechat-daily-pipeline
description: Use to run the end-to-end daily workflow for the WeChat Official Account 智能体架构笔记: topic planning, writing, cover/illustration planning, HTML layout, review, WeChat draft saving, and an audit package for human approval. Never publishes automatically.
---

# WeChat Daily Pipeline

Use this skill for the daily end-to-end workflow of `智能体架构笔记`.

This skill orchestrates:

1. `wechat-topic-planner`
2. `wechat-article-writer`
3. `wechat-article-layout`
4. `wechat-article-reviewer`
5. `wechat-account-operator`

Read:

- `../references/account-positioning.md`
- `../references/style-system.md`
- `../references/review-checklist.md`

## Hard Boundary

Never publish automatically.

Allowed:

- create local draft files
- generate cover and illustration assets
- upload cover/materials when credentials are configured
- save a WeChat Official Account draft
- read back the draft for verification
- report an audit package to the user

Forbidden:

- calling publish/freepublish endpoints
- changing AppSecret or account settings
- exposing `.env`, access tokens, AppSecret, or cookies

## Daily Workflow

1. Read operation context:
   - account positioning
   - recent operation plan
   - existing drafts and recent outputs
2. Plan topics:
   - generate candidates
   - select one recommended topic
   - produce writer brief
3. Write the article:
   - title, digest, cover prompt
   - content illustration brief or explicit no-illustration decision
   - conversational Chinese body
   - technical clarity + enterprise landing value
4. Prepare visuals:
   - cover image
   - inline diagram based on the writer's brief, only when it improves understanding
   - unified style from `style-system.md`
5. Layout:
   - apply WeChat HTML style
   - avoid native `<ul>/<li>`
6. Review:
   - run reviewer checklist
   - fix P1/P2 issues before saving
7. Save draft:
   - use local WeChat API helper if available
   - use `.env` for credentials
   - save only as draft
8. Verify:
   - read back draft title, digest, content, and cover
   - confirm no publish action occurred
9. Report audit package.

## Expected Local Workspace

If running in `/Users/guojiexie/content-mgmt`, use the existing conventions:

- drafts in `drafts/`
- images in `assets/wechat/`
- operation notes in `operations/`
- API helper `scripts/wechat_draft_api.py`
- credentials in `.env`

If paths differ, adapt to the current workspace and report the paths used.

## Audit Package Format

```markdown
## 今日待审草稿

- 标题：
- 摘要：
- 选题理由：
- 目标读者：
- 封面路径：
- 插图路径：
- 草稿 media_id：
- 审稿结论：
- 建议调整点：

## 发布边界

已保存草稿，未发布。请人工审核后再确认是否发布。
```

## Failure Handling

- If credentials or IP whitelist fail, produce local Markdown/HTML/assets and report the blocker.
- If cover generation fails, create a precise cover prompt and continue with article draft.
- If review fails, do not save to WeChat unless the user explicitly asks for a flawed draft.
- If WeChat API saves the draft, always read it back when possible.
