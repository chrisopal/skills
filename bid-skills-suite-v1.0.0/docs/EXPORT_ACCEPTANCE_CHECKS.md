# 导出成稿内容完整性检查

`scripts/export_checks.py` 是 `build_docx.py` 的内容完整性检查器。它读取同一份 `document-spec`，回读实际 DOCX 和 PDF 字节，检查标题、正文段落、表格单元格、图注、图片关系、关键事实和文件身份。它不把生成成功、语义评审、签署授权或逐页视觉检查混为一项通过条件。

## 运行与收据

项目根目录必须包含 `work/project.json`，并且其中有当前项目的 `project_id`。每次导出使用新的收据文件名：

```bash
python scripts/export_checks.py \
  --spec /project/artifacts/14-document-spec.json \
  --docx /project/deliverables/candidate.docx \
  --pdf /project/deliverables/candidate.pdf \
  --project-root /project \
  --receipt /project/deliverables/candidate.export-receipt.json
```

命令输出和可选收据都是 JSON。收据至少绑定：`project_id`、输入 spec 的 SHA-256、DOCX/PDF 的实际 SHA-256 与字节数、PDF 页数、检查器版本及 `python-docx`/`PyMuPDF` 版本。`visual_qa` 固定为 `NOT_RUN`；Word/PDF 渲染后的逐页人工记录应作为独立证据保存，不能修改这条机器收据来冒充视觉通过。

Python 调用入口为：

```python
from scripts.export_checks import inspect, verify_receipt

receipt = inspect(spec_path, docx_path, pdf_path, project_root)
verify_receipt(receipt, spec_path, docx_path, pdf_path, project_root)
```

`inspect` 返回 `passed`、`findings`、`counts` 和按类别拆分的 `coverage.*.expected/present/absent`。`verify_receipt` 会重新读取 spec、项目身份和两个实际文件；任何 spec、文件字节、大小、页数或期望内容漂移都会抛出 `ValueError`，不会用旧收据继续通过。

## 检查边界

- DOCX 标题按 `Heading 1`—`Heading 3` 的层级和出现顺序核对；正文段落按规范化后的完整段落文本核对；表格按实际表格顺序逐行逐单元格核对。封面元数据表也属于规范的一部分。
- PDF 使用 PyMuPDF 读取实际文字层，并按完整规范化文本检查出现顺序。空文字层、替换字符、不可解释控制字符和格式损坏都会阻断自动通过；规范化只处理 Unicode NFC 和空白，不折叠康熙部首等兼容字形，不静默替换异常字形。
- 规范声明的每一张 PNG/JPEG 都必须在 DOCX 的 inline shape、图片关系和 `word/media` 部件中同时出现（重复使用同图允许共享媒体部件）；PDF 使用实际页面图片引用计数核对。缺图、额外图或关系不一致都会失败。
- `expected_facts` 是可选的关键事实清单，可以写文本，也可以写 `{ "id": "deadline", "value": "30天", "required": true }`。必需事实必须在 DOCX 和 PDF 中出现；`required: false` 只记录期望值，不作为失败条件。
- 开启 `export_settings.toc.enabled` 时，目录占位提示、缺失的 TOC 字段、未出现两次的章节标题都会失败。`build_docx.py` 产生的“目录字段将在支持的Word交付引擎中更新”明确表示尚未刷新，不能自动通过。

通过机器检查仍只代表实际文件的客观内容和身份与当前 spec 一致。正式业务语义、证据真实性、客户模板保真、目录页码、字体可用性、签字盖章和发布授权仍需各自的评审或人工门禁。

## 当前版本、配图与内部信息

当项目存在08目录及11正文时，spec必须绑定两份当前哈希，章节顺序须与目录显示树一致，不能用不完整spec让漏章通过。显式数字编号的同级章节按数字自然顺序显示；含自定义或未编号节点的同级组仍保留原顺序。存在12商务产物时还必须绑定其当前哈希，并覆盖所有非空字段值。

DOCX每个插图位置除计数外还核对解码后像素身份与顺序；同数量的错误图片不能通过。PDF按实际图片出现次数检查。声明的页眉、页脚、页码格式须在DOCX及PDF逐页存在。PDF长段落被分页时，仅移除实际声明的页眉页脚后再核对，不能随意删除正文来凑通过。

导出扫描拒绝 `confirmation_ref`、`body_markdown` 等内部字段及项目工作目录路径，即使这些内容也写进了spec。商务字段只存对外可读的内容，签署授权引用保留在产物的独立审计字段中；不通过跳过非空商务字段掩盖泄漏。

LibreOffice刷新保存后相邻表格需要独立段落分隔，避免重新保存时合并。机器内容检查不认证客户固定表单的几何保真；长固定文案改成正文段落时，必须标记“固定表单版式未验收”。Microsoft Word原生打开与二次刷新也须另行执行和记录。

08、11、12分别存在时各自检查当前项目、哈希和内容；不要求三者同时存在才启动核对。畸形当前产物产生失败收据。页眉页脚通过生成器共享默认解析器处理，包括省略`page_field`时页脚默认必须有页码；不只检查显式字段。
