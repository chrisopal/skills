# 宿主能力与图像接口

本技能不附模型 API、密钥或第三方服务。宿主名字不能证明能力存在；每次按当前可调用工具声明检查。

| 能力 | 适用模式与用途 | 缺失时 |
|---|---|---|
| 文本生图 | 两种模式：单页完整视觉设计 | 先完成内容/主题任务，不能声称图片完成 |
| 查看真实图片 | 两种模式：生图审阅、素材检查 | 不得自动勾选视觉通过 |
| 保存/导入实际输出 | 两种模式：固定页版本与素材来源 | 按工具支持的保存机制落地，不猜最新文件 |
| PPTX 打开与渲染工具 | 两种模式：查看实际成稿 | 明确待实际渲染验收，不用机器通过替代 |
| 带图编辑/素材分离 | editable：清理背景、拆出原有插画/图标 | 转换前解决相关能力缺口；image 不因缺少拆图能力受阻 |
| editppt 转换 CLI | 仅 editable：原生对象重建与结构校验 | 批量生图前按依赖说明安装 |
| 子 Agent | 仅 editable：多页重建 | 单页支持 local，多页需真实派发能力 |

用户明确选择 `image` 后，不要求安装 editppt、host-tool 转换契约或准备重建子 Agent。图片仍需生图、人工/授权代审、选版、handoff、export-images/audit-images 和实际渲染；有错误的整页图片可以按宿主能力编辑或重生成。默认 editable，不能把其能力缺口或执行失败作为自动降级图片版的理由。

## Codex

优先调用当前可用的 `image_gen.imagegen`；参数遵循本次工具声明，不复制旧版本的 model/size 参数。编辑前先查看输入图。全新页面不携带无关图片；延续风格时只加入本次需要的授权参考。仅 editable 转换使用 `--image-backend builtin-imagegen`，其回退条件仍由依赖的现有契约管理。

## WorkBuddy / Claude Code / 其他宿主

发现用户已配置的图像生成工具并读取声明；不硬编码平台专属工具名。image 路径直接将明确返回的本地图片 register，无需下述转换契约。

仅 editable：另外核对编辑能力，并记录一个 host-tool JSON：当前会话的发现证据、观察到的工具/参数、generate/edit 映射、输入和保存方式。准确字段见 image-to-editable-ppt 的 `references/manifest-schema.md` 中 **Native host-tool contract**，命令见其 `references/cli-helper.md`。

然后：

```bash
editppt prepare /实际路径/设计图.png --image-backend host-tool --image-backend-contract /实际路径/host-tool.json
```

host-tool 由 Agent 调用真实工具，CLI 只检查契约和记录来源，不会把工具名作为 shell 执行。契约中的名称仍需要 Agent 当场核对，JSON 校验并不能证明服务在线。失败不自动转向未配置的 API。

转换过程中产生的素材用 `editppt image import ... --backend host-tool --tool-name 实际工具名` 登记。源码目录中的新版 CLI 支持这个模式；安装了旧版时先更新 CLI，不能通过伪造 builtin-imagegen 名称绕过。

目前适配要求生成工具能接收明确文本提示，编辑工具能接收独立的提示与图片参数，并能按工具/宿主公开机制落地为明确本地文件。仅支持聊天上下文、没有可描述参数映射的插件需要额外适配；不承诺所有插件直接兼容。

editable 的 OCR/素材编辑只使用任务所需资料，沿用当前用户对素材处理的约束。没有 OCR 时遵照依赖的离线/在线选择流程；本技能保留原稿文字有助于纠错，但不替代位置、字体和图形结构识别。

## WorkBuddy 实测边界（2026-10-11）

WorkBuddy 5.6.2、Deepseek-V4.1-Flash 的实际会话已发现并加载本技能和两个依赖；本地安装目录为 `~/.workbuddy/skills/`。本次发现的工具名是 `ImageGen`，生成输入为 `prompt`，明确落盘路径来自返回值 `images[].localPath`；`image1` 是其声明的编辑输入参数。这些只是本次发现结果，后续仍按当前工具声明核对，不能硬编码。

单页蓝色咨询通用样稿已实际生图，并走通图片版与可编辑版、交接/内容/备注审计、实际字号回读和LibreOffice渲染。可编辑版7个原生文本框、5个结构对象；正文20pt、标题32pt、标签24pt。此页没有复杂插画，未实跑图像编辑/素材分离，也未验证WorkBuddy多页子Agent派发或其他主题。

首次生图连接重置，第二次成功；PaddleOCR返回500后采用内置位置提示结合已确认原文。LibreOffice全局配置触发文件保护时，采用任务独立配置后渲染成功，见[质量检查](quality.md)。可编辑副本通过程序修改文字、字号及面板位置，保存/回读并重新在LibreOffice渲染；不将其表述为WorkBuddy执行了PowerPoint界面编辑。测试产物留本地，不随技能安装。
