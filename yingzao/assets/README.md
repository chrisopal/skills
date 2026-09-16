# 资产分层

- `reference-plates/`：较大参考图，供 `design_tokens.py recipe <id> --json` 返回并作为图像模型的主导参考输入。
- `reference-thumbnails/`：同名轻量预览，供 HTML Token 目录快速浏览；不作为高风格化任务的首选模型输入。
plates 与 thumbnails 保留相同文件名是有意的质量分层，不是两套独立参考库。新增或删除参考时必须同步文件集合；目录渲染不应为预览加载整套大图。
