# 示例运行手册

## 1. 生成评审资料包

```bash
python scripts/create_review_bundle.py deck.pptx --out work/review
```

先阅读：

- `work/review/montage.png`
- `work/review/structural_audit.md`
- `work/review/analysis.json`

然后用 `prompts/profile_analyzer.md`、`prompts/narrative_reviewer.md` 和 `prompts/visual_auditor.md` 生成正式评审结果。

## 2. 确认变更范围

把 `work/review/change_manifest.json` 中的 `approval_status` 改为 `approved`，并填写确认人、时间、受保护术语和风险。

## 3. 建立设计 Token

以 `examples/style_tokens.industrial-consulting.json` 为参考，结合品牌色、字体和样板页填写 `style_tokens.json`。

## 4. 执行 L1 规范化

```bash
python scripts/normalize_pptx.py deck.pptx work/normalized.pptx \
  --tokens work/review/style_tokens.json \
  --manifest work/review/change_manifest.json \
  --apply-role-sizes \
  --standardize-title-position \
  --log work/normalization_log.json
```

## 5. 验证

```bash
python scripts/validate_pptx.py \
  --original deck.pptx \
  --candidate work/normalized.pptx \
  --manifest work/review/change_manifest.json \
  --out work/validation
```

即使脚本返回通过，仍需逐页打开 `work/validation/rendered/slide-*.png` 进行视觉确认。
