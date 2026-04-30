---
name: huixin-ui-design
description: Use when designing, implementing, refactoring, or reviewing frontend UI against Huixin UI Design 2.0. Trigger for dashboards, admin systems, portals, forms, tables, charts, cards, login pages, responsive layouts, design tokens, theme setup, component styling, and UI consistency reviews. Do not use for backend-only or data-only tasks.
---

# Huixin UI Design Skill

## Goal

Produce frontend UI that follows Huixin UI Design 2.0: deep-blue intelligent-manufacturing brand style, clean enterprise information hierarchy, consistent admin/frontstage grids, disciplined typography, component sizes, status colors, and spacing.

## When to Use

Use this skill when the task mentions or implies any of the following:

- UI design, page layout, dashboard, admin system, portal, official site, login page, product page.
- Form, table, list page, details page, card, modal, drawer, notification, empty state, pagination, tab, breadcrumb, stepper.
- Theme, design token, CSS variable, Tailwind theme, Ant Design/Arco/Element theme, icon, color, font, spacing.
- “按公司UI规范”, “统一风格”, “优化布局”, “更专业”, “给 Codex 改前端”.

Do not use this skill for backend-only tasks unless the backend change directly affects UI contracts or API states displayed in UI.

## Required References

Load these files before making UI decisions:

1. `references/huixin-ui-spec.md` — distilled company UI specification.
2. `tokens/huixin.tokens.json` — machine-readable color, typography, spacing, grid, and component tokens.
3. `tokens/huixin-theme.css` — CSS variable implementation starter.
4. `templates/ui-implementation-checklist.md` — checklist to validate changes.
5. `templates/design-review-report.md` — format for UI review output.

Optional implementation starters:

- `templates/react-page-scaffold.tsx` with `templates/react-page-scaffold.css`
- `templates/agent-console-page.tsx` with `templates/agent-console-page.css`
- `templates/bid-agent-landing.html` with `templates/bid-agent-landing.css`
- `templates/tailwind.config.example.js`
- `templates/antd-theme.example.ts`
- `scripts/check-huixin-ui-tokens.mjs`

## Workflow

### 1. Classify the UI Surface

Before editing, classify the page as one of:

- **Frontstage / Portal**: official website, solution introduction, marketing landing page, customer-facing product page.
- **Middle/Backstage / Admin**: management system, dashboard, table/list, form, detail page, login page, monitoring page.
- **Hybrid**: customer portal with both marketing and workbench interactions.

Apply the correct grid and density:

- Frontstage: 1920px canvas, 1128px content width, 12 columns, 72px column, 24px gutter, 8px grid base.
- Admin: 1440px canvas, 1208px content width, 24 columns, 16px gutter, 24px margin, 232px fixed sidebar, flexible content region.

### 2. Scan the Existing Codebase

Identify:

- Framework: React, Vue, Next.js, Vite, Nuxt, etc.
- Styling approach: CSS/SCSS modules, Tailwind, CSS variables, styled-components, Less, Sass, UnoCSS.
- Component library: Ant Design, Arco, Element Plus, shadcn/ui, local component system.
- Existing theme/tokens files.
- Existing layout shell and routing conventions.

Do not add new production dependencies just for styling unless the user explicitly asked and the project already accepts that dependency category.

### 3. Install or Map Huixin Tokens

Prefer the least disruptive path:

1. If tokens already exist, map Huixin values into the existing token names.
2. If no token system exists, add CSS variables from `tokens/huixin-theme.css`.
3. If Tailwind exists, extend the Tailwind config using `templates/tailwind.config.example.js`.
4. If Ant Design exists, map to `templates/antd-theme.example.ts`.
5. If a component library exists, configure its theme rather than rewriting all components.

`tokens/huixin-theme.css` is intentionally tokens-only. Do not use starter CSS to override a project's global `body` styles unless the existing application theme expects that.

Never scatter raw hex values across components. Use variables, token objects, utility classes, or theme references.

### 4. Implement Layout

For admin/backstage pages:

- Use a fixed 232px sidebar if the shell has a side navigation.
- Use 24px page margins.
- Use 16px gutters within content grids.
- Use `minmax(0, 1fr)` to avoid overflow in CSS Grid.
- Keep table overflow inside the table container.
- Optimize for 1366px, 1440px, and 1920px widths.

For frontstage pages:

- Center content within a 1128px effective width.
- Use 12-column composition.
- Use wider whitespace and clearer focal hierarchy.
- Switch to mobile layout under 768px.

### 5. Implement Components

Apply the key component defaults:

- Button: 32px height, 14px text, 3px radius, `5px 16px` padding, 16px icon, 8px icon-text gap.
- Input/select/search/date/time: 32px height, 14px text, 3px radius, 16px icons unless the component calls for 24px.
- Form: 14px label/control text, right-aligned dense labels when appropriate, 16px label-control gap, 24px row gap.
- Card: 6px radius, `16px 24px` padding, 16px title, 14px body.
- Tag: 24px height target, `2px 8px` padding, 12px text, 14px icon.
- Dropdown: 6px container padding, 6px radius, `3px 8px` item padding, 3px item radius.
- Icon: 24/48/72px standard sizes, 16px common UI icon, 2px stroke, rounded caps/joins, SVG export.
- Empty state: flat illustration, 20px title, 14px description.
- Modal/alert: `16px 24px` padding, 20px icon, 14px text.

### 6. Protect Brand and Typography

- Use `HarmonyOS Sans`, `Source Han Sans SC`, `思源黑体`, `Microsoft YaHei`, `Arial`, sans-serif fallback.
- Use `D-DIN-PRO` or fallback for numeric metric emphasis when available.
- Allowed weights: 320, 400, 600.
- Do not embed or import unlicensed commercial font files.
- Do not distort or recolor official logo assets.
- Keep logo on pure color or visually clean image backgrounds.

### 7. Validate Quality

Run available commands in the repository:

- Lint.
- Typecheck.
- Tests.
- Build.
- Visual or screenshot checks if already available.

If checks are unavailable, explain what was inspected manually.

### 8. Final Response Format

When finishing a UI task, report in this structure:

```markdown
## 已完成
- ...

## 采用的慧新全智 UI 规范
- ...

## 校验结果
- `command`: result

## 仍需确认
- ...
```

Do not include huge code dumps unless the user explicitly asks. Summarize changed files and key implementation decisions.

## Design Review Mode

When the user asks for review rather than implementation:

1. Inspect the target page/component.
2. Compare against the spec in `references/huixin-ui-spec.md`.
3. Return issues by severity:
   - P0: breaks usability or cannot ship.
   - P1: visibly violates brand/layout/component rules.
   - P2: polish or consistency improvement.
4. Provide exact remediation: token, layout, component, or CSS class to change.
5. Use `templates/design-review-report.md` as the output format.

## Non-Negotiables

- No arbitrary new colors.
- No random spacing outside the 4px/8px system unless required by an existing library component.
- No unreadable dense text.
- No logo distortion.
- No hidden focus outlines unless replaced with visible accessible focus states.
- No page-level horizontal overflow at 1366px.
- No business logic regressions for visual-only tasks.
