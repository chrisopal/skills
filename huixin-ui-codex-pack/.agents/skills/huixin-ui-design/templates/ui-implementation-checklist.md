# Huixin UI Implementation Checklist

Use this before finishing a UI implementation task.

## Context

- [ ] I classified the surface: Frontstage / Admin / Hybrid.
- [ ] I inspected the existing framework, component library, and styling system.
- [ ] I reused existing project patterns rather than adding a parallel UI system.

## Brand and Tokens

- [ ] Colors use Huixin tokens or mapped project theme tokens.
- [ ] No random raw hex values are scattered across page components.
- [ ] Token files do not override existing global `body` styles unless the project explicitly allows it.
- [ ] Primary actions use brand blue/teal consistently.
- [ ] Success, warning, and error colors are semantic.
- [ ] Logo assets are not distorted, recolored, shadowed, or placed on messy backgrounds.

## Typography

- [ ] Font family uses approved/open fonts or system fallback.
- [ ] Type scale follows 36/24/20/18/16/14/12px hierarchy.
- [ ] Line heights are readable and align with the spec.
- [ ] Weights are limited to 320/400/600 where possible.
- [ ] Numeric dashboard values use numeric font stack where appropriate.

## Layout

- [ ] Admin pages use 24px margin, 16px gutters, 24-column logic, 232px sidebar if applicable.
- [ ] Frontstage pages use centered 1128px content width and 12-column logic.
- [ ] Layout works at 1366px, 1440px, and 1920px where applicable.
- [ ] No page-level horizontal overflow.
- [ ] Tables overflow inside their own container.

## Spacing

- [ ] Spacing uses 4px/8px scale: 4/8/12/16/20/24/28/32/40.
- [ ] Card, form, module, and inline gaps are consistent.
- [ ] Dense admin pages are compact but readable.

## Components

- [ ] Buttons: 32px height, 14px text, 3px radius, 5px 16px padding.
- [ ] Inputs/selectors/date/time/search: 32px height, 14px text, 3px radius.
- [ ] Cards: 6px radius, 16px 24px padding, 16px title.
- [ ] Tags: 24px height target, 12px text, 2px 8px padding.
- [ ] Icons: 16px common UI size; custom icons exportable as SVG.
- [ ] Empty states use flat illustration style, 20px title, 14px description.
- [ ] Modal/alert/drawer sizing and padding follows spec.

## Accessibility

- [ ] Interactive elements have visible focus states.
- [ ] Inputs have labels or accessible names.
- [ ] Color is not the only indicator for errors/status.
- [ ] Keyboard operation is preserved.
- [ ] Contrast is acceptable for normal text and controls.

## Validation

- [ ] Ran lint.
- [ ] Ran typecheck.
- [ ] Ran tests if available.
- [ ] Ran build if feasible.
- [ ] Captured or reviewed UI visually if tooling is available.

## Final Note

Report changed files, applied design rules, validation commands, and any unresolved assumptions.
