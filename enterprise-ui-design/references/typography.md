# Typography Roles and Rendering Checks

Use the role tokens in `assets/tokens.json` as starting points. They organize hierarchy; they do not justify applying one weight or size to every element.

| Role | Starting point | Use |
|---|---|---|
| body/data | 14px / 400 / `line-data` | body copy, tables and comparable values |
| nav/label | 13–14px / 400–500 | navigation and field labels; selected state may use 600 |
| section | 14–16px / 600 | group headings and local summaries |
| page title | 22–24px / 600–700 | one page-level heading |
| metric | 28–36px / 700 | a real decision-support value with a unit |
| meta | 12–13px | provenance and secondary context, never the main action |
| reading | 16px / 1.7 | long-form explanation or document reading only |

Keep `weight-emphasis` at its existing value for compatibility. Use the role tokens when a new component needs a more specific contract; reserve 800 for a verified font and an actual hierarchy need. Compact density changes insets, control height and table padding. It does not shrink body text or turn mobile touch targets into compact controls.

For mixed Chinese, Latin, numbers and units, keep the host font stack and a reliable fallback. Use `font-variant-data: tabular-nums` for comparable numeric columns and keep units in a separate span when their emphasis differs. Do not add global letter spacing, negative tracking, `scaleX`, or a monospaced font to ordinary Chinese prose.

## Font evidence

Record the requested family, declared `@font-face` weights/styles, loaded resource and fallback path. Check `document.fonts.ready`, `document.fonts.check()` and computed styles, then use browser Rendered Fonts (or an equivalent runtime API) for representative Chinese, English, numeric and unit glyphs such as `μm`, `℃`, `±`, `≤`, `≥` and superscripts. A family string or `fonts.check()` result alone does not prove the rendered face.

Compare layout before and after font loading at the same viewport and data state. Keep UI fonts separate from report/print fonts. If no licensed, complete local font resource is available, keep the existing system fallback and report the missing evidence rather than adding a CDN-only dependency or copying proprietary fonts.
