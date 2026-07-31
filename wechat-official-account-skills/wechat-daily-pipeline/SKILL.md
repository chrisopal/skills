---
name: wechat-daily-pipeline
description: "Use to run the end-to-end daily workflow for the WeChat Official Account 智能体架构笔记: topic planning, writing, cover/illustration planning, HTML layout, review, WeChat draft saving, and an audit package for human approval. Never publishes automatically."
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
- `../references/growth-playbook.md`
- `../references/style-system.md`
- `../references/review-checklist.md`

## Current Recommendation Strategy

When no stronger user instruction overrides it, run the daily pipeline as an `AI 落地复盘与决策笔记` workflow, not a generic `工业 AI 信息号` workflow or a setup-tutorial stream.

Use the validated recommendation signal from recent backend data:

- strongest repeatable main-article pattern: `真实公司 / 真实流程 / 真实结果 / 清晰业务代价`
- proven tag cluster: `设备 / 工业 / 智能体 / 知识库`
- priority search/recommendation phrases: `设备智能体`、`工业智能体`、`设备知识库`、`设备维修智能体`、`故障诊断`、`点检`、`工单`、`MES`、`运维`
- `从 0 到 1` is one historical article-level signal, not a reusable breakout formula

Practical default:

- Rotate the four-week mix around `真实案例复盘 50% + 阶段总结 30% + 方法拆解 20%`.
- If recent main articles are dominated by setup methods, the next main article must be a case review, stage summary, failure review, or customer-decision piece.
- If using daily reports or product research as source material, translate the source into a customer question: `谁正在为这个问题付代价，项目改了哪段工作，结果怎么验收，客户为什么会继续投入？`
- Do not let a broad news summary become the final article unless the user explicitly asks for a news roundup.
- For growth-oriented drafts, the title and first 300 Chinese characters should naturally expose one concrete industrial workflow tag. Do not keyword-stuff.

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
   - compare at least the latest 10 main-article titles and latest 4 article structures before selecting a topic
2. Plan topics:
   - generate candidates
   - select one recommended topic
   - produce writer brief
   - prefer evidence-backed case reviews, stage summaries, failure reviews, or customer-decision topics over another setup article when scores are close
   - require the selected topic brief to include minimum data package, workflow, permission boundary, and 0-1 validation path if it is a setup article
   - reject the candidate if any of the previous four main articles used the same title frame or section sequence
3. Write the article:
   - title, digest, cover prompt
   - content illustration brief or explicit no-illustration decision
   - conversational Chinese body
   - technical clarity + enterprise landing value
   - when recent ops feedback indicates weak first-screen attraction, prefer titles with concrete company/result/workflow hooks over repeated abstract judgment formulas
   - case reviews must keep the real case as the article spine; stage summaries must include observation scope, counterexamples, and a customer decision
   - use 现场问题 -> 边界定义 -> 最小资料包 -> 最小工作流 -> 权限责任 -> 0-1 验证 -> 可复用清单 only for the limited method-article slot
4. Prepare visuals:
   - use the host agent's configured image generation capability via the `imagegen` tool first
   - generate cover image with `imagegen`
   - keep the homepage cover simpler than the inline diagrams: one core scene, 3-5 modules max, optional short result badges, no dense explanatory panels
   - generate inline diagram with `imagegen` based on the writer's brief, only when it improves understanding
   - immediately after each `imagegen` call, persist the selected final image into a repo-local path such as `assets/wechat/` before draft save; do not leave final assets only in host cache or chat preview state
   - when running inside `/Users/guojiexie/content-mgmt`, use `python3 scripts/persist_imagegen_output.py --target assets/wechat/<slug>-<role>-imagegen.png --record assets/wechat/imagegen-manifest.jsonl` as the default persistence step
   - use local overlay/resizing only for exact labels, final dimensions, or export-format cleanup after `imagegen`
   - unified style from `style-system.md`
5. Layout:
   - apply WeChat HTML style
   - avoid native `<ul>/<li>`
6. Human-tone review:
   - run the dedicated human-tone reviewer on the full draft text
   - fix AI-sounding, repetitive, weak-object, or over-smoothed passages before final review
   - when possible, compare against recent drafts to avoid repeating the same opening/closing patterns
   - fail the review when the opening is a generic invented factory scene and the article then repeats the same setup checklist used in recent drafts
   - if the draft leans on repeated crutch phrases such as `真正值钱的`、`最值得企业学的`、`下一步该补的` or too many `不是……而是……`, rewrite those sections instead of merely swapping synonyms
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

## Revision Policy

If human feedback after draft save says the article still has obvious AI smell, awkward sentence rhythm, or template-heavy judgment lines:

- revise the Markdown source first
- re-run human-tone review mentally against the updated text
- re-render HTML if needed
- update the existing WeChat draft via `update-draft` when a same-day `media_id` already exists
- do not create a second near-duplicate draft just for style edits

## Expected Local Workspace

If running in `/Users/guojiexie/content-mgmt`, use the existing conventions:

- drafts in `drafts/`
- images in `assets/wechat/`
- imagegen persistence helper `scripts/persist_imagegen_output.py`
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
- If `imagegen` succeeds visually but the file is not yet inside the repo workspace, first recover/copy the chosen output into `assets/wechat/` from the host cache path such as `$CODEX_HOME/generated_images/...` or from the current session record. In this repo, default to `python3 scripts/persist_imagegen_output.py --target ... --record assets/wechat/imagegen-manifest.jsonl` immediately after the `imagegen` call. Do not switch to a local-drawing fallback just because the built-in output path was inconvenient.
- If `imagegen` is unavailable, fails repeatedly, or cannot yield a usable asset, use a clearly reported fallback asset and include the fallback reason in the audit package.
- If review fails, do not save to WeChat unless the user explicitly asks for a flawed draft.
- If WeChat API saves the draft, always read it back when possible.
