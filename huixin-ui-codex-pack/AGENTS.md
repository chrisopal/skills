# AGENTS.md — Huixin UI Frontend Guidance for Codex

## Purpose

This repository must follow **Huixin UI Design 2.0** for all user-facing frontend work. Treat this file as the persistent project-level working agreement for Codex.

When a task involves page layout, component implementation, dashboard UI, forms, tables, login pages, portals, charts, icons, theme tokens, responsive behavior, or visual refactoring, use the repository skill:

```text
$huixin-ui-design
```

The skill is located at:

```text
.agents/skills/huixin-ui-design/SKILL.md
```

## Working Agreement

1. **Do not improvise a new visual language.** Preserve the company brand style: calm technology, intelligent manufacturing, industrial internet, deep-blue primary tone, clean information hierarchy, and restrained enterprise UI.
2. **Use design tokens first.** Do not hardcode random colors, font sizes, spacing, border radii, or component heights if a Huixin token exists.
3. **Match the product surface.** Use the public/frontstage grid for marketing portals and solution pages. Use the admin/backstage grid for dashboards, management systems, lists, forms, details, login pages, and internal platforms.
4. **Prefer existing components.** If the repository already uses Ant Design, Arco, Element Plus, shadcn/ui, Tailwind, or a local component library, extend its theme using Huixin tokens instead of creating a parallel component system.
5. **Keep changes atomic.** Separate token/theme changes, layout changes, component changes, and business logic changes when possible.
6. **Protect brand assets.** Never redraw, stretch, recolor, distort, add shadows to, or place the logo on a messy background. Use official logo assets if present; otherwise leave a clear placeholder and note the missing asset.
7. **Accessibility is mandatory.** Preserve semantic HTML, focus states, keyboard support, form labels, sufficient contrast, and error/help text.
8. **Validate before finishing.** Run the relevant project checks after UI changes: lint, typecheck, unit tests, build, and available visual or screenshot checks.

## Huixin Brand Summary

### Visual Keywords

- Intelligent / 智能
- Make & Manufacturing / 制造与生产
- Internet / 互联
- Future / 无限可能
- Industrial technology, reliable enterprise systems, precise data interaction

### Core Colors

Use these as source-of-truth tokens unless a closer existing token already exists in the repository.

| Token | Hex | Use |
|---|---:|---|
| `--hx-color-primary` | `#00405C` | Main brand color, side navigation, primary blocks, selected main state |
| `--hx-color-primary-action` | `#0097BA` | Clickable/action state, active tabs, links, selected controls |
| `--hx-color-selected-bg` | `#CCF5FF` | Selected background, active row/background tint |
| `--hx-color-accent-green` | `#A5D867` | Brand auxiliary accent, positive highlight, brand secondary mark |
| `--hx-color-success` | `#2BA471` | Success state |
| `--hx-color-warning` | `#E37318` | Warning state |
| `--hx-color-error` | `#D54941` | Error/destructive state |
| `--hx-color-border-a` | `#DBDFE7` | Standard border |
| `--hx-color-border-b` | `#E3E7EE` | Light divider |
| `--hx-color-bg-a` | `#F0F2F5` | Page background / layout area |
| `--hx-color-bg-b` | `#F5F7FA` | Light section/card background |
| `--hx-color-text-title` | `#333333` | Titles and high-emphasis text |
| `--hx-color-text-primary` | `#666666` | Main body text |
| `--hx-color-text-secondary` | `#999999` | Secondary text, descriptions, placeholders |

### Typography

Use authorized/open fonts first. Use system fonts only as fallback.

```css
font-family: "HarmonyOS Sans", "Source Han Sans SC", "思源黑体", "Microsoft YaHei", Arial, sans-serif;
```

Approved type families:

- HarmonyOS Sans
- 思源黑体 / Source Han Sans
- D-DIN-PRO for numeric or dashboard data emphasis
- 钉钉进步体 / 斗鱼追光体 only for controlled art-display usage, not dense product UI

Avoid unlicensed commercial font embedding. System calls to platform fonts are acceptable as fallback.

### Type Scale

| Level | Size | Line height | Weight | Use |
|---|---:|---:|---:|---|
| H1 | 36px | 54px | 600 | Home hero/banner title |
| H2 | 24px | 36px | 600 | Page title, major focal area |
| H3 | 20px | 30px | 600 | Module title |
| H4 | 18px | 28px | 600 | Section title/news title |
| H5 | 16px | 24px | 400/600 | Main navigation, card title |
| Body | 14px | 22px | 400 | Default UI text, forms, tables |
| Assist | 12px | 18px | 400 | Tips, remarks, secondary metadata |

Allowed weights: `320`, `400`, `600`.

### Spacing

Use a 4px / 8px spacing system:

```text
4, 8, 12, 16, 20, 24, 28, 32, 40
```

Default dense enterprise UI rhythm:

- Inline icon gap: 8px
- Form field vertical rhythm: 16px or 24px
- Card inner padding: 16px 24px
- Page content margin: 24px
- Module gap: 16px, 24px, or 32px depending on density

### Layout Grids

#### Frontstage / Portal Pages

Use for official website, solution pages, public landing pages, product introduction pages.

- Design canvas: 1920px
- Effective content width: 1128px
- Grid: 12 columns
- Column width: 72px
- Gutter: 24px
- Grid base: 8px
- Below 768px: mobile page
- 768px–1128px: columns compress dynamically, gutter remains stable
- Above 1128px: keep content centered; side whitespace expands

#### Middle/Backstage / Admin Pages

Use for management systems, dashboards, forms, list pages, details pages, login pages, monitoring pages.

- Design canvas: 1440px
- Effective content width: 1208px
- Grid: 24 columns
- Gutter: 16px
- Page margin: 24px
- Sidebar: 232px fixed
- Content region: auto/flexible
- Design for 1920px, 1440px, and 1366px widths
- Sidebar and module gaps stay fixed; content area adapts

## Component Rules

### Buttons

- Height: 32px unless local system has a stricter size ramp.
- Font: 14px.
- Border radius: 3px.
- Text-only button padding: `5px 16px`.
- Icon button with text: icon 16px, gap 8px, padding `5px 16px`.
- Primary button uses `--hx-color-primary` or `--hx-color-primary-action` according to the existing design language.

### Inputs, Selects, Search, Date/Time Pickers

- Height: 32px.
- Font: 14px.
- Border radius: 3px.
- Input padding: `5px 8px`.
- Search padding: `4px 4px 4px 8px`.
- Icons: 16px or 24px depending on component type.
- Placeholder uses secondary/low-emphasis text.

### Forms

- Label font: 14px.
- Control font: 14px.
- Default label alignment in dense admin forms: right aligned.
- Common label-control gap: 16px.
- Common row gap: 24px.
- Error/help text must be close to the field and use status colors.

### Cards

- Border radius: 6px.
- Padding: `16px 24px`.
- Title: 16px.
- Body text: 14px.
- Header/action row height target: 40px.
- Use borders and subtle backgrounds rather than heavy decoration.

### Tags and Badges

- Tag padding: `2px 8px`.
- Tag font: 12px.
- Tag height target: 24px.
- Tag icon: 14px.
- Badge height target: 20px.

### Dropdowns and Menus

- Dropdown container padding: `6px`.
- Dropdown radius: 6px.
- Item padding: `3px 8px`.
- Item radius: 3px.
- Font: 14px.

### Tables

- Use compact, readable enterprise density.
- Keep headers clear, row hover visible, and action columns right-aligned when practical.
- Use pagination format compatible with the existing project.
- Selected rows should use `--hx-color-selected-bg` or an equivalent brand tint.

### Icons

- Standard sizes: 24px, 48px, 72px.
- Common UI icon: 16px.
- Stroke/fill style: solid stroke/fill with clear hierarchy.
- Stroke width: 2px.
- Rounded caps and rounded joins.
- Use even sizes, even radii, and integer anchor positions.
- Export custom icons as SVG.

### Empty, Loading, Modal, Drawer, Notification

- Empty state illustration: flat style.
- Empty title: 20px; description: 14px.
- Modal/alert padding: `16px 24px`.
- Alert icon: 20px; text: 14px.
- Drawer action buttons should follow the standard button rules.

## Implementation Standards

### CSS Variables

Add or reuse Huixin CSS variables. Prefer central token files such as:

- `src/styles/tokens.css`
- `src/styles/theme.css`
- `src/theme/index.ts`
- `tailwind.config.*`
- Ant Design / Arco / Element theme config files

Reference package files:

- `.agents/skills/huixin-ui-design/tokens/huixin-theme.css`
- `.agents/skills/huixin-ui-design/tokens/huixin.tokens.json`

### React / Vue / Frontend Code

- Keep components small and composable.
- Avoid large inline style objects except when the project convention requires them.
- Prefer semantic component names aligned to business modules: `QualityDashboard`, `ProjectListTable`, `DeviceStatusCard`, etc.
- Use data-driven rendering for menus, stats, tables, cards, and timeline items.
- Avoid mixing business calculations directly into JSX/templates; extract helpers.

### Responsive Behavior

- Ensure admin layouts remain usable at 1366px width.
- Avoid fixed widths that overflow content areas.
- Use `minmax(0, 1fr)` for flexible grid columns in CSS Grid.
- Tables with many columns should support horizontal scroll within the table container, not at the page level.

### Charts and Dashboard Data

- Use D-DIN-PRO or the numeric fallback stack for key metric values.
- Primary data series should use brand blue/teal; success/warning/error should use status colors.
- Keep axes, legends, and labels legible at 12px–14px.
- Avoid decorative gradients unless already part of the product style.

## Validation Checklist Before Final Response

For UI-related changes, Codex must report:

- What files changed.
- Which Huixin tokens or component rules were applied.
- Which checks were run and their result.
- Any remaining visual risk, missing asset, or assumption.

Run relevant commands when available:

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

Use the package manager already used by the repository: `pnpm`, `yarn`, `npm`, or `bun`.
