# Huixin UI Design 2.0 — Distilled Implementation Reference

This reference converts the company UI design specification into implementation rules for coding agents and frontend engineers.

## 1. Brand and Style

### Keywords

- Intelligent / 智能
- Make & Manufacturing / 制造与生产
- Internet / 互联
- Future / 无限可能
- Industrial Internet, enterprise technology, reliable digital platform

### Style Direction

Huixin's UI should feel:

- Professional and enterprise-grade.
- Precise, clean, calm, and technology-oriented.
- Suitable for manufacturing, production, IoT, industrial software, dashboards, and management systems.
- Based on deep blue as the main brand color.

Avoid:

- Neon cyberpunk effects.
- Random gradients.
- Cartoonish visual language.
- Overly decorative shadows.
- Inconsistent color usage.
- Dense text without hierarchy.

## 2. Logo Rules

Use official logo assets whenever they exist in the repository.

Rules:

- Prefer the provided electronic logo files.
- Use horizontal logo in most cases; avoid vertical logo unless the layout requires it.
- Do not change, move internal parts, stretch, rotate, recolor, or distort the logo.
- Do not add shadow, bevel, emboss, glow, texture, or decorative effects.
- Place the logo only on pure-color or visually clean image backgrounds.
- Do not place the logo on a messy or high-contrast image area.
- Keep safe space around the logo equivalent to the marked logo reference unit.
- Keep logo away from page edges.
- Minimum size reference: 30mm for print or 150px for digital usage.

Text usage:

- When used as official brand logo, insert the logo image rather than typing the characters.
- In body paragraphs, write `慧新全智` directly without spaces.

App icon reference sizes:

- iOS: 120, 180, 152, 167, 1024px depending on device/store.
- Android: 48, 72, 96, 144, 192px for mdpi to xxxhdpi.

## 3. Color System

### Core Colors

| Role | Hex | Recommended CSS variable |
|---|---:|---|
| Main brand / primary | `#00405C` | `--hx-color-primary` |
| Click/action | `#0097BA` | `--hx-color-primary-action` |
| Selected background | `#CCF5FF` | `--hx-color-selected-bg` |
| Auxiliary green | `#A5D867` | `--hx-color-accent-green` |
| Auxiliary teal | `#0097BA` | `--hx-color-accent-teal` |
| Error | `#D54941` | `--hx-color-error` |
| Warning | `#E37318` | `--hx-color-warning` |
| Success | `#2BA471` | `--hx-color-success` |
| Border A | `#DBDFE7` | `--hx-color-border-a` |
| Border B | `#E3E7EE` | `--hx-color-border-b` |
| Background A | `#F0F2F5` | `--hx-color-bg-a` |
| Background B | `#F5F7FA` | `--hx-color-bg-b` |

### Brand Palette

| Token | Hex | Usage |
|---|---:|---|
| Brand1 | `#EDFAFF` | Highlight / very light background |
| Brand2 | `#DAF4FF` | Focus tint |
| Brand3 | `#B9DFF0` | Disabled tint |
| Brand4 | `#67BFE5` | Light hover/visual data |
| Brand5 | `#2495C7` | Hover |
| Brand6 | `#036F9E` | Normal interactive blue |
| Brand7 | `#015478` | Dark brand tone |
| Brand8 | `#00405C` | Primary/click/deep brand |
| Brand9 | `#063449` | Dark background support |
| Brand10 | `#01283A` | Deepest background support |

### Success Palette

| Token | Hex |
|---|---:|
| Success1 | `#E3F9E9` |
| Success2 | `#C6F3D7` |
| Success3 | `#92DAB2` |
| Success4 | `#56C08D` |
| Success5 | `#2BA471` |
| Success6 | `#008858` |
| Success7 | `#006C45` |
| Success8 | `#005334` |
| Success9 | `#003B23` |
| Success10 | `#002515` |

### Warning Palette

| Token | Hex |
|---|---:|
| Warning1 | `#FFF1E9` |
| Warning2 | `#FFD9C2` |
| Warning3 | `#FFB98C` |
| Warning4 | `#FA9550` |
| Warning5 | `#E37318` |
| Warning6 | `#BE5A00` |
| Warning7 | `#954500` |
| Warning8 | `#713300` |
| Warning9 | `#532300` |
| Warning10 | `#3B1700` |

### Error Palette

| Token | Hex |
|---|---:|
| Error1 | `#FFF0ED` |
| Error2 | `#FFD8D2` |
| Error3 | `#FFB9B0` |
| Error4 | `#FF9285` |
| Error5 | `#F6685D` |
| Error6 | `#D54941` |
| Error7 | `#AD352F` |
| Error8 | `#881F1C` |
| Error9 | `#68070A` |
| Error10 | `#490002` |

## 4. Typography

### Approved/Open Fonts

- HarmonyOS Sans
- 思源黑体 / Source Han Sans
- D-DIN-PRO

### Artistic Fonts

Use only in controlled brand/graphic contexts, not dense product UI:

- 钉钉进步体
- 斗鱼追光体

### System Fallbacks

The following can be used as system calls in UI, not embedded as font files:

- PingFang SC
- San Francisco UI
- Hiragino Sans GB
- Helvetica Neue
- Microsoft YaHei
- Arial

### Type Scale

| Level | Size | Line height | Weight | Application |
|---|---:|---:|---:|---|
| H1 | 36px | 54px | 600 | Home hero/banner large title |
| H2 | 24px | 36px | 600 | Page title / major focus area |
| H3 | 20px | 30px | 600 | Module title / subtitle |
| H4 | 18px | 28px | 600 | Section title / news title |
| H5 | 16px | 24px | 400/600 | Main navigation |
| Body | 14px | 22px | 400 | Paragraph, table, form, remarks |
| Assist | 12px | 18px | 400 | Remark, metadata, bottom navigation |

Weights:

- Light: 320
- Regular: 400
- Semibold: 600

## 5. Grid and Layout

### Frontstage Grid

For official websites, landing pages, solution pages, and public pages.

- Design board: 1920px.
- Effective content width: 1128px.
- 12-column grid.
- Column width: 72px.
- Gutter: 24px.
- Grid base: 8px.
- When width < 768px: use mobile layout.
- When width is 768px–1128px: column varies from 42px to 72px; gutter remains unchanged.
- When width > 1128px: content stays centered; side whitespace scales.

### Backstage/Admin Grid

For dashboards, management systems, lists, forms, details, login, and operational pages.

- Design board: 1440px.
- Effective content width: 1208px.
- 24-column grid.
- Gutter: 16px.
- Margin: 24px.
- Sidebar fixed width: 232px.
- Content region auto-resizes.
- Consider 1920px, 1440px, and 1366px resolutions.
- Sidebar and module gaps stay fixed; content dynamically scales.

### Layout Areas for Admin UI

Common page composition:

1. Logo area.
2. Side navigation.
3. Menu / top function bar.
4. Guide / breadcrumb area.
5. Main content area.
6. Copyright / footer info.

## 6. Spacing

Use the 4px and 8px spacing system:

```text
4, 8, 12, 16, 20, 24, 28, 32, 40
```

Use even values. Avoid one-off spacing like 13px, 17px, or 27px unless matching an existing component library internals.

## 7. Image Proportions

Supported image proportions:

- 4:3
- 3:2
- 2:1
- 16:10
- 16:9

Use consistent proportions within a single module. Place important visual focus using golden ratio / Fibonacci composition where applicable for marketing or banner visuals.

## 8. Icon Rules

### Design Guides

Maintain consistent visual size by designing within shape-specific guide areas:

- Circular icons.
- Square icons.
- Short/wide icons.
- Tall icons.
- Irregular icons.

### Sizes

- Primary icon size: 48px.
- Other standard icon sizes: 72px and 24px.
- Common component icon size: 16px.

### Style

- Solid stroke/fill style.
- Clear fill hierarchy.
- Stroke width: 2px.
- Rounded endpoints and rounded corners.
- Corner radius, stroke width, layer width/height should be even numbers when possible.
- Anchor positions should be integer values.
- Export custom icons as SVG.

### State Colors

- Default state: use `#333333` opacity scale: 10%, 20%, 40%, 100%.
- Selected state: use `#0097BA` opacity scale: 10%, 20%, 40%, 100%.

## 9. Component Rules

### Divider

- Support horizontal, vertical, and text divider.
- Use light border tokens.

### Button

- Height: 32px.
- Padding: `5px 16px 5px 16px`.
- Font: 14px.
- Radius: 3px.
- Icon size: 16px.
- Icon-text gap: 8px.
- Supported types: filled, outline, dashed, text.

### Link

- Font: 14px.
- Icon size: 16px.
- Icon-text gap: 8px.
- Support leading icon, basic text link, underline link, trailing icon.

### Anchor

- First-level anchor font: 12px.
- Common vertical step: 16px or 24px depending on density.

### Dropdown Menu

- Text: 14px.
- Icon: 16px.
- Container padding: `6px`.
- Container radius: 6px.
- Item padding: `3px 8px`.
- Item radius: 3px.
- Example width: 160px container, 148px inner menu.

### Pagination

- Support page size selector, page number, jump-to-page.
- Use compact enterprise density.

### Cascader / Checkbox

- Support single and multiple cascader.
- States: selected, default, hover, click, disabled, secondary selected.
- Checkbox states: unchecked, hover checked, checked, disabled unchecked, disabled checked, indeterminate, disabled indeterminate.

### Date Picker

- Input height: 32px.
- Padding: `4px 8px 4px 4px`.
- Font: 14px.
- Icon: 16px.
- Radius: 3px.

### Form

- Label font: 14px.
- Control text: 14px.
- Radius: 3px.
- Icon: 16px.
- Default dense form label alignment: right aligned.
- Row gap reference: 24px.
- Tag text: 12px; tag icon: 14px; tag padding `4px 8px 4px 4px`.

### Input

- Height: 32px.
- Padding: `5px 8px`.
- Font: 14px.
- Placeholder color: low-emphasis text.
- Entered text color: high-emphasis text.
- Icon: 16px.

### Number Input / Radio / Search / Selector

- Number input height: 32px; radius 3px; icon 16px.
- Search input padding: `4px 4px 4px 8px`; font 14px; icon 24px; radius 3px.
- Selector uses 32px height and same text/radius rules as input.

### Time Picker

- Padding: `5px 8px`.
- Font: 14px.
- Icon: 16px.
- Radius: 3px.
- Selected text color: brand normal.

### Avatar

- Common avatar sizes: 24px and 48px.

### Upload

Support:

- Basic file upload.
- Image upload.
- Drag upload.
- Input + file upload.

### Badge

- Height: 20px.
- Padding: `0 6px`.
- Font: 12px.

### Card

- Padding: `16px 24px`.
- Title font: 16px.
- Other text: 14px.
- Radius: 6px.
- Header/action height target: 40px.

### Collapse

- Header padding: `12px 16px`.
- Font: 14px.
- Icon: 16px.
- Expanded fill: neutral gray light background.
- Inner stroke: neutral divider.
- Height reference: 46px.

### Tag

- Padding: `2px 8px`.
- Font: 12px.
- Icon: 14px.
- Height target: 24px.

### Dialog / Alert

- Padding: `16px 24px`.
- Icon: 20px.
- Font: 14px.
- Support common info, success, warning, and error/destructive messages.

### Empty State

- Illustration style: flat.
- Title: 20px.
- Description: 14px.

### Login Page

- Button padding: `8px 12px`.
- Font: 16px.
- Icon: 18px.
- Button height reference: 40px.

## 10. Engineering Principles

- Prefer token-driven CSS variables and theme configuration.
- Keep UI consistent with existing app architecture.
- Maintain responsiveness and avoid page-level horizontal overflow.
- Preserve accessibility and keyboard interaction.
- Use status colors semantically.
- Avoid visual noise.
