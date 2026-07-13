# Problem Definition Skill

Portable problem-definition capability for enterprise-service agents.

This package is designed to run as a standalone closed loop inside many agent hosts: Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or plain shell automation.

## What It Does

- Accepts opportunity-analysis output, normalized Evidence, customer statements, meeting notes, requirements, or text materials.
- Preserves the customer’s stated demand separately from deeper interpretation.
- Distinguishes symptoms, causes, constraints, and solution preferences.
- Produces surface problem, deep problem, decision problem, impacts, success criteria, assumptions, missing information, clarification questions, and solution entry points.
- Stores the result in local SQLite by default.
- Runs controlled problem-definition queries.
- Renders HTML and Markdown views.
- Leaves clear extension points for CRM/MCP, Feishu, PostgreSQL, model-backed analysis, and custom display templates.

The bundled analyzer is a lightweight reference implementation. Production deployments can replace one internal stage or `src/problem_definition_skill/analyzer.py` with a model-backed analyzer while keeping the same schemas, storage contract, and display contract.

## Internal Pipeline Stages

This remains one closed-loop skill with a single `analyze/query/detail` runtime. Internally, the analysis is split into three reusable stages:

- `evidence_normalization`: implemented by `src/problem_definition_skill/stages/evidence_normalization.py`; collects source text and evidence references.
- `problem_framing`: implemented by `src/problem_definition_skill/stages/problem_framing.py`; separates stated demand, symptoms, root causes, and constraints.
- `decision_definition`: implemented by `src/problem_definition_skill/stages/decision_definition.py`; produces the decision question, impacts, success criteria, assumptions, missing information, clarification questions, and entry points.

`src/problem_definition_skill/analyzer.py` composes these stages for backward-compatible host integration.

## Quick Start

Use Python 3.10 or newer.

```bash
cd problem-definition-skill
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
problem-definition analyze --input examples/input_from_opportunity_skill.json --output-dir /tmp/problem-definition-demo
problem-definition query --keyword 质检 --render-html --output-dir /tmp/problem-definition-query
```

The `analyze` command writes its complete output-contract envelope to stdout and `<output-dir>/result.json`. For a clean repository checkout, set `SKILL_DATA_DIR` or pass `--db` so runtime data is not created under the skill directory.

Without installation:

```bash
PYTHONPATH=src python3.12 -m problem_definition_skill.cli analyze --input examples/input_from_opportunity_skill.json
```

## Default Storage

If `--db` is omitted, the runtime writes to:

```text
$SKILL_DATA_DIR/problem-definition/problem_definition.db
```

When `SKILL_DATA_DIR` is not set, it falls back to:

```text
./.skill_data/problem-definition/problem_definition.db
```

## Detail View

Use the `problem_definition_id` returned by `analyze` or `query`:

```bash
problem-definition detail \
  --problem-definition-id pd_xxxxx \
  --template decision_brief \
  --output-dir /tmp/problem-definition-detail
```

Available templates:

- `problem_definition_card`
- `problem_tree`
- `clarification_questions`
- `decision_brief`

## Agent Host Integration

Any host agent can use the package in one of two ways:

- Shell mode: call the Python CLI and read JSON/stdout plus generated HTML/Markdown files.
- Contract mode: follow `SKILL.md`, `schemas/`, and the storage/display contracts when shell execution is unavailable.

The preferred upstream input is the output from `opportunity-analysis-skill`. The preferred downstream consumers are solution-outline, PPT-storyline, enterprise-architecture, and SOW/scope skills.

## Validation

Run the portable validator:

```bash
python3.12 scripts/validate_skill.py
```

It verifies the declared JSON contracts, all templates, end-to-end persistence and rendering, input rejection, and query HTML escaping. Install the package dependencies first with `python -m pip install -e .`.
