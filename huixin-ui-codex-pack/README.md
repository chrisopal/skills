# Huixin UI Codex Pack

This package contains a Codex-ready repository instruction file and a reusable UI design skill based on Huixin UI Design 2.0.

## Contents

```text
AGENTS.md
.agents/skills/huixin-ui-design/
  SKILL.md
  references/huixin-ui-spec.md
  tokens/huixin.tokens.json
  tokens/huixin-theme.css
  templates/ui-implementation-checklist.md
  templates/design-review-report.md
  templates/codex-task-prompts.md
  templates/react-page-scaffold.tsx
  templates/react-page-scaffold.css
  templates/agent-console-page.tsx
  templates/agent-console-page.css
  templates/agent-console-preview.html
  templates/bid-agent-landing.html
  templates/bid-agent-landing.css
  templates/tailwind.config.example.js
  templates/antd-theme.example.ts
  scripts/check-huixin-ui-tokens.mjs
  agents/openai.yaml
```

## Installation

Copy the files into the root of the target frontend repository:

```bash
cp AGENTS.md /path/to/repo/AGENTS.md
cp -R .agents /path/to/repo/.agents
```

Then start Codex from the repository root or any subdirectory inside it.

## Usage

In Codex, use:

```text
Use $huixin-ui-design. Refactor this page to match Huixin UI Design 2.0 while preserving business logic.
```

or:

```text
Use $huixin-ui-design in review mode. Review the dashboard UI against Huixin UI Design 2.0 and return P0/P1/P2 issues.
```
