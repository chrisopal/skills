# 宿主能力与图像接口

本技能不附模型 API、密钥或第三方服务。宿主名字不能证明能力存在；每次按当前可调用工具声明检查。

| 能力 | 用途 | 缺失时 |
|---|---|---|
| 文本生图 | 单页完整视觉设计 | 可先完成内容/主题任务，不能声称图片完成 |
| 带图编辑 | 清理背景、分离原有插画/图标等 | 复杂视觉页无法完成转换；先解决能力缺口 |
| 查看真实图片 | 生图审阅、素材检查 | 不得自动勾选视觉通过 |
| 保存/导入实际输出 | 固定页版本与素材来源 | 按工具支持的保存机制落地；不猜最新文件 |
| editppt 与渲染工具 | 重建、渲染与验证 | 在批量生图前按依赖安装说明解决 |
| 子 Agent | 多页重建 | 只有单页支持 local；多页需真实派发能力 |

## Codex

优先调用当前可用的 `image_gen.imagegen`；参数遵循本次工具声明，不复制旧版本的 model/size 参数。编辑前先查看输入图。全新页面不携带无关图片；延续风格时只加入本次需要的授权参考。转换使用 `--image-backend builtin-imagegen`，其回退条件仍由依赖的现有契约管理。

## WorkBuddy / Claude Code / 其他宿主

发现用户已配置的图像工具并读取生成、编辑两项声明；不硬编码平台专属工具名。记录一个 host-tool JSON：当前会话的发现证据、观察到的工具/参数、generate/edit 映射、输入和保存方式。准确字段见 image-to-editable-ppt 的 `references/manifest-schema.md` 中 **Native host-tool contract**，命令见其 `references/cli-helper.md`。

然后：

```bash
editppt prepare /实际路径/设计图.png --image-backend host-tool --image-backend-contract /实际路径/host-tool.json
```

host-tool 由 Agent 调用真实工具，CLI 只检查契约和记录来源，不会把工具名作为 shell 执行。契约中的名称仍需要 Agent 当场核对，JSON 校验并不能证明服务在线。失败不自动转向未配置的 API。

转换过程中产生的素材用 `editppt image import ... --backend host-tool --tool-name 实际工具名` 登记。源码目录中的新版 CLI 支持这个模式；安装了旧版时先更新 CLI，不能通过伪造 builtin-imagegen 名称绕过。

目前适配要求生成工具能接收明确文本提示，编辑工具能接收独立的提示与图片参数，并能按工具/宿主公开机制落地为明确本地文件。仅支持聊天上下文、没有可描述参数映射的插件需要额外适配；不承诺所有插件直接兼容。

OCR/图像编辑只使用任务所需资料，沿用当前用户对素材处理的约束。没有 OCR 时遵照依赖的离线/在线选择流程；本技能保留原稿文字有助于纠错，但不替代位置、字体和图形结构识别。
