# Opportunity Analysis Skill

Portable opportunity analysis capability for enterprise-service agents.

This package is designed to run as a standalone closed loop inside many agent hosts: Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or plain shell automation.

## What It Does

- Accepts normalized Evidence or text materials.
- Extracts account, contacts, opportunity, needs, budget signals, timeline, systems, competitors, risks, and next actions.
- Stores the result in local SQLite by default.
- Runs controlled opportunity queries.
- Renders HTML and Markdown views.
- Leaves clear extension points for Feishu, CRM/MCP, PostgreSQL, external model extraction, and custom display templates.

The bundled extractor is a lightweight reference implementation. Production deployments can replace `src/opportunity_skill/extractor.py` with a model-backed extractor while keeping the same schemas, storage contract, and display contract.

## Quick Start

Use Python 3.10 or newer. On this machine, `python3.12` is a safe choice.

```bash
cd opportunity-analysis-skill
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
opportunity-analysis analyze --input examples/input_visit_note.json --output-dir /tmp/opportunity-analysis-demo
opportunity-analysis query --min-score 60 --render-html --output-dir /tmp/opportunity-analysis-query
```

Without installation:

```bash
cd opportunity-analysis-skill
PYTHONPATH=src python3.12 -m opportunity_skill.cli analyze --input examples/input_visit_note.json
```

## Default Storage

If `--db` is omitted, the runtime writes to:

```text
$SKILL_DATA_DIR/opportunity-analysis/opportunity.db
```

When `SKILL_DATA_DIR` is not set, it falls back to:

```text
./.skill_data/opportunity-analysis/opportunity.db
```

You can still pass an explicit path:

```bash
opportunity-analysis analyze \
  --input examples/input_visit_note.json \
  --db /tmp/opportunity-analysis/opportunity.db \
  --output-dir /tmp/opportunity-analysis-demo
```

## Detail View

Use the `opportunity_id` returned by `analyze` or `query`:

```bash
opportunity-analysis detail \
  --opportunity-id opp_xxxxx \
  --template opportunity_detail \
  --output-dir /tmp/opportunity-analysis-detail
```

## Agent Host Integration

Any host agent can use the package in one of two ways:

- Shell mode: call the Python CLI and read JSON/stdout plus generated HTML/Markdown files.
- Contract mode: follow `SKILL.md`, `schemas/`, `storage/storage_contract.md`, and `display/display_contract.md` manually when shell execution is unavailable.

Raw audio, image, document, email, and webpage inputs should be transcribed, OCRed, parsed, or extracted before this skill runs. The reference runtime accepts either `evidence_list` or text `materials`.

## Adapter Strategy

SQLite is the only implemented storage adapter in this package. Other adapters are intentionally contract stubs:

- `storage/adapters/feishu_adapter.py`: Feishu Docs, Sheets, or Bitable.
- `storage/adapters/crm_adapter.py`: customer CRM APIs or MCP-backed CRM tools.
- `storage/adapters/postgres_adapter.py`: team or enterprise PostgreSQL.

Hosts should provide credentials through configuration references, environment variables, or secret managers. Do not commit API tokens or customer secrets into this package.

## Validation

Run the portable validator:

```bash
python3.12 scripts/validate_skill.py
```

It checks JSON files, Python compilation, template safety, evaluation cases, analyze/query/detail runtime behavior, and distribution noise such as `outputs/`, `.skill_data/`, `*.egg-info`, `__pycache__`, and `*.pyc`.
