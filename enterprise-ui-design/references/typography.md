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

## Complete role and resource contract (v1.3)

`tokens.json` → `semantics.font.roles` is the machine role inventory. Each body, label, nav, table-heading, record, meta, title, section, metric, unit, reading and code role declares family/size/weight/line/tracking/numeric behavior. Generated `type-*` CSS aliases and effective component recipes consume the same map; do not duplicate literal sizes in another table. Page title 22–24, section14–16, body14 and metric28–36 are starting ranges, not universal exact values. Record values remain readable body size; units stay visible while quieter than the number. Code/identifiers alone use the mono fallback.

Default uses the existing compatible OS/system fallback. The legacy `font-sans` still lists Inter first for compatibility; this does **not** bundle, download or prove Inter is installed. Projects may explicitly supply their own family through the existing theme adapter. An optional self-hosted font needs known license/version, full weight mapping, WOFF2 path/bytes/cache/preload strategy, Chinese dynamic-content coverage or reliable fallback, mixed-script specimen and before/after loading layout evidence. No mandatory font picker or CDN. Never package PingFang/Segoe/Microsoft YaHei binaries from an OS.

All Chinese/body tracking defaults to zero. Latin optical tracking needs a scoped role/language exception, and should not globally propagate. Real precision, negative signs, percent/decimal alignment and zero/empty/unknown are business formatting contracts: `tabular-nums` does not license rounding or converting missing to0. Verify actual font support and alignment, not only the property.

| Resource | Source/version/license | Bytes/path/weights | Evidence and gaps |
|---|---|---|---|
| Existing UI sans fallback | Host OS fonts; OS version/platform-specific license | No font binary shipped; legacy `font-sans`; browser synthesizes/falls back only as observed | Record platform face for Chinese/Latin/numeric specimens. Cross-platform identity is not promised. |
| Existing mono fallback | Host OS; no new download | No font binary shipped; `font-mono`; code/IDs only | Record rendered face if exact identifier alignment matters. |
| Optional project self-hosted font | Must be provided/selected with traceable open license or project rights | Record exact version/hash, file bytes, declared weights, source and loading path | Not added by this update; missing resource is not filled by naming a family. |
| Reference icons/charts | Native text glyphs and original Canvas code, simulated data | Local source, no external asset/font dependency | Glyph appearance depends on fallback; chart has an equal-value table. No brand/logo asset copied from screenshots. |

The delivery validation report records runtime fonts and missing evidence separately. UI changes never propagate into signed reports, print/PDF templates or report body fonts without explicit scope.
