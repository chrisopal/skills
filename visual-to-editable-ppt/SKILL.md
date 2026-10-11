---
name: visual-to-editable-ppt
description: Use when a user provides a presentation outline, per-slide content and style and wants AI-designed slides as an editable PPTX or explicitly chooses an image-only PPTX. 适用于咨询汇报、产品方案、营销、年会及先生成设计图再制作PPT；已有图片只做可编辑转换时用 image-to-editable-ppt。
---

# 视觉优先 PPT：可编辑或图片型

将已确认内容做成单页设计图，再按用户选择交付 PPTX。未指定时默认 `editable`：重建原生文字与普通结构，照片/插画作为独立可替换图片，不承诺全部视觉变成矢量。用户明确选择 `image` 时，每页保留一张完整设计图，整图可替换，图中文字和结构不能单独编辑。不得因转换失败或缺少转换能力擅自改交图片版。

## 入口与依赖

输入：整套大纲、每页标题/正文/数字/图表数据、视觉主题或参考页。接受自然语言和文档，由 Agent 整理为内容包，不要求用户手填 JSON。缺内容时列具体缺口，不补未经确认的事实。

两条路径都依赖 `consulting-ppt-image` 的内容 schema、页 ID、init/register/review/select/sync/audit。仅 `editable` 还依赖 `image-to-editable-ppt` 的素材分离、原生对象重建、页级派发和 record/finalize；仓库入口是 `image-to-editable-ppt/skills/image-to-editable-ppt/SKILL.md`。`image` 不需要转换 CLI、拆图、原生对象重建或多页重建子 Agent。

首次运行读 [安装与示例](README.md) 和 [宿主能力](references/host-tools.md)。定位所选路径的依赖；consulting 路径不同时使用脚本全局参数 `--consulting-root`。生图前核对生成、查看、保存和最终渲染能力；仅可编辑路径额外检查转换运行时、图像编辑及多页派发能力。

## 制作流程

1. **内容锁定。** 采用依赖的 `slide-content-pack` schema，保留原文、单位、图表数据、节点/连线和来源。`review_status` 与 `approval_ref` 记录真实已有确认，不重复索取已给出的确认。[内容交接](references/content-handoff.md) 定义显示文字、备注和逐页映射。
2. **主题与代表页。** 按 [主题目录](references/themes.md) 选择主题，已有参考优先。按[字号规则](references/typography.md)区分正文、标签和封面，以最终PPTX的显式pt为准；默认微软雅黑（`Microsoft YaHei`），普通正文/图内节点/图表与表格标签14pt（四号）、副标题16pt、模块短标题18pt、内容标题28pt、页脚12pt，封面另定。以常规字重为主，短标签不放大填空间。此为中文密集商务稿偏好，不宣称14pt符合18pt无障碍建议；用户品牌/大屏规范优先。微软雅黑未安装或应用不能解析时报告缺口，不得静默替换。通常先做封面、密集内容、图解三类代表页；短稿按实际页面选择。代表页须走完所选输出路径并查看实际 PPTX 渲染：editable 检查重建，image 检查整图导出。之后再扩大批次。范围由实际 `order` 决定，稳定 ID 不变。
3. **初始化与提示词。** 用依赖 `init --style` 锁定主题，再用 `scripts/visual_bridge.py plan --output-mode editable` 或 `--output-mode image` 生成任务；省略时默认 editable。队列记录 `output_mode` 和当前 `typography` 目标，不修改图像选版。草稿仅用 `--draft` 查结构，禁止执行生图。不调用带固定墨绿要求的旧 plan；主题字段决定风格审校。
4. **宿主逐页生图。** 读取当前工具声明，一次一页。每次返回立即保存、register；调用成功不等于图片通过审阅。Codex 用内置 Image Gen，其他宿主使用已发现的生成能力；仅可编辑转换需要 `host-tool` 编辑契约，细节见宿主参考。
5. **检查并选版。** 逐页查看真实图片，核对内容、关系、主题、页码、阅读性和来源，填写依赖七项 review。按用户确认或明确代审授权 select，已有批次授权无需每页重复询问。图片里有错字/错数先修复设计图；图片版直接保留这些像素，可编辑重建也仍以原稿为准。
6. **共同交接。** 用 `handoff` 导出已选图片、逐页内容、主题、哈希和备注载体；部分稿显式传 `--range`。两条路径都先运行 `verify-handoff`，不改写已有交接目录。
7. **按模式导出并验收。** editable 按 [转换流程](references/editable-conversion.md) 执行 editppt，向每个页 Agent 传内容文件；record/finalize 后运行 `audit-pptx`。image 用 `export-images --project … --output 交接目录 --pptx 新成稿路径.pptx`，再运行 `audit-images`。不得把 `conversion-input.pptx` 改名当成成稿，也不使用旧 assemble 跳过本技能校验。按 [质量检查](references/quality.md) 查看最终实际渲染；可编辑版还须在副本中修改文字和结构对象并保存重开。未执行的验收明确标为待完成。

## 续做与修改

- 先读图像 manifest；editable 另读 editppt 的 `run next`，不扫描目录猜最新版本。
- 内容/顺序改动通过 `sync`；主题改动新建主题项目。变化后的受影响页重新生成、审阅、选版。
- `verify-handoff` 失败时先恢复有效选版，再创建新 handoff 和新成稿；editable 创建相应新 run。旧版保留，无变化可继续原 run。
- 同原因连续两次失败先诊断工具、输入和环境，不盲目重试或切换输出模式。editable 不绕过 page reset/lease；多页按真实宿主并发上限派发，缺少能力时明确缺口。

## 交付

提供所选模式的 PPTX、预览及简短说明：模式、完整/部分范围、页数、主题、实际验证状态。editable 说明原生对象与保留位图；image 明确每页整图、内部文字不可编辑。图片、审校记录和工作区默认留在项目目录，不把联系表或转换载体当成演示稿。机器通过、实际视觉检查、编辑保存重开和用户业务验收分别记录。
