---
name: wechat-industrial-ai-innovation-product-pipeline
description: "Use when turning the daily 工业AI创新产品研究 into a WeChat Official Account 图片消息草稿 for 智能体架构笔记, especially when the output should be 2-3 company/product cards with 9:16 vertical visuals, saved as draft only, with a review bundle and no automatic publishing."
---

# WeChat Industrial AI Innovation Product Pipeline

Use this skill when the goal is a closed loop from `工业AI创新产品研究` to a WeChat Official Account draft for `智能体架构笔记`.

Read:

- `../references/account-positioning.md`
- `../references/style-system.md`
- `../references/review-checklist.md`
- `../references/imagepost-draft-api.md`

Also use:

- `得到大脑（Get笔记）` skill for verified note save / KB attachment
- `imagegen` skill for every final visual

## Current Recommendation Strategy

This pipeline should not select innovation products only because they are new. It should select products that help the account own a narrow WeChat recommendation path:

> `工业智能体落地方法号`：具体设备、具体流程、具体系统、具体责任边界。

Priority product angles:

- products that can become `设备智能体从 0 到 1` source material: 设备知识库、维修、点检、故障诊断、备件、巡检、售后
- products that can become `工厂流程智能体从 0 到 1` source material: 工单、采购确认、订单处理、质量异常、报表分析、排产
- products that show `老系统长出智能体`: MES、ERP、PLM、SCADA、APS、WMS integration with knowledge, tools, approvals, logs, and human confirmation

For each chosen company/product, explicitly decide:

- it maps to which industrial workflow
- what minimum data package it would need
- what permission or human-confirmation boundary makes it safe
- what future main article it can support

Avoid broad AI-agent platform announcements unless there is a visible industrial workflow, device, system integration, or deployment path.

## Mission

Take the current innovation-product research and turn it into:

1. a verified Get笔记 note
2. one `imagegen` visual per company/product case
3. WeChat-ready case copy in the account voice
4. a saved WeChat draft for human review only
5. an audit bundle with links, image paths, prompts, and draft metadata

## Hard Boundary

Never publish automatically.

Allowed:

- read the latest innovation-product research note / markdown
- create local JSON / Markdown / image assets
- upload WeChat draft assets
- save draft only
- update an existing draft when the user wants a revised version

Forbidden:

- calling publish / freepublish endpoints
- exposing AppSecret, access token, cookies, or `.env` values
- inventing company facts, links, or metrics

## Default Source

Prefer the same-day `工业AI创新产品研究`.

On this machine, default assumptions are:

- source KB: `工业AI创新产品知识库`
- preferred `topic_id`: `JK2Om9a0`
- automation lineage: `ai-2`

If the same-day research does not exist yet:

1. run the innovation-product research workflow first
2. save it to Get笔记
3. only then continue to WeChat draft creation

## Important Product Boundary

When the user says `贴图` / `图片消息` / `小红书式`, default to WeChat draft `article_type=newspic`.

`newspic` still has the same constraints as the daily image-post pipeline:

- plain-text body only
- no HTML links
- no Markdown-rich formatting assumptions

If richer links are required, keep them in the review bundle or create a companion `news` draft only when the user explicitly wants it.

## Default Workflow

1. Load the same-day innovation-product research.
   - Prefer the already verified Get笔记 note or the local markdown used for that note
2. Normalize `2-3` companies/products into a structured bundle.
   - default one case = one image card
   - keep original source URLs
   - weak facts must be marked `未确认` / `未公开`
   - each case must include `落地标签`: `设备智能体` / `工厂流程智能体` / `老系统智能体` / `暂不适合主文`
   - each case must include `可延展主文`: a future concrete article angle, or explain why it cannot support one
3. Write copy for each case.
   - `标题`: short, direct, no hype
   - `观点`: one sharp sentence
   - `说明`: what happened, why it matters, what industrial readers should notice
   - `最小资料包`: documents, records, system data, logs, rules, or knowledge needed for the product to land
   - `权限边界`: what can be suggested, generated, executed, or must require human confirmation
   - `来源`: keep raw URLs in the review bundle; in `newspic`, include them as named plain-text URL lines
4. Generate visuals with `imagegen`.
   - one image per case
   - use the shared style system
   - default to `infographic-diagram`
   - visuals explain the product direction; they are not decorative posters
5. Persist assets locally.
   - keep stable names under `assets/wechat/`
   - never leave final assets only in `$CODEX_HOME/generated_images/...`
6. Build the WeChat draft payload.
   - default mode: `newspic`
   - title must be 20 Chinese characters or fewer; default to `工业AI创新产品 MM-DD`
   - default to one `newspic` article containing all case images
   - put up to 20 generated case images into one `image_info.image_list`
   - body is one compact plain-text note: short overview, one short paragraph per case, named source URL lines, and one final judgment
7. Save or update the draft with `../scripts/wechat_imagepost_draft_api.py`.
8. Report the audit bundle.

If running on this machine and the workspace is `/Users/guojiexie/content-mgmt`:

- reuse `/Users/guojiexie/content-mgmt/.env`
- reuse `/Users/guojiexie/content-mgmt/scripts/persist_imagegen_output.py`
- for `newspic` image-post drafts, use `../scripts/wechat_imagepost_draft_api.py`

## Copy Rules

Voice must match `智能体架构笔记`:

- explain like someone who understands both technology and landing
- prefer natural judgment like `真正麻烦的是` / `说白了` / `如果你是工厂负责人`
- no consultant report tone
- no inflated phrases like `颠覆` / `彻底改变`

Each case should include:

- `案例标题`
- `一句观点`
- `案例说明`
- `落地标签`
- `最小资料包`
- `权限边界`
- `可延展主文`
- `来源链接`
- `配图说明`

## Visual Rules

Use the shared account style from `style-system.md`.

### Mandatory format

- final case visuals are `9:16` vertical cards
- do not use horizontal landscape cards as the default deliverable
- when revising an existing same-day draft, replace old horizontal case images with the new vertical set so the draft stays consistent

### Mandatory look

- white or near-white background
- engineering paper feel
- deep gray, ink green, small orange highlights
- modules, arrows, labels, equipment/process/data relationships
- no people unless the case truly requires it
- no poster gradients
- no fake dashboards unless the case is explicitly software-centric

### Recommended vertical-card structure

- top: company/product title + 1 short category tag
- middle: one product logic diagram or process chain
- lower-middle: 3-4 short evidence/value bullets
- bottom: one closing judgment line + source/date footer

Recommended visual forms:

- capability chain
- process map
- control loop
- robot teaching / orchestration flow
- product-value-landing diagram

## Bundle Outputs

Produce these artifacts before draft save finishes:

- `case-bundle.json`
- `case-review.md`
- all generated images
- final WeChat draft payload JSON
- draft save or draft update result metadata

Recommended review markdown:

```markdown
## 今日待审贴图草稿

- 标题：
- 草稿类型：`newspic`
- 来源研究：
- Get笔记 note_id：
- 草稿 media_id：
- 案例数：
- 图片比例：`9:16`
- 推荐路径判断：
- 可延展主文：

## 案例清单

### 01
- 标题：
- 观点：
- 落地标签：
- 最小资料包：
- 权限边界：
- 可延展主文：
- 配图路径：
- 来源链接：

## 发布边界

已保存草稿，未发布。请人工审核。
```

## WeChat Draft Mode Rules

Use `newspic` when the user explicitly wants `贴图`.

- body text must stay simple
- title must stay within 20 Chinese characters
- assume the body is rendered as plain text
- structure the body with visible section markers such as `【01｜Company】`
- write sources as named URL lines
- do not use Markdown links, HTML links, or HTML bold in `newspic.content`
- default to a single `newspic` article with multiple images, not one article per case
- use real line breaks, not literal escaped `\\n`

## Failure Handling

- If WeChat credentials are missing, still generate the local bundle and stop before upload.
- If draft save or update fails, report the stage, error code, and human-readable reason.
- If `newspic` constraints block richer formatting, save the image-post draft anyway and keep full links in the review bundle.
- If `imagegen` fails for one case, do not drop the case silently; keep a fallback prompt and note the blocker in the audit package.
