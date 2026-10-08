---
name: xiaohongshu-skill
description: 小红书 / Xiaohongshu / RedNote 浏览器技能。搜索和读取内容，管理登录，按清单准备视频、封面、正文和草稿，发布图文、视频与长文。需要小红书发布、运营或笔记读取时使用；公开提交及互动须有用户明确授权。
license: Apache-2.0
metadata:
  compatibility: Requires Python 3.10 or newer and Playwright Chromium. Supports Windows, macOS, and Linux.
  openclaw:
    emoji: "📕"
    requires:
      anyBins:
        - python3
        - python
    os:
      - win32
      - linux
      - darwin
---

# 小红书 Skill

本版本由 Chrisopal/skills 维护；来源与上游版本见 [UPSTREAM.md](UPSTREAM.md)。

通过 JSON CLI 操作小红书浏览器会话。执行入口统一为：

```bash
cd {baseDir}
uv run python -m scripts <command>
```

## 安全规则

发布、评论、回复、点赞、收藏、取消点赞和取消收藏会改变真实账号状态。执行前必须：

1. 展示目标账号、内容、媒体和操作类型。
2. 获得用户明确确认。
3. 只执行用户确认的单次操作。

用户已明确授权的同一次操作不重复确认。用户要求准备素材或检查发布能力时，可以上传、填写和保存草稿；这不代表授权公开提交。用户告知已手动发布后立即停止该笔记的自动提交，并记录状态。

遇到验证码、登录页或安全验证页时停止。不要自动绕过验证，不要运行批量抓取或批量互动。

## 任务路由

| 用户目标 | 命令或参考 |
| --- | --- |
| 首次登录或重新登录 | `qrcode --headless=false` |
| 检查登录 | `check-login` |
| 管理多个账号 | `--profile <name>`；详见 `docs/INSTALL.md` |
| 搜索笔记 | `search` |
| 读取笔记详情 | `feed` |
| 读取用户主页 | `user` 或 `me` |
| 获取推荐流 | `explore` |
| 准备或发布图文 | `publish` |
| 准备或发布视频 | `publish-video` |
| Markdown 转图片发布 | `publish-md` |
| 准备或发布长文 | `publish-longform` |
| 评论和回复 | `comment`、`reply`、`reply-notification` |
| 点赞和收藏 | `like`、`collect`、`unlike`、`uncollect` |
| 模板、策略和 SOP | `template`、`strategy-*`、`sop` |
| 查看参数 | `python -m scripts <command> --help` |

完整命令见 `docs/API.md`；安装和平台接入见 `docs/INSTALL.md`、`docs/INTEGRATIONS.md`。

## 视频与封面一起准备

已有视频、封面和文案时，优先使用发布清单，避免逐项复制或重新上传。详见 [视频工作流](docs/VIDEO_WORKFLOW.md) 和 [清单示例](examples/video-manifest.json)。

```bash
uv run python -m scripts publish-video --manifest /path/to/job.json --preflight
uv run python -m scripts publish-video --manifest /path/to/job.json --headless=false
```

- 清单带入账号、完整标题、正文、标签、视频、封面及可见范围；相对文件路径按清单目录解析。
- 先做本地预检；只有草稿保存成功才返回 `draft_saved`。恢复清单时优先打开已有草稿，标题不唯一时停止，不猜选。
- 标签默认作为准确的 `#话题` 文本加入正文，不选择模糊联想首项；不要将文本标签说成已绑定平台话题。
- 封面通过实际编辑器上传，正文替换后读回校验。上传超时或封面解析失败必须报错，不能当成准备完成。
- 已准备的清单可在用户授权后加 `--auto-publish`；不要为了确认而重新生成清单。
- 用户手动发布后：`uv run python -m scripts publish-video --manifest /path/to/job.json --record-published`。这是用户报告，不是独立的发布验收。
- 清单旁保存任务状态，profile 目录保存按内容指纹索引的发布账本；改名或复制清单也不能重复提交已发布及结果不确定的任务。更换账号、素材或文案后使用新清单重新核对；不要删除状态绕过重复提交保护。

## 初始化

```bash
cd {baseDir}
uv sync --frozen --no-dev
uv run playwright install chromium
uv run python -m scripts qrcode --headless=false
```

开发者使用：

```bash
uv sync --frozen --group dev
uv run python -m scripts.quality check
```

## 只读示例

```bash
uv run python -m scripts search "咖啡" --limit=5
uv run python -m scripts feed <feed_id> <xsec_token>
uv run python -m scripts explore --limit=10
```

`feed_id`、`user_id` 和 `xsec_token` 必须来自当前会话的结果，不要长期缓存。

## 发布语义

图文及长文命令默认填写表单并返回 `ready`。视频命令默认保存草稿并返回 `draft_saved`，浏览器关闭后仍可恢复。公开提交需要用户明确授权；确认后才能追加 `--auto-publish`。

自动提交可能返回：

- `confirmed`：已观察到可信成功信号。
- `submitted_unconfirmed`：已点击提交但未确认成功；必须人工复核，禁止自动重试。
- `failed`：提交失败或出现登录、验证码、安全验证等失败信号。

## 输出和错误

标准输出是 JSON；诊断信息写入标准错误。Agent 应先读取 `status`，再依据 `scripts/output_contracts.py` 中的契约处理字段。

发生 `captcha_required` 或浏览器安全验证时，不要重试循环。切换到有头模式并由用户处理。

## 本地状态

每个 profile 独立保存浏览器状态、Cookie 备份和会话元数据。不要读取、展示、提交或外发这些文件。`XHS_FP_SEED` 只用于显式覆盖当前进程的稳定指纹 seed。

安全和隐私规则见 `docs/SECURITY.md`。架构说明见 `docs/ARCHITECTURE.md`。
