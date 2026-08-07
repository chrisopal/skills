# Agent Image Backends

Scope: official first-party docs only, current as of 2026-08-07. "Unsupported" means I did not find a first-party doc that confirms the capability.

Note: Qoder docs use `QoderWork` as the desktop assistant name. I did not find an official product named "Qoder Worker".

## Capability Matrix

| Runtime | Official product name | Prompt-to-image | Reference-image editing | Local output path | Agent-callable image backend | Skills / plugins / MCP | Version / support note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Tencent WorkBuddy | WorkBuddy Enterprise / WorkBuddy | Yes | Partial - official Tencent material describes `ImageGen` as `文生图/图生图`, and WorkBuddy articles describe using it for image-to-image style workflows; I did not find a public tool schema for mask/size/model controls. | Yes - official Tencent article says generated images are saved to the workspace directory by default. | Yes - the skill contract uses the built-in `image_gen.imagegen` tool, and WorkBuddy release notes mention `ImageGen/VideoGen` tool descriptions. | Yes - Skills, connectors, experts, and plugin/connector integration are documented. | Current docs mention ImageGen/Skill UI updates in 5.2.6 and 5.3.3; the ImageGen prompt/image-to-image article is newer. No public low-level API contract found. |
| Anthropic Claude Code | Claude Code | No documented native image generation backend. | No documented native image editing backend. | N/A for native image backend. | No native image tool found. Claude Code can accept images for analysis and can extend via tools, MCP, skills, and plugins, but the docs do not describe a built-in image generator/editor. | Yes - skills, plugins, MCP, hooks, subagents, and built-in file/search/exec/web tools are documented. | Vision supports image input and analysis only. If image generation/editing exists, I did not find it in first-party docs. |
| Qoder / QoderWork | QoderWork | Yes - `/gen-image` generates images from a natural-language description. | Partial - QoderWork documents AI image remix workflows that keep brand style/color and change the scene, but I did not find a generic reference-image edit API or explicit mask workflow. | Yes - generated images can be downloaded locally, and QoderWork is a local desktop app with direct file access. | Yes - the image command is callable from chat/agent flow. | Yes - skills, plugins, connectors, MCP, hooks, commands, and scheduled tasks are documented. | Current docs are versionless. Treat image-remix support as partial unless a future doc adds a formal edit contract. |

## Discovery Rules For An Agent

1. Require all four properties before treating a backend as usable for `image-to-editable-ppt`: prompt-to-image, reference-image editing, local output path, and agent-callability.
2. Treat "vision only" products as non-backends for this skill. Image analysis is not enough.
3. If docs mention only image generation, do not assume reference-image editing.
4. If docs mention remix/variant generation from a reference image but do not show a formal edit API, mark the backend `partial`.
5. Accept a backend only when the agent runtime can call it directly. A manual UI-only feature is not enough.
6. Prefer explicit local file paths returned by the tool. Do not infer the newest file in a directory.
7. Re-check product docs for version gates before enabling a backend. For Claude Code, some skill behaviors are version-gated (`v2.1.200+` / `v2.1.203+` in the docs); for WorkBuddy, image-related changes appear in 5.2.6 and 5.3.3 release notes.

## Source URLs

- https://cloud.tencent.com/document/product/1831/134324
- https://cloud.tencent.com/document/product/1831/134384
- https://cloud.tencent.com/document/product/1831/134391
- https://cloud.tencent.com/document/product/1831/134420
- https://cloud.tencent.com/document/product/1831/134432
- https://cloud.tencent.com/document/product/1831/134453
- https://cloud.tencent.com/document/product/1831/134525
- https://developer.cloud.tencent.com/article/2719751
- https://docs.anthropic.com/en/docs/claude-code/overview
- https://docs.anthropic.com/en/docs/claude-code/skills
- https://docs.anthropic.com/en/docs/claude-code/mcp
- https://docs.anthropic.com/en/docs/claude-code/plugin-marketplaces
- https://docs.anthropic.com/en/docs/build-with-claude/vision
- https://docs.qoder.com/qoderwork/introduction
- https://docs.qoder.com/user-guide/chat/tools
- https://docs.qoder.com/qoderwork/user-stories/case-18
- https://docs.qoder.com/qoderwork/skills
- https://docs.qoder.com/extensions/plugins
- https://docs.qoder.com/qoderwork/connectors
- https://docs.qoder.com/qoderwork/quick-start
