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

## 5. L2/L3 精修（需要样板批准）

先按 `templates/pilot_confirmation.template.json` 形成 `work/pilot_confirmation.json`，再执行：

```bash
python scripts/execute_refinement_plan.py \
  --input deck.pptx --output work/candidate.pptx \
  --plan work/review/refinement_plan.json \
  --tokens work/review/style_tokens.json \
  --manifest work/review/change_manifest.json \
  --pilot-confirmation work/pilot_confirmation.json \
  --log work/change_log.json --before-after-dir work/before_after
```

叙事 Agent 和视觉 Agent 的独立结果可用 `scripts/compose_review_report.py` 合并；编排器只负责结构契约，不代替外部判断。

## 6. 验证

```bash
python scripts/validate_pptx.py \
  --original deck.pptx \
  --candidate work/normalized.pptx \
  --manifest work/review/change_manifest.json \
  --visual-signoff work/visual_signoff.json \
  --out work/validation
```

先逐页打开 `work/validation/rendered/slide-*.png`，再由人工填写 `work/visual_signoff.json` 并重新运行验证。没有人工签字时，最终验证会失败。
