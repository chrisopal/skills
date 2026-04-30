# Codex Task Prompt Templates for Huixin UI

## 1. Implement a New Admin Page

```text
Use $huixin-ui-design.
Create/implement the [page name] admin page according to Huixin UI Design 2.0.
Requirements:
- Surface: admin/backstage
- Main content: [describe modules]
- Use existing project component library and theme patterns
- Use Huixin tokens for color, typography, spacing, and component sizing
- Avoid page-level horizontal overflow at 1366px
- Run available lint/typecheck/build checks
Return changed files and validation results.
```

## 2. Refactor Existing Page to Company UI Spec

```text
Use $huixin-ui-design.
Refactor [route/file/component] to match Huixin UI Design 2.0 while preserving business logic and API behavior.
Focus on:
- Layout hierarchy and spacing
- Brand color/token usage
- Form/table/card/button consistency
- Responsive behavior
Do not add new dependencies unless absolutely necessary.
Run available checks and summarize risks.
```

## 3. Create Token System

```text
Use $huixin-ui-design.
Add Huixin UI Design 2.0 tokens to this frontend project.
First inspect the existing styling/theme setup, then choose the least disruptive option:
- CSS variables, or
- Tailwind theme extension, or
- Ant Design/Arco/Element theme mapping.
Avoid scattering raw hex values.
Include a short usage example.
Run lint/typecheck/build if available.
```

## 4. UI Review Only

```text
Use $huixin-ui-design in review mode.
Review [route/file/screenshot/component] against Huixin UI Design 2.0.
Return P0/P1/P2 issues with exact remediation suggestions.
Do not modify code unless I explicitly approve implementation.
```

## 5. Dashboard Polish

```text
Use $huixin-ui-design.
Polish the dashboard UI in [file/route].
Keep data and business logic unchanged.
Improve:
- Card hierarchy
- Metric typography
- Chart spacing and color semantics
- Table density
- 1366px layout usability
Run validation and report changed files.
```
