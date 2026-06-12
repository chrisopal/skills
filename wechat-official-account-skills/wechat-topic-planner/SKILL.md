---
name: wechat-topic-planner
description: Use to plan topics for the WeChat Official Account 智能体架构笔记, especially AI technology explanations, enterprise AI landing cases, failure reviews, and business model innovation. Produces topic candidates, recommendation rationale, audience fit, and article angle.
---

# WeChat Topic Planner

Use this skill when selecting or refining topics for the WeChat Official Account `智能体架构笔记`.

Read `../references/account-positioning.md` before planning topics.

## Mission

Choose topics that help the account do two things:

1. 把这一轮 AI 技术讲明白。
2. 把 AI 在企业里的真实发生讲清楚。

“智能体” is the entry point, not the narrow boundary. Topics may cover large models, Agent, workflow, RAG, MCP, harness engineering, agent skill, tools, memory, evaluation, permissions, and enterprise adoption.

## Workflow

1. Inspect recent drafts, published articles, or the current operation plan if available.
2. Generate 3-5 candidate topics.
3. For each topic, state:
   - target reader
   - why now
   - article promise
   - likely share/collection reason
   - search keywords
   - risk of being too generic
4. Pick one recommended topic and explain why.
5. Produce a compact brief for the writer.

## Topic Filters

Prefer topics that:

- connect technology to a real enterprise workflow
- explain a confusing technical concept without becoming a glossary
- include a success case, failure review, or reusable pattern
- can be supported by a diagram or concrete scenario
- are valuable even if a specific tool becomes outdated

Avoid topics that:

- only summarize product releases
- only compare tools without a business implication
- promise AI replacement without discussing workflow and responsibility
- require facts that cannot be verified

## Output Format

```markdown
## 候选选题

1. 题目
   - 读者：
   - 为什么现在写：
   - 文章承诺：
   - 传播/收藏点：
   - 搜索关键词：
   - 风险：

## 推荐选题

标题：
一句话角度：
推荐理由：

## 写作 Brief

- 核心读者：
- 核心问题：
- 必讲观点：
- 案例/场景：
- 图解建议：
- 不要写成：
```

