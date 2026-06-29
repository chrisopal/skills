---
name: wechat-industrial-ai-imagepost-pipeline
description: "Use to turn the daily 工业AI日报 into a WeChat Official Account 图片消息 or companion 图文草稿 for 智能体架构笔记: reuse the verified daily report, save to Get笔记 if needed, generate one imagegen visual per case, write account-matched观点和说明, save only to WeChat draft, and emit a review bundle. Never publishes automatically."
---

# WeChat Industrial AI Image-Post Pipeline

Use this skill when the goal is a closed loop from `工业AI日报` to a WeChat Official Account draft for `智能体架构笔记`.

Read:

- `../references/account-positioning.md`
- `../references/style-system.md`
- `../references/review-checklist.md`
- `../references/imagepost-draft-api.md`

Also use:

- `得到大脑（Get笔记）` skill for verified note save / KB attachment
- `imagegen` skill for every final visual

## Mission

Take the current industrial AI daily report and turn it into:

1. a verified Get笔记 note
2. one `imagegen` visual per重点案例
3. WeChat-ready case copy in the account voice
4. a saved WeChat draft for human review only
5. an audit bundle with links, image paths, prompts, and draft metadata

## Hard Boundary

Never publish automatically.

Allowed:

- read the latest daily report note / markdown
- create local JSON / Markdown / image assets
- upload WeChat draft assets
- save draft only
- read back draft metadata when helper support exists

Forbidden:

- calling publish / freepublish endpoints
- exposing AppSecret, access token, cookies, or `.env` values
- inventing company facts, links, or metrics

## Important Product Boundary

When the user says `贴图` / `小红书式` / `图片消息`, default to WeChat draft `article_type=newspic`.

But the official WeChat draft API currently states:

- `newspic` content is more constrained than normal `news`
- image-message content supports plain text and limited special tags, not full HTML article behavior

Practical rule:

- If the user wants true image-post drafts, save `newspic`
- If the user also wants rich clickable links in-body, produce a dual output:
  - primary `newspic` draft for the visual post
  - companion review bundle or `news` draft with full links

Do not promise fully rich HTML links inside `newspic` body unless verified in the current account/runtime.

## Default Workflow

1. Run a duplicate / already-published gate before fixing today’s case set.
   - inspect recent local audit artifacts first, especially `/Users/guojiexie/content-mgmt/drafts/*industrial-ai-imagepost-review.md`, same-day `case-bundle.json`, and `/Users/guojiexie/.codex/automations/ai/memory.md`
   - treat the following as duplicate signals:
     - same source URL already used in a recent daily run
     - same company + same event/topic already used in a recent daily run
     - same or near-same Chinese case title already used in a recent daily run
     - explicit publication markers such as `已发布` / `已发表` / `published` found in review or memory notes
   - if the current candidate set overlaps with already-used or already-published content, drop the overlapping case and continue searching until you rebuild a fresh 3-6 case set
   - if no explicit published record is available, still treat a successfully saved prior same-day draft or prior same-day daily run as a strong duplicate signal and avoid reusing it
   - write the duplicate-screening conclusion into the local review bundle and automation memory so later reruns do not repeat the same selection
2. Load the source report.
   - Prefer the already verified same-day `工业AI日报`
   - If missing, run the industrial daily-report workflow first
   - Prefer the saved Get笔记 note or the local markdown used for that note
3. Normalize 3-6 cases into a structured bundle.
   - one case = one visual card
   - keep the original source URLs
   - mark weak facts as `未确认`
4. Write copy for each case.
   - `标题`: short, direct, no hype
   - `观点`: one sentence in the account voice
   - `说明`: what happened, why it matters, what industrial readers should notice
   - `整体方案`: 2 short lines explaining how the solution works end to end; do not reduce this to a slogan
   - `来源`: keep raw URLs in the review bundle; in `newspic`, include them as plain text lines unless the current account confirms richer support
5. Generate visuals with `imagegen`.
   - one image per case
   - use the shared style system
   - default to `infographic-diagram`
   - visuals explain the case; they are not decorative illustrations
   - every final card must pass the Fullcard Visual Contract and Visual Review Gate below before draft save
6. Persist assets locally.
   - keep stable names under a workspace path such as `assets/wechat/`
   - never leave final assets only in `$CODEX_HOME/generated_images/...`
7. Build the WeChat draft payload.
   - default mode: `newspic`
   - title must be 20 Chinese characters or fewer; default to `工业AI日报 MM-DD` or `每日工业AI MM-DD`
   - for image-post publishing, default to one article containing all case images
   - put up to 20 generated case images into one `image_info.image_list`
   - write one compact plain-text daily-report body: short overview, one short paragraph per case, named source URL lines, and one final viewpoint
8. Save draft with `../scripts/wechat_imagepost_draft_api.py`.
9. Report the audit bundle.

If running on this machine and the workspace is `/Users/guojiexie/content-mgmt`:

- reuse `/Users/guojiexie/content-mgmt/.env`
- reuse `/Users/guojiexie/content-mgmt/scripts/persist_imagegen_output.py`
- for normal `news` drafts, prefer `/Users/guojiexie/content-mgmt/scripts/wechat_draft_api.py`
- for `newspic` image-post drafts, use `../scripts/wechat_imagepost_draft_api.py`

## Copy Rules

Voice must match `智能体架构笔记`:

- explain like someone who understands both technology and landing
- prefer `真正麻烦的是` / `说白了` / `你如果是工厂负责人` style natural judgment when it helps
- no consultant report tone
- no inflated phrases like `颠覆` / `彻底改变`

Each case should include:

- `案例标题`
- `一句观点`
- `案例说明`
- `整体方案`
- `来源链接`
- `配图说明`

## Visual Rules

Use the shared account style from `style-system.md`.

For this skill, prefer:

- white or near-white background
- engineering paper feel
- deep gray, ink green, small orange highlights
- modules, arrows, labels, material/process/equipment/data relationships
- no people unless the case truly requires it
- no poster-like gradients
- no fake dashboards unless the case is explicitly software-centric

Recommended visual forms:

- capability chain
- process map
- supply chain / factory / R&D flow
- equipment-data-decision loop
- industry-specific concept diagram

## Fullcard Visual Contract

For daily `newspic` image cards, use a 9:16 `imagegen` fullcard that behaves like a dense but readable engineering note. The preferred reference style is the earlier `OnLogic` and `SINTRONES` cards: large case title, company/region chip, top `图例链路`, a large central architecture/process diagram, then four bottom explanation rows. The card must include these visible sections:

- `标题`: concise case title, not oversized; leave room for the body.
- `公司/地区`: company plus region or `未确认`, usually as a green chip or subtitle.
- `行业标签`: 2-4 short tags such as `ERP / 制造分销 / AI决策`.
- `图例链路`: 4 labeled modules with arrows, showing the simple path.
- `中部方案图`: the largest section; use boxes, device/system icons, dashboards, process arrows, feedback loops, and callouts to explain the end-to-end solution.
- `做了什么`: concrete event, product, partnership, deployment, or release.
- `方案抓手`: 2-4 mechanism labels; avoid generic `AI平台` alone.
- `业务价值`: measurable or operational value; if exact numbers are unavailable, state the business effect without inventing metrics.
- `我的判断`: one account-voice judgment that names why industrial readers should care.
- Optional `核心要点`: one short bottom note when the case needs a final synthesis.

Layout rules:

- Use the reference structure: header -> green divider -> `图例链路` -> large central scheme diagram -> four bottom rows.
- The central scheme diagram should occupy roughly 40-50% of the card height and carry the "overall solution" explanation visually.
- Bottom rows should use large green square icons on the left, bold row labels, and 1-2 lines of explanation on the right.
- Keep body text in short clauses; no dense paragraphs, tiny footnotes, or text overflow.
- Use white / near-white paper, deep gray, ink green, and small orange highlights only.
- No fake logos, watermarks, people, decorative collages, cyberpunk, blue-purple gradients, or abstract background art.

## Visual Review Gate

Before saving or updating the WeChat draft, visually inspect the generated cards or a contact sheet. If any card fails, regenerate it before upload. Record the review result in the local review markdown.

Minimum pass criteria:

- Required sections are present: `公司/地区`, `整体方案`, `图例链路`, `做了什么`, `方案抓手`, `业务价值`, `我的判断`.
- The central scheme diagram explains the end-to-end solution path, not just a row of abstract icons.
- Bottom rows follow the reference style: icon + label + explanatory copy.
- Style matches the account system: paper feel, ink green/deep gray/orange, engineering-note layout.
- Title is readable but not dominant; body content has clear hierarchy.
- Chinese text is readable and not visibly clipped, crowded, or overlapping.
- No real company logo, watermark, stock-photo feel, or decorative-only image elements.

## Bundle Outputs

Produce these artifacts before draft save finishes:

- `case-bundle.json`
- `case-review.md`
- all generated images
- final WeChat draft payload JSON
- draft save result metadata
- visual review result for each final image

Recommended review markdown:

```markdown
## 今日待审贴图草稿

- 标题：
- 草稿类型：`newspic` / `news`
- 来源日报：
- Get笔记 note_id：
- 草稿 media_id：
- 案例数：
- 去重检查：
- 是否发现与已发表/已保存内容重复：
- 视觉审核：

## 案例清单

### 01
- 标题：
- 观点：
- 配图路径：
- 视觉审核：
- 来源链接：

## 发布边界

已保存草稿，未发布。请人工审核。
```

## WeChat Draft Mode Rules

### A. `newspic` image-post draft

Use when the user explicitly wants `贴图`.

- body text must stay simple
- title must stay within 20 characters; use date-short titles such as `工业AI日报 06-21`
- assume the body is rendered as plain text; do not rely on Markdown, HTML, or rich link rendering
- structure the body with visible plain-text section markers, for example `【01｜Company】`
- write sources as named URL lines, for example `来源名：https://example.com`
- 中文硬规则：`newspic` 正文按纯文本处理，不使用 Markdown 加粗、Markdown 链接或 HTML 链接
- 已验证：向 `newspic.content` 直接提交 `<a>` / `<strong>` 会被接口以 `45166 invalid content` 拒绝；不要用 HTML 伪造后台编辑器的“内容链接”
- keep full clickable-link material in the local review bundle or a companion `news` draft if needed
- attach images via `image_info.image_list`
- first image is the cover by default
- default to a single `newspic` article with multiple images, not one article per case
- 中文硬规则：贴图默认是“单篇 `newspic` + 多张图片”，不要拆成多个子文章
- avoid literal escaped newlines such as `\\n\\n`; the saved body must contain real line breaks

### B. Companion `news` draft or review bundle

Use when clickable links and richer explanation are required.

- keep full HTML/link richness here
- reference the same case visuals
- do not replace the `newspic` draft unless the user asks to prioritize article form over image-post form

## Failure Handling

- If WeChat credentials are missing, still generate the local bundle and stop before upload.
- If draft save fails, report the endpoint stage, error code, and human-readable reason.
- If `newspic` constraints block required links, save the image-post draft anyway and keep full links in the review bundle.
- If `imagegen` fails for one case, do not drop the case silently; keep a fallback prompt and note the blocker in the audit package.
- If duplicate screening shows today’s candidate set collides with already-published or already-used items, continue searching and rebuild the case set before any image generation or draft save.
