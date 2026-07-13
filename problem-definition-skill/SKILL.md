---
name: problem-definition-skill
description: Portable problem-definition capability for enterprise-service agents. Use it to turn opportunity outputs, customer statements, meeting notes, interview transcripts, requirements, or normalized evidence into surface problems, deep problems, decision questions, business impacts, success criteria, constraints, assumptions, clarification questions, solution entry points, local SQLite records, safe queries, and HTML/Markdown views. Designed to run inside different agent hosts such as Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or plain shell automation.
version: 0.2.0
---

# Problem Definition Skill

## Purpose

Convert ambiguous customer demand into a decision-ready problem definition asset:

1. Run `evidence_normalization`: normalize opportunity output, customer statements, notes, and evidence.
2. Run `problem_framing`: separate stated demand, symptoms, root causes, constraints, and solution preferences.
3. Run `decision_definition`: define the management decision, business impacts, success criteria, assumptions, missing information, and clarification questions.
4. Mark critical conclusions as `confirmed`, `inferred`, or `missing`.
5. Store results through a Storage Adapter.
6. Query problem definitions through a controlled query object.
7. Render HTML and Markdown views through a Display Renderer.
8. Validate the package with a host-independent script.

This package is both a portable agent skill and a Python reference runtime. The default runtime is intentionally self-contained: SQLite is the default storage, and no external model service is required.

The package is intentionally one P0 closed-loop skill, not several disconnected prompts. Internal stages live under `src/problem_definition_skill/stages/` so future agents or model-backed analyzers can replace one stage without breaking the end-to-end `analyze/query/detail` workflow.

## Quick Run

From this folder:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
problem-definition analyze --input examples/input_from_opportunity_skill.json --output-dir /tmp/problem-definition-demo
problem-definition query --keyword 质检 --render-html --output-dir /tmp/problem-definition-query
```

Without installation:

```bash
PYTHONPATH=src python3.12 -m problem_definition_skill.cli analyze --input examples/input_from_opportunity_skill.json
```

If `--db` is omitted, the runtime writes to:

- `$SKILL_DATA_DIR/problem-definition/problem_definition.db`, when `SKILL_DATA_DIR` is set;
- otherwise `./.skill_data/problem-definition/problem_definition.db` relative to the current working directory.

## Agent Workflow

When using this skill inside any agent host:

1. Inspect the input type.
2. Prefer the structured output from `opportunity-analysis-skill`; otherwise normalize customer statements, meeting notes, interview transcripts, requirements, or Evidence.
3. Treat the logical pipeline as `evidence_normalization -> problem_framing -> decision_definition -> storage -> display`.
4. Preserve the customer’s original wording before interpreting deeper problems.
5. Do not treat a requested system, platform, module, or AI tool as the problem itself; treat it as a proposed solution until evidence proves otherwise.
6. Call the Python runtime for deterministic storage/rendering when a shell is available.
7. If shell execution is unavailable, follow the extraction rules and output contract manually, then persist through the host's equivalent storage adapter.
8. Never write arbitrary SQL from natural language. Convert requests to `schemas/query.schema.json`, then let the adapter execute parameterized queries.
9. Return JSON plus rendered HTML/Markdown paths or content.

## Input Contract

Preferred input is the structured output of the opportunity analysis skill, including:

- `account`, `contacts`, `decision_chain`, and `opportunity`;
- `risks`, `next_actions`, `missing_information`, and `evidence_map`;
- normalized `evidence` with source identifiers and confidence.

The reference runtime also accepts:

- `materials` containing text content;
- `evidence_list`;
- `customer_statements`;
- `meeting_notes`;
- plain `text`.

Each source should preserve a source identifier where possible so key problem conclusions remain traceable.

## Output Contract

Every successful analyze run returns:

```json
{
  "human_summary": "business-readable summary",
  "structured_data": {
    "case_name": "...",
    "account_id": "...",
    "opportunity_id": "...",
    "problem_definition": {
      "surface_problem": {},
      "deep_problem": {},
      "decision_problem": {},
      "business_impacts": [],
      "success_criteria": [],
      "constraints": [],
      "assumptions": [],
      "missing_information": [],
      "solution_entry_points": []
    },
    "clarification_questions": [],
    "evidence_map": []
  },
  "storage_result": {
    "adapter": "sqlite",
    "saved": true,
    "problem_definition_id": "...",
    "db_path": "..."
  },
  "display_result": {
    "template_id": "problem_definition_card",
    "html": "...",
    "markdown": "...",
    "html_path": "...",
    "markdown_path": "..."
  }
}
```

## Quality Rules

- Preserve customer wording separately from consultant interpretation.
- Do not invent budgets, KPI baselines, target values, decision makers, current-state facts, or signed commitments.
- Do not convert a requested product or system directly into the root problem.
- Mark every critical conclusion as `confirmed`, `inferred`, or `missing`.
- Deep problems must state their reasoning and business impact.
- Success criteria should be measurable where evidence permits; otherwise use `target_value=待确认`.
- Clarification questions must validate the problem, decision, scope, value, constraints, or solution design.
- Limit solution entry points to three concise directions; do not expand into a full solution architecture.
- Render HTML from structured data only; escape user-controlled values.
- Templates must not include `<script>`, inline event handlers, or `javascript:` URLs.
- External adapter credentials must be provided by the host and must not be committed into this package.

## Extension Points

- Storage: default SQLite is implemented. CRM/MCP, Feishu, and PostgreSQL adapters can implement the same storage contract.
- Display: default HTML/Markdown templates live under `display/templates/`. Hosts can replace templates while preserving the data contract.
- Analysis stages: `evidence_normalization.py`, `problem_framing.py`, and `decision_definition.py` are lightweight heuristic references. Production deployments may replace one stage or the whole analyzer with a model call while keeping the output contract stable.
- Query understanding: natural-language queries should become `schemas/query.schema.json` before storage execution.
- Downstream orchestration: this skill is designed to feed `solution-outline-skill`, `ppt-storyline-skill`, `enterprise-architecture-skill`, and `sow-scope-skill`.

## Validation

Run:

```bash
python3.12 scripts/validate_skill.py
```

The validator checks JSON schemas and fixtures, Python syntax without creating source-tree bytecode, template safety, all display templates, analyze/query/detail runtime behavior, escaped query HTML, invalid-input rejection, and accidental distribution artifacts.
