# Opportunity Analysis Portable Skill Design

## Context

`opportunity-analysis-skill` should not be a Codex-only skill. It is the first example of a broader enterprise-service capability package that can run inside different agent hosts such as Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or shell automation.

The package must be useful by itself: a host agent can pass visit notes or normalized evidence, run the reference runtime, store the result, query it, and render a view without needing external services.

## Goals

- Provide a standalone closed loop: input -> analysis -> structured data -> SQLite storage -> controlled query -> HTML/Markdown display -> validation.
- Keep SQLite as the default implemented adapter.
- Leave clear extension contracts for Feishu, CRM/MCP, PostgreSQL, external model extraction, and custom display templates.
- Keep the package portable across agent hosts by avoiding Codex-specific metadata or tool assumptions.
- Remove generated runtime artifacts from the distributable skill.
- Add a host-independent validator that proves the package still runs.

## Non-Goals

- Implement live Feishu, CRM, or PostgreSQL API calls in this pass.
- Add third-party Python dependencies.
- Build a UI workbench.
- Replace the heuristic extractor with a production model call.

## Architecture

The package has four stable layers:

1. `SKILL.md` and `manifest.yaml` describe the portable agent contract.
2. `src/opportunity_skill/` is the Python reference runtime.
3. `schemas/`, `storage/`, and `display/` define the durable contracts.
4. `scripts/validate_skill.py` verifies the runtime and packaging surface.

SQLite is the default adapter. Feishu, CRM, and PostgreSQL adapters remain explicit extension stubs with configuration keys and `NotImplementedError` methods, so future integration work has a stable place to land without pretending support is already shipped.

## Data Flow

1. Host agent normalizes raw sources into text or Evidence.
2. `opportunity_skill.extractor.analyze` produces structured opportunity data.
3. `OpportunitySQLiteAdapter` auto-migrates and persists account, contact, opportunity, evidence, risk, action, rendered view, and run records.
4. `SkillDisplayRenderer` renders HTML and Markdown from structured data.
5. Query and detail commands read from storage and render list/detail views.

## Error Handling

- Missing `--db` uses `$SKILL_DATA_DIR/opportunity-analysis/opportunity.db`, then `./.skill_data/opportunity-analysis/opportunity.db`.
- Unknown external adapters fail explicitly through `NotImplementedError`.
- Natural-language queries must be converted to `schemas/query.schema.json` before execution.
- Templates must remain script-free and escape user-controlled values.

## Testing

The validator should run without external services:

- JSON syntax checks for schemas and examples.
- Python compilation for runtime and scripts.
- Template safety checks.
- Evaluation cases for expected stage and minimum score.
- Analyze/query/detail runtime smoke tests.
- Distribution noise checks for `.skill_data`, `outputs`, `*.egg-info`, `__pycache__`, and `*.pyc`.

## Rollout

This package becomes the pattern for future enterprise-service skills: receivables, delivery execution, customer success, contract fulfillment, and other business workflows should follow the same default-closed-loop plus adapter-extension shape.
