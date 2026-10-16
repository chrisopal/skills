# 固定表单：从原件到 Markdown、Word

PDF 的逐行文字只是追溯底稿，不能作为表格模板。06 回看原页，保留列、行、合并、多行表头、脚注、签署区和方向；原始 DOCX/表格可用时优先保留原模板。扫描页需宿主 OCR 后目视复核，不从 OCR 阅读顺序推断表格已完整。

06 的 `template_path` 指向实际未填 Markdown 模板。简单表用管道表格；合并或多行表头使用内嵌 HTML `table` / `rowspan` / `colspan`。12 的可选 `section_id`、`template_path`、`filled_template_path`、`table_spec_path` 绑定目录、原模板、填报 Markdown 和结构 JSON。路径相对项目根；实际存在且在导出 spec.inputs 中记录当前 SHA256。匹配不到章节时报错，不能默认归到最后一章。

结构 JSON 使用 `{"paragraphs":[],"tables":[]}`。不要把整份 PDF 模板原文作为企业字段值重复导出；原文和来源保留在06，填值、来源及缺失状态留在12。表格规格示例：

```json
{
  "headers": ["项目", "姓名", "证书号"],
  "rows": [["项目组", "测试人员甲（模拟）", ""], ["", "测试人员乙（模拟）", ""]],
  "merges": [{"row": 1, "column": 0, "row_span": 2, "col_span": 1}],
  "missing_cells": [{"row": 1, "column": 2, "label": "甲的证书号"}],
  "widths_cm": [4, 5, 6],
  "paragraphs_before": ["项目团队人员表"],
  "paragraphs_after": ["原件脚注及签署区保留在表后。"]
}
```

坐标从0开始，包含表头。`header_rows` 默认为1；多行表头的 headers 为二维数组；无表头时 header_rows=0、headers=[]。合并覆盖格保持空字符串，内容只在锚点；重叠、越界或覆盖非空值拒绝生成。`page_break_before:true` 可用于原文要求逐人独立页的第一张表。section 的 `orientation` 可设 portrait / landscape；原件横向宽表按当前页面正文宽度校验，不通过缩小强制字号挤入竖页。

缺失字段仍是 `value:null / state:missing`。表格通过 missing_cells 输出 `【待补充：字段名】`，Markdown 的 mark 和 Word 的黄色文字高亮同时保留。备用空行与明确不适用项不误判为缺失；已有模拟值明确标注，不能当作真实有效材料。签章不自动生成，留原签署区和待办提示。

`scripts/fixed_form_tables.py` 的 normalize_table_spec、effective_grid、table_to_markdown 与 build_docx / export_checks 共用同一结构。导出验收检查实际 Word 表格、合并跨度、缺项文字和黄色高亮，PDF 保留缺项文字；颜色和页面阅读效果仍需实际渲染比照原页。只有全文都可检索不算格式合格。必填内容或真实签署缺失时，正式交付保持阻塞，模拟功能测试结论单列。
