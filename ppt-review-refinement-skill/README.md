# PPT 评审与精修 Skill

这是一个面向现有 PPTX 的受控优化 Skill。它把“PPT 美化”拆成七个阶段：

```text
定位 → 叙事评审 → 视觉评审 → 变更授权 → 样板确认 → 全稿优化 → 质量校验
```

## 目录说明

- `SKILL.md`：主技能说明和执行约束。
- `workflows/`：逐阶段操作手册。
- `prompts/`：各子 Agent 的提示词契约。
- `rules/`：叙事、视觉、页面原型、风险和配图规则。
- `schemas/`：关键 JSON 输出的 Schema。
- `templates/`：上下文、授权、设计 Token 和评审报告模板。
- `scripts/`：可运行的结构审计、渲染、规范化和验证脚本。
- `examples/`：示例配置与运行方法。
- `tests/`：本地冒烟测试。

## 安装

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

可选系统工具：

- LibreOffice / `soffice`：把 PPTX 转成 PDF。
- Poppler / `pdftocairo` 或 `pdftoppm`：把 PDF 渲染成 PNG。

## 最快开始

```bash
python scripts/create_review_bundle.py your_deck.pptx --out work/review_bundle
```

完成评审和授权后，可执行低风险规范化：

```bash
python scripts/normalize_pptx.py your_deck.pptx work/normalized.pptx \
  --tokens examples/style_tokens.industrial-consulting.json \
  --manifest examples/change_manifest.l1.json \
  --log work/normalization_log.json
```

验证优化结果：

```bash
python scripts/validate_pptx.py \
  --original your_deck.pptx \
  --candidate work/normalized.pptx \
  --manifest examples/change_manifest.l1.json \
  --out work/validation
```

## 设计边界

脚本提供的是可执行 MVP：

- `analyze_pptx.py`：量化结构、字体、字号、颜色、图片清晰度、越界和重叠风险。
- `analyze_pptx.py`：对有明确字号和尺寸的文本框增加保守的溢出风险估算；最终仍需结合渲染图确认。
- `render_pptx.py`：生成逐页 PNG。
- `normalize_pptx.py`：执行明确授权的字体、颜色映射和标题位置规范化。
- `validate_pptx.py`：校验页数、正文、数字、受保护术语和候选文件结构风险。
- `validate_pptx.py`：实际项目的 `change_manifest.json` 和 `style_tokens.json` 必须通过对应 Schema；未登记的链接、动画、SmartArt、嵌入对象或图片替换风险不能进入通过状态。

复杂的 L2/L3 单页重构仍需要具备 PowerPoint/OOXML/PptxGenJS/Office API 编辑能力的执行器；该 Skill 提供完整的决策、授权、计划和验收框架。

## 安全建议

始终保留源文件；在副本上编辑。涉及客户机密时，不要把源文件上传到未经批准的外部图片或模型服务。
