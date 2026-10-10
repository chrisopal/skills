---
name: visual-to-editable-ppt
description: Use when a user provides a presentation outline, per-slide content and style and wants visually polished AI-designed slides delivered as an editable PPTX. 适用于咨询汇报、产品解决方案、营销、年会，以及“先生成漂亮图片再转可编辑PPT”；已有图片只做转换时用 image-to-editable-ppt。
---

# 视觉优先可编辑 PPT

将已确认内容做成单页设计图，再重建为可编辑 PPTX。设计图是中间产物；最终同时检查内容、视觉和可编辑性。文字与普通结构是原生对象，照片/插画是独立可替换图片；不承诺所有视觉都能变成矢量。

## 入口与依赖

输入：整套大纲、每页标题/正文/数字/图表数据、视觉主题或参考页。接受自然语言和文档，由 Agent 整理为内容包，不要求用户手填 JSON。缺内容时先列具体缺口；不为了“好看”补未经确认的结论。

本技能复用两项依赖，不复制转换引擎：
- `consulting-ppt-image`：内容 schema、页 ID、init/register/review/select/sync/audit。
- `image-to-editable-ppt`：图像拆分、原生对象重建、页级派发、record/finalize。

从宿主技能目录或仓库定位并读取依赖。仓库中的第二项入口是 `image-to-editable-ppt/skills/image-to-editable-ppt/SKILL.md`。独立安装时需要同时安装这两项；路径不同用 `--consulting-root` 指定。首次运行读 [安装与示例](README.md) 和 [宿主能力](references/host-tools.md)。在生图前确认转换运行时、图像编辑能力、渲染能力和多页子 Agent 能力；避免全部图片生成后才发现无法转换。

## 制作流程

1. **内容锁定。** 采用依赖的 `slide-content-pack` schema，保留原文、单位、图表数据、节点/连线和来源。`review_status` 与 `approval_ref` 记录真实已有确认；不重复索取已给出的确认。[内容交接](references/content-handoff.md) 定义额外的显示文字与转换映射。
2. **风格与代表页。** 按 [主题目录](references/themes.md) 选择一套主题，已有参考优先。通常先做封面、密集内容、图解三类代表页；短稿按实际页面选择。代表页也必须完成可编辑重建与渲染比较，再扩大批次。生成范围由实际 `order` 决定，稳定 ID 不变。
3. **初始化与提示词。** 用依赖的 `init --style` 锁定主题。用本技能 `scripts/visual_bridge.py plan` 生成逐页任务；不调用旧 `plan`，它包含固定墨绿要求。草稿只用 `--draft` 查结构，禁止当生产任务执行。主题字段决定视觉审校，原技能白底墨绿专属 QA 不适用于其他主题。
4. **宿主逐页生图。** 读取当前工具真实声明，调用原生生图工具，一次一页。每次返回立即保存、register；工具成功不等于图片通过审阅。Codex 用内置 Image Gen，其他宿主通过已发现的工具与 `host-tool` 转换契约衔接，细节见宿主参考。生成与编辑能力分别检查。
5. **检查并选版。** 逐页查看真实图片，核对内容、图形关系、主题、页码、阅读性和来源，填写依赖的七项 review。用户确认或明确代审授权后 select；已有授权可覆盖批次，无需每页重复询问。图片里有错字/错数先修复设计图；转换仍以原始内容为准。
6. **转换衔接。** 使用 `handoff` 导出已选图片、完整逐页内容、主题和哈希。部分稿显式传 `--range`。转换前运行 `verify-handoff`，随后按 [转换流程](references/editable-conversion.md) 调用 editppt，给每个页 Agent 传对应内容文件。不得调用旧 `assemble` 作为本技能最终交付。
7. **最终验收。** 依赖完成 record/finalize 后运行 `audit-pptx`，再按 [质量检查](references/quality.md) 查看最终渲染与设计图。改一个文本框、一个结构对象，保存重开验证编辑性；只修改验证副本。未做视觉检查就报告“待视觉验收”，不得用机器通过代替。

## 续做与修改

- 续做先读图像 manifest 和 editppt 的 `run next`，不扫描目录猜最新图片。
- 内容/顺序改动通过依赖 `sync`；主题改动新建已批准主题项目。变化后的受影响页重新生成、审阅和选版。
- 旧转换不会被自动同步。`verify-handoff` 失败时不继续旧 run，先恢复图像选版，再创建新版本 handoff/run，保留旧版。
- 失败重试限于当前页；同原因连续两次失败先诊断工具/输入/环境，不盲目继续烧额度。不绕过 dependency 的 page reset/lease 规则。
- 单页可用 editppt local 模式；多页按真实宿主并发上限派发，不虚构 Agent ID。缺少多页派发能力时明确缺口。

## 交付

提供可编辑 PPTX、预览及简短说明：页数/部分范围、可编辑对象与保留位图、主题、验证状态。图片、审校记录和中间工作区默认留在项目目录；不把内部联系表当成演示稿。

主质量目标：布局有层级、有变化、符合用途，成品文字清晰，结论/数字准确，修改对象不会露出重复底图。具体失败判断见质量参考。
