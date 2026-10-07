# 安装与配置

## 安装 / 更新

本目录是 `chrisopal/skills` 中保留 portable-backend 和 visual-QA 定制的版本。请从包含这些定制的已审查 fork 提交安装，安装包路径为 `image-to-editable-ppt/skills/image-to-editable-ppt/`。

将 `<fork-commit>` 替换为包含本地定制的已审查提交 SHA，将 `<agent-id>` 替换为当前智能体标识（例如 `codex`），将 `<skill-root>` 替换为实际安装目录。不要假定默认分支已包含这些定制，也不要用上游发行 ZIP 覆盖本版本。

```bash
npx -y skills@latest add "https://github.com/chrisopal/skills/tree/<fork-commit>/image-to-editable-ppt/skills/image-to-editable-ppt" \
  --skill image-to-editable-ppt \
  --agent <agent-id> \
  --global
pipx install --force --editable <skill-root>/cli
editppt doctor
editppt page visual-qa --help
editppt image extract-source --help
editppt run backend --help
```

更新后重新加载技能上下文，确认 `run backend --help` 中仍有 `agent-image-tool`，且 visual-QA 与提取命令可用。API 凭据和 OCR Token 保存在技能目录之外的 `~/.editppt/config.yaml`。CLI 默认模型已升级为 `gpt-image-2.5-sunburst`；显式配置的模型不会被更新过程覆盖。

模型默认值适用于 `editppt image` CLI。可用 `editppt config --model gpt-image-2.5-sunburst` 更新已保存的旧模型设置；单次请求可用 `--model gpt-image-2.5-flare`、受支持的日期快照或服务商命名空间（如 `openai/gpt-image-2.5-sunburst`）。显式 `--model` 优先于环境变量，环境变量优先于配置文件；显式选择 `gpt-image-2` 仍有效。`--quality` 默认保留 `auto`；新增 `xhigh`、`max` 仅适用于 2.5 Sunburst/Flare。原生图片工具使用其自身提供的模型，不向 Codex 内置工具传入 `model`。具体服务是否开放所选模型仍取决于账号和服务商。

## 从本地 checkout 安装

已检出并验证目标 fork 提交时，也可用本地技能目录安装；随后执行上面的 CLI 刷新和检查。

```bash
npx -y skills@latest add /path/to/chrisopal-skills/image-to-editable-ppt/skills/image-to-editable-ppt \
  --skill image-to-editable-ppt --agent <agent-id> --global
```

## 运行权限建议

**建议在 Codex 中使用「完全访问权限」执行本 skill。**

本 skill 运行时间较长，并且会自动执行 OCR、图片生成/编辑、文件读写、子 agent 分派和长时间轮询等步骤。「请求批准」模式会频繁打断执行，可能阻塞部分步骤，尤其是在子 agent 环境里。「替我审批」模式已知仍可能在 OCR 阶段、图片生成/编辑阶段或第三方 API 调用阶段拦截请求，要求你手动审批；如果你不在电脑旁，转换流程会停住。

![Codex 完全访问权限设置示意](https://raw.githubusercontent.com/ningzimu/image-to-editable-ppt-skill/main/assets/codex-full-access-permission.png)

## 运行要求

- 单页/单图输入不需要创建 page worker，由主 agent 本地执行同一页面重建流程。
- 多页输入需要 agent 能分派 page worker/subagent；如果当前环境不能创建 page worker，应换到支持 page worker 的环境执行。
- 本 skill 依赖的 `editppt` 命令行工具是 AI 在执行 skill 的过程中自动安装的，不需要你手动执行任何命令。
- 受限于模型基础理解能力和对 skill 的遵循能力，不保证 gpt-5.5 以下模型的使用效果。

## OCR Token（推荐配置）

本 skill 通过第三方 OCR 服务（百度 PaddleOCR-VL）来校正文字的大小和位置，显著提升文字还原质量，原理参见[设计理念](design.md)。

**你只需要做一个动作——申请 Token**：到百度 AI Studio 申请 Access Token：<https://aistudio.baidu.com/account/accessToken>。对个人使用来说，目前免费额度完全够用，可以放心申请，无额外费用。

首次使用时如果还没配置 Token，AI 会主动询问你一次——把申请到的 Token 发给它即可，AI 会帮你写入用户级配置（`~/.editppt/config.yaml`，遮蔽存储），一次配置长期生效，之后不再提示。

不提供 Token 也能运行：skill 会退化为内置的离线检测器（纯几何测量，不识别内容），文字还原质量会有折扣。

## 图片 Backend 与第三方 API 配置

图片生成和编辑默认优先调用 Codex 内置 `image_gen.imagegen`。在 WorkBuddy、Claude Code、QoderWork 或其他智能体中，skill 会发现 Tool、Skill、Plugin、MCP/Connector 和已配置图片模型；候选必须同时支持文生图、参考图编辑和明确本地输出，否则使用默认模型为 `gpt-image-2.5-sunburst` 的 `editppt image` CLI。CLI 优先使用本机 Codex OAuth（`~/.codex/auth.json`），不可用时再读取 OpenAI-compatible API 配置。

WorkBuddy 的 ImageGen 和 QoderWork 的 `/gen-image`/remix 需要在安装环境中确认参考图编辑契约；Claude Code 官方只确认图片理解，因此通常需要额外图片 Skill/Plugin/MCP，或直接使用 CLI fallback。只会“看图”的视觉模型不能作为图片 backend。

通常不需要你自己配置。只有这些情况才需要让 AI 帮你配置 API fallback：

- 你明确要求使用第三方 API 或 OpenAI 兼容中转站。
- 在 WorkBuddy、Claude Code、QoderWork 等环境中使用，没有通过能力校验的原生图片工具，也没有可用的 Codex OAuth auth。
- `editppt image` 报告 Codex OAuth 和 `OPENAI_API_KEY` 都不可用。

如果需要第三方 API fallback，告诉 AI 你要使用的服务、base URL、模型名和 API key 即可。AI 会在执行过程中完成环境检查和配置写入，把凭据保存在用户级配置 `~/.editppt/config.yaml`，并在输出里遮蔽敏感值。不要把 API key 写进项目目录、run 目录或 skill 目录。

Codex OAuth 路径依赖本机 Codex auth 和订阅侧图片额度；API fallback 依赖所选 OpenAI-compatible 服务的图片生成/编辑能力。多页转换还要求 page worker 能访问同一原生图片工具，否则整次运行统一使用 CLI。
