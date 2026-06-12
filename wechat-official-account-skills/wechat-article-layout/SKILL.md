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

Default prompt:

> 白底专业技术架构图风格，主题是「{文章主题}」，包含清晰模块、箭头、分层结构、连接线和笔记感元素，中文标题区域留白，颜色使用深灰、墨绿、少量橙色，简洁、现代、工程感，不要人物，不要赛博朋克，不要复杂背景。

Recommended outputs:

- horizontal cover: 900x383
- square backup: 500x500

## Inline Illustration Types

Choose one only when it improves understanding:

- flow diagram: business input -> AI judgment -> human confirmation -> system action -> metric
- layer diagram: model, context, tool, workflow, governance
- comparison diagram: demo vs production, tool call vs responsibility boundary
- case map: scenario -> capability -> integration -> risk -> outcome

Do not add decorative images.

## Handoff To API

When a local repo has a draft API helper, use it only to save drafts, never to publish.

Expected artifacts:

- Markdown source
- cover image path
- optional inline image paths
- rendered HTML or API-created draft
- draft `media_id` if saved to WeChat

## QA

Before finishing:

- verify rendered content has `0` `<ul>` and `0` `<li>`
- verify title, digest, content, and thumb/cover exist
- verify colors match the style system
- verify no AppSecret or token is written into artifacts

