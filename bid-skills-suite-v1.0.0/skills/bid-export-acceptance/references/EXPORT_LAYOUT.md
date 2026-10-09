# 导出封面、目录与页眉页脚配置

`scripts/build_docx.py` 可以在原有 `document-spec` 的正文样式基础上接收一份可复用的导出配置。配置只控制工作稿的封面、目录字段、页眉和页脚，不改变需求、评分、证据或正文事实。

## 使用方式

外部配置适合保存在用户项目的 `profiles/export-settings.json`，并在项目评审前固定版本：

```bash
python scripts/build_docx.py \
  --spec /project/artifacts/14-document-spec.json \
  --export-settings /project/profiles/export-settings.json \
  --asset-root /project \
  --out /project/deliverables/draft-v2.docx
```

也可以将同样的对象嵌入 `document-spec.json` 的 `export_settings` 字段。外部文件与内嵌字段不能同时提供。旧调用方式仍然有效，未提供配置时使用保守的工作稿封面、内部页眉、`PAGE` 页脚字段，目录保持关闭。

配置改变会改变实际导出字节和页码，必须更新项目 `profiles` 下的配置版本或哈希，并使依赖该版本的审核、导出快照失效。应按当前配置重新评审并重新生成候选文件；配置保存不表示已采纳、已签章或取得递交授权。

## 配置字段

顶层只允许 `style`、`cover`、`toc`、`header` 和 `footer`。

`cover` 支持：

- `enabled`：是否写入封面，默认 `true`。
- `title`、`subtitle`：封面标题和副标题；缺省时分别使用 spec 的 `title`、`subtitle`。
- `metadata_rows`：按数组顺序写入的 `{ "label": "...", "value": "..." }` 行；label 不能重复。
- `alignment`：`left`、`center` 或 `right`。
- `own_page`：封面后是否分页，默认 `false`。
- `image`：可选的 `{ "path": "assets/cover.png", "width_cm": 12, "height_cm": 5 }`；路径相对 `--asset-root`，只能使用 PNG/JPEG，宽度不能超过当前正文版心，高度不能超过可用页面高度。
- `typography`：可选的封面字号和中文字体字段，支持 `title_east_asia_font`、`subtitle_east_asia_font`、`metadata_east_asia_font`、`title_size_pt`、`subtitle_size_pt` 和 `metadata_size_pt`。

`toc` 支持 `enabled`、`title`、`levels`（1—9）和 `typography`。`typography` 支持 `east_asia_font`、`latin_font`、`size_pt`、`line_spacing`、`space_before_pt`、`space_after_pt` 和 `alignment`。开启后脚本写入合法的复杂 Word `TOC` 字段（含 `\o`、`\h`、`\z`、`\u` 开关），为每个正文标题写入唯一书签，并预置 `TOC 1` 至 `TOC 9` 段落样式，按层级增加缩进。脚本只写入字段和待更新提示，不从 XML 伪造已刷新的目录条目或页码；应在实际 Word/LibreOffice 交付引擎中更新、保存，再读回和逐页检查。

`header` 和 `footer` 支持 `text`、`alignment`、`page_field`、`page_prefix`、`page_suffix`。footer 默认写入 `PAGE` 字段，默认显示为“第 PAGE 页”；将 `page_field` 设为 `false` 可关闭。header/footer 的默认内部工作稿提示仍然存在，除非配置明确覆盖。

## 基础视觉基线

基础生成器会将表格作为可编辑的 Word 表格保留，并显式写入浅灰色外边框与内网格、浅蓝表头、交替浅色数据行、统一的单元格内边距和紧凑的单元格段落行距。表格正文与表头都使用当前 `style` 的正文字体和 `table_size_pt`，不会依赖宿主主题字体；客户指定的字体和字号仍优先由 `style` 覆盖。

正文插图段落默认居中，图注使用当前正文字体和 `caption_size_pt`，与图片保持在同一排版组内，并保留图注前后的明确间距。页眉、页脚和页码字段也显式写入当前正文字体。上述规则只改善基础候选工作稿的可读性，不替代客户模板、复杂固定表或最终 Word/PDF 逐页检查。

正文的 `style` 字段支持继续放在 document-spec，也支持放在导出配置顶层。两者使用同一套严格校验；导出配置的 `style` 按字段覆盖 document-spec 的 `style`，未提供的字段沿用 document-spec 或基础默认值。支持正文/标题字体、字号、行距、首行缩进、段前后距、对齐、表格/图注字号和四边页边距。表格与图注行距默认继承 `body_line_spacing`，也可分别用 `table_line_spacing` 和 `caption_line_spacing` 覆盖。`table_border_color`、`table_header_fill`、`table_alternate_fill` 接受六位十六进制颜色或 `null`（关闭对应显式样式）；`table_cell_padding` 接受 `top/start/bottom/end` 四个 twips 数值或 `null`（不写入显式内边距）。导出配置不会绕过已有 style 校验，也不会接受未知字段、重复 JSON 键、重复 metadata label、越界路径或超出版心的图片尺寸。

## 规则优先级与验收边界

插图按实际宽高比检查缩放后高度，并给图注及与图相连的标题/末段预留空间；接近整页的图需要减小或单独编排。文字换行高度是保守估算，最终分页仍以实际Word/PDF渲染为准。

招标文件、有效补遗和 06 格式提取中的强制封面、目录、字体、页眉页脚、分页及固定表要求优先于这份偏好配置。配置只补齐原文未规定的部分；发生冲突时记录覆盖理由，不能用通用样例替代客户强制格式。macOS 预览可使用示例中的 `Songti SC` 和 `Heiti SC`，其他宿主必须确认实际可用字体，不能把字体名称写入 DOCX 当作字体嵌入或正式符合证明。

脚本返回的状态始终是 `draft_only`，`visual_qa` 始终是 `NOT_RUN`。实际 DOCX 结构回读不能替代 Word/PDF 渲染、目录刷新、页码核对、固定表保真、签署检查或业务/发布授权。这里没有应用 UI，也不会生成真实项目投标文件、上传或递交文件。
