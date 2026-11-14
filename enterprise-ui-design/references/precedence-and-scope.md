# Rule precedence and scoped applicability

Use this page when two Enterprise UI Design references, a project contract, or a
Profile recipe appear to disagree. It is a decision rule, not another visual
token source.

## Precedence

Resolve a decision in this order:

1. The host product's business, permission, data, accessibility and component
   contracts. Product behavior and truthful state always win over appearance.
2. The named project's current `DESIGN.md`, UI Blueprint and explicitly named
   project exception. These apply only to that product and declared surface.
3. The explicitly selected Profile, theme, brand and density layers. For
   Huixin, framework/material geometry is fixed in `huixin-framework.md` and
   `huixin-components.md`; modes and brands provide color/alpha only through
   the generated configuration.
4. The generic style, spatial, component, form and detail references.
5. Runnable fixtures, screenshots and examples. They demonstrate a pattern or
   evidence path; they do not create a product rule or a required dimension.

When an applicable higher layer changes a generic recommendation, record the
scope, reason, affected consumers and evidence in the Blueprint. Do not resolve
an ambiguity by copying both recipes or by changing a shared token globally.

## Token and source authority

`assets/tokens.json` is the sole authored token source for this Skill. Generated
CSS, configuration, aliases and runtime adapters are derived outputs. A host
project may map these semantic roles to its own token system, but must not copy a
second palette or maintain competing dimensions. Literal colors and dimensions
in examples are not token authority.

## Common conflict boundaries

| Topic | Generic rule | Scoped override | How to report it |
|---|---|---|---|
| Row actions | `layout-action-gap` starts at 8px; keep one recognizable action group | Explicit Huixin uses 12px and 32px compact row actions. A named product exception may retain its own value | Name the product/Profile, measured gap and consumer scope |
| Detail and traceability | Readable identity and current task first; optional provenance follows business content and history | Move provenance or checksums next to an action only when the real task requires it; preserve version binding and access rules | Record the chosen detail variant and why the order differs |
| Forms | Field/group spacing follows host tokens; 8px label gap is a starting point, not a universal size | Huixin's declared field group and label gaps apply only inside the selected Huixin Profile | Record the mapped tokens and actual rendered values |
| Responsive layout | Reflow from actual container width; viewport breakpoints primarily govern global navigation | A project or fixture may declare local breakpoints when its container and interaction contract require them | Record container width, scroll owner and breakpoint/condition |
| Material and palette | Generic Profiles stay flat and semantic | Huixin's declared glass/gradient recipes are opt-in; project brand assets remain local | State Profile/brand/theme and verify actual composited contrast |

Project exceptions never weaken authorization, data truth, keyboard access,
focus management or error recovery. If no higher-scope contract is named, use
the generic rule and the existing host component behavior.
