# 原始内容与转换交接

沿用 consulting-ppt-image 的 `schemas/slide-content-pack.schema.json`。
基本字段：deck_id/version/page_budget/theme_profile/approval_ref/sections/slides/citation_index。
每页保留 slide_id/order/title/key_message/supporting_points/visual_type/review_status、来源与限定语。

- `diagram_spec`：保留节点、关系、箭头方向。
- `chart_spec`：保留真实数据、系列名、类别、单位和显示格式，不以生成图的高度/面积反推数值。
- `speaker_notes`：保留原稿备注；向转换传单张图不会自动带备注，必须按转换参考明确传入。
- `visible_text`（本技能可选扩展）：已确认要实际展示的字符串列表，含标题、正文、图表标签/数字/单位、限定语。用于最终 PPT 原生文本核对。只有原稿确实确定这些显示文字时才建立；不得在验收失败后删掉缺失字符串来凑通过。

没有 visible_text 时，机器核对标题、主结论、支撑点、限定语、diagram 节点/边标签。图表数据和受保护数值仍需逐项审阅；“原生文本存在”不能证明图形准确或文字可见。

`visual_bridge.py handoff` 的输入是选版完毕的图像项目。它复制原图，不调用模型、不修改图像/转换状态：

```text
handoff-v001/
  conversion-input.pptx        # 一图一页+原始备注，仅作为转换输入
  handoff.json                 # scope、包/主题哈希、逐页映射
  style-profile.json
  images/page_001.png          # 显式选版的原图，保持字节
  content/page_001.json        # 完整 slide、证据、schedule、原稿包哈希
```

`page_id` 是本次转换的序号，`slide_id` 是全稿稳定 ID。例如 `--range 1,3`：page_001→S001、page_002→S003。保留原始 order/总页数；交付必须标明部分稿。

每次转换前、续做前及最终交付前运行 verify-handoff。它检查当前原稿/主题、选版、顺序、内容文件与图片字节。新标题、重排、另选图片使旧 handoff 失效。它不更新已有 editppt run；建立新版本目录重做受影响转换。无变化可继续原 run。

若用户只给大纲，先完成逐页内容草案，标 draft 或 content_complete=false。给出需要确认的具体差异；禁止把一句主题自动当成已批准整页事实。

备注载体采用第一张已选原图的实际宽高比；同一批图片需具有相同宽高比。主题允许的轻微比例误差不会被拉伸修正。比例不一致时先重生成不兼容页，或按用户明确的范围分别转换。
