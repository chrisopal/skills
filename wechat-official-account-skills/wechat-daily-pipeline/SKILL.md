---
name: wechat-daily-pipeline
description: Use to run the end-to-end daily workflow for the WeChat Official Account 智能体架构笔记: topic planning, writing, cover/illustration planning, HTML layout, review, WeChat draft saving, and an audit package for human approval. Never publishes automatically.
---

# WeChat Daily Pipeline

Use this skill for the daily end-to-end workflow of `智能体架构笔记`.

This skill orchestrates:

1. `wechat-topic-planner`
2. `wechat-article-writer`
3. `wechat-article-human-tone-reviewer`
4. `wechat-article-layout`
5. `wechat-article-reviewer`
6. `wechat-account-operator`

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
   - use the host agent's configured image generation capability via the `imagegen` tool first
   - generate cover image with `imagegen`
   - generate inline diagram with `imagegen` based on the writer's brief, only when it improves understanding
   - persist the selected final images into repo-local paths such as `assets/wechat/` before draft save; do not leave final assets only in host cache or chat preview state
   - use local overlay/resizing only for exact labels, final dimensions, or export-format cleanup after `imagegen`
   - unified style from `style-system.md`
5. Layout:
   - apply WeChat HTML style
   - avoid native `<ul>/<li>`
6. Human-tone review:
   - run the dedicated human-tone reviewer on the full draft text
   - fix AI-sounding, repetitive, weak-object, or over-smoothed passages before final review
   - when possible, compare against recent drafts to avoid repeating the same opening/closing patterns
7. Review:
   - run reviewer checklist
   - fix P1/P2 issues before saving
8. Save draft:
   - use local WeChat API helper if available
   - use `.env` for credentials
   - save only as draft
9. Verify:
   - read back draft title, digest, content, and cover
   - confirm no publish action occurred
10. Report audit package.

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
- `imagegen` means the host agent image generation tool/capability, not a repo-local drawing script.
- Do not default to local PIL/SVG/HTML drawing when `imagegen` is available.
- If `imagegen` succeeds visually but the file is not yet inside the repo workspace, first recover/copy the chosen output into `assets/wechat/` from the host cache path such as `$CODEX_HOME/generated_images/...` or from the current session record. Do not switch to a local-drawing fallback just because the built-in output path was inconvenient.
- If `imagegen` is unavailable, fails repeatedly, or cannot yield a usable asset, use a clearly reported fallback asset and include the fallback reason in the audit package.
- If review fails, do not save to WeChat unless the user explicitly asks for a flawed draft.
- If WeChat API saves the draft, always read it back when possible.
