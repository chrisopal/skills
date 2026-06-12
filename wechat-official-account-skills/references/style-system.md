# 公众号排版与配图风格系统

适用账号：智能体架构笔记

## Visual Positioning

视觉语言应像一份工程架构笔记：

- 内容优先，少装饰。
- 纸面感、工程感、可收藏。
- 有清晰层级、编号、注释块、细线分隔。
- 统一使用墨绿、深灰、白底、少量橙色强调。

## Color Tokens

| Token | Hex | Usage |
| --- | --- | --- |
| Ink | `#1f2933` | 正文主色 |
| Muted | `#64716b` | 摘要、说明、脚注 |
| Soft | `#f6f8f6` | 标题区、信息块背景 |
| Line | `#dfe8e3` | 分隔线、边框 |
| Green | `#1f5b45` | 栏目标签、编号 |
| Green Dark | `#12372a` | 主标题、二级标题 |
| Orange | `#d97732` | 关键提示、引用左边框 |

## Typography

微信公众号正文使用系统字体栈：

```css
-apple-system, BlinkMacSystemFont, Helvetica Neue, PingFang SC,
Hiragino Sans GB, Microsoft YaHei, Arial, sans-serif
```

字号：

- 正文：16px / 1.86-1.9
- 摘要：15px / 1.75
- 二级标题：20px / 1.52
- 文章内标题：25px / 1.38
- 标签与编号：12-13px

## HTML Components

### Article Header

- 浅灰绿背景 `#f6f8f6`
- 1px 边框 `#dfe8e3`
- 顶部 5px 墨绿线
- 小标签：`AGENT ARCHITECTURE NOTE`
- 标题 + 摘要

### Section Heading

每个二级标题使用：

- 顶部分隔线
- `SECTION 01` 小标签
- 20px 墨绿标题

### Lists

不要使用原生 `<ul>` / `<li>`。

原因：微信编辑器和预览里容易出现空 bullet、间距失控、断行难看。

替代方案：

- 每个列表项渲染成独立浅底编号块。
- 左侧使用 `01`、`02`、`03`。
- 用 `section/span` 组合，而不是 `<ul>/<li>`。

### Quote / Key Question

- 左侧 4px 橙色线
- 浅橙背景
- 用于关键问题、判断或转折

### Footer

固定栏目签名：

> 智能体架构笔记，持续记录这一轮 AI 技术从能力走向系统、从演示走向企业真实流程。

## Cover Image

封面图默认通过 `imagegen` skill 生成 raster bitmap，再按需用本地脚本叠加准确中文标题。不要默认用手写 PIL/SVG/HTML 画封面，除非 imagegen 不可用或用户明确要求确定性图形。

封面统一方向：

- 白底专业技术架构图风格
- 主题关键词 8-14 字
- 分层结构、节点、箭头、连接线、笔记感元素
- 中文标题区域留白
- 深灰、墨绿、少量橙色
- 不要人物、赛博朋克、复杂背景、强蓝紫渐变

推荐尺寸：

- 微信封面横图：900x383
- 方图备份：500x500

## Inline Illustrations

正文插图默认通过 `imagegen` skill 生成统一风格 raster bitmap。插图的内容 brief 由写作 skill 给出，排版 skill 负责把 brief 转成 imagegen prompt、保存图片、必要时叠加短标签。

适合图型：

- 流程图：从输入到决策到行动到复盘
- 分层图：模型层、上下文层、工具层、流程层、治理层
- 对比图：demo vs 上线、工具调用 vs 权限边界
- 案例路径图：业务场景 -> AI 能力 -> 人类确认 -> 系统动作 -> 指标

图内文字要短，优先 4-6 个节点，不做密集表格。

生成原则：

- 优先让 imagegen 生成“无文字底图”，再用本地脚本叠加准确中文标签。
- 如果需要保留在图中的中文，必须人工或脚本复核文字准确性。
- 不使用纯代码绘制的占位图作为最终插图；代码绘图只适合流程验证或 imagegen 失败兜底。
- 图片保存到项目工作区，例如 `assets/wechat/`，不能只留在 imagegen 默认目录。

## QA Rules

交付前检查：

- 正文不含原生 `<ul>` / `<li>`。
- 标题层级明显，列表没有空 bullet。
- 封面与正文配色一致。
- 没有 emoji 作为图标。
- 没有大面积蓝紫科技风。
- 封面和正文插图来自 imagegen 或明确记录了 fallback 原因。
