---
name: wechat-article-layout
description: Use to format WeChat Official Account articles for 智能体架构笔记, including unified HTML/CSS styling, cover images, inline illustrations, diagram prompts, and visual QA. Enforces the account's paper-like engineering style and avoids native ul/li bullet issues.
---

# WeChat Article Layout

Use this skill when preparing a `智能体架构笔记` article for WeChat draft upload.

Read `../references/style-system.md` before layout work.

## Mission

Turn clean Markdown into a polished WeChat-ready article:

- unified visual style
- cover image and optional inline illustrations
- readable mobile-first HTML
- no native `<ul>` / `<li>` bullet rendering

## Layout Rules

Use inline styles because WeChat strips or transforms many CSS patterns.

Required components:

- article header with title, short label, digest
- section headings with `SECTION 01`
- paragraph rhythm around 16px / 1.86-1.9
- numbered list blocks instead of `<ul>/<li>`
- quote block for key question or judgment
- fixed footer signature

Forbidden:

- native `<ul>` and `<li>`
- emoji as icons
- large blue/purple cyber gradients
- dense tables as the main explanation
- external font dependencies

## Cover Image

Generate the cover with the host agent's `imagegen` tool by default. Treat `imagegen` as the primary path, not an optional enhancement. Prefer letting `imagegen` render the cover title directly when the title is short enough to specify verbatim. Use code/PIL/SVG only for resizing, export cleanup, tiny corrections, or as a fallback when `imagegen` is unavailable or unusable.

Default prompt:

> 白底专业技术架构图风格，主题是「{文章主题}」，包含清晰模块、箭头、分层结构、连接线和笔记感元素，中文标题区域留白，颜色使用深灰、墨绿、少量橙色，简洁、现代、工程感，不要人物，不要赛博朋克，不要复杂背景。

Recommended outputs:

- horizontal cover: 900x383
- square backup: 500x500

Repo-local final path rule:

- the chosen final cover must end up in the current project workspace, usually `assets/wechat/<slug>-cover-imagegen.png`
- do not treat a host preview, a chat-only image, or a cache-only file under `$CODEX_HOME/generated_images/...` as the final deliverable
- if `imagegen` returns or stores the image outside the repo, copy or decode the selected result into the workspace before any WeChat upload step

## Inline Illustration Types

Consume the writer's `正文插图` brief. Choose or generate an inline illustration only when it improves understanding:

- flow diagram: business input -> AI judgment -> human confirmation -> system action -> metric
- layer diagram: model, context, tool, workflow, governance
- comparison diagram: demo vs production, tool call vs responsibility boundary
- case map: scenario -> capability -> integration -> risk -> outcome
- high-fidelity product prototype: realistic enterprise UI or agent console showing how a named assistant would actually appear in use

Do not add decorative images.

If an article includes a named enterprise assistant or workflow screen and no real screenshot is available, prefer generating a `高保真系统原型图` in addition to any abstract structure diagram. The prototype should look like a believable SaaS product screenshot or Figma-level UI mockup, not a poster.

Generate accepted inline illustrations with the host agent's `imagegen` tool by default. Prefer this sequence:

1. Ask imagegen for a polished raster diagram in the account style with the required short Chinese labels already rendered in the image.
2. Save/copy the selected image into the project workspace, usually `assets/wechat/`.
3. Use local post-processing only for cropping, compression, export cleanup, or tiny corrections. Avoid large local text overlays because they look visually detached from the generated diagram.
4. Verify the final image visually before uploading to WeChat.

If the host `imagegen` path is not directly writable:

1. Check whether the tool already saved the output under a host cache path such as `$CODEX_HOME/generated_images/...`.
2. If yes, copy the selected file into the workspace with a stable article-specific name.
3. If the host call only exposed the image inside the current session record, decode/export that selected result into the workspace and then continue.
4. Only after those steps fail should you consider a documented non-imagegen fallback.

For high-fidelity prototypes:

1. Ask imagegen for a realistic enterprise software UI screenshot-style image.
2. Use Chinese UI labels whenever readability is important.
3. Make planning, execution, approval, and trace areas visible if the article discusses them.
4. Keep the visual tied to the concrete scenario in the article, such as 售后处置助手 or 投标助手.
5. If the full screenshot is too dense for mobile reading, crop or zoom the image locally to a focused version that keeps the key working area legible.

Prototype captions should state what the interface shows, not how it was made.

Do not use hand-drawn PIL/SVG/HTML diagrams as final assets when the host `imagegen` capability is available. Use those only when `imagegen` fails, is unavailable, cannot produce a usable result after iteration, or the user explicitly asks for deterministic code-native diagrams. If fallback is used, report the fallback reason in the audit package.

If the writer brief says no inline illustration is needed, do not invent one unless the article has a clear visual explanation gap.

For each accepted illustration, produce:

- final image prompt
- intended placement
- output path
- short alt/description text for the audit package

Use stable naming:

- cover: `assets/wechat/<slug>-cover-imagegen.png`
- inline pain chain: `assets/wechat/<slug>-pain-chain-imagegen.png`
- inline architecture: `assets/wechat/<slug>-architecture-imagegen.png`
- inline value loop: `assets/wechat/<slug>-value-loop-imagegen.png`
- inline prototype: `assets/wechat/<slug>-workbench-imagegen.png`

## Handoff To API

When a local repo has a draft API helper, use it only to save drafts, never to publish.

Expected artifacts:

- Markdown source
- cover image path
- optional inline image paths
- imagegen prompt(s) used for cover and illustrations, or fallback reason
- rendered HTML or API-created draft
- draft `media_id` if saved to WeChat

## QA

Before finishing:

- verify rendered content has `0` `<ul>` and `0` `<li>`
- verify title, digest, content, and thumb/cover exist
- verify colors match the style system
- verify cover and inline illustrations were generated by the host `imagegen` tool or have a documented fallback reason
- verify the final cover and inline images exist at repo-local output paths, not only in host cache or chat state
- verify no AppSecret or token is written into artifacts
