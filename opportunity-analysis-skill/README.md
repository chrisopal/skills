# Opportunity Analysis Skill

Portable opportunity analysis capability for enterprise-service agents.

This package is designed to run as a standalone closed loop inside many agent hosts: Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or plain shell automation.

## What It Does

- Accepts normalized Evidence or text materials.
- Archives readable source files from `file_path`, `path`, `source_path`, `source_ref`, or `attachments`.
- Extracts account, customer-side requirement contacts, decision chain, opportunity, needs, budget signals, timeline, systems, competitors, risks, and next actions.
- Generates sales/business confirmation questions and recalculates win probability from confirmed answers.
- Stores the result in local SQLite by default.
- Runs controlled opportunity queries.
- Renders HTML and Markdown views, including thumbnails and links for archived source material.
- Leaves clear extension points for Feishu, CRM/MCP, PostgreSQL, external model extraction, and custom display templates.

The bundled extractor is a lightweight reference implementation. Production deployments can replace one internal stage or `src/opportunity_skill/extractor.py` with a model-backed extractor while keeping the same schemas, storage contract, and display contract.

## Internal Pipeline Stages

This is still one closed-loop skill with a single `analyze/query/detail` runtime. Internally, the analysis is split into three reusable stages:

- `evidence_normalization`: implemented by `src/opportunity_skill/stages/evidence_normalization.py`; wraps normalized evidence or parsed text materials and preserves file/archive metadata.
- `account_profile_extraction`: implemented by `src/opportunity_skill/stages/account_profile_extraction.py`; extracts customer profile, systems, pain points, requirement owners, contacts, and decision-chain nodes.
- `opportunity_analysis`: implemented by `src/opportunity_skill/stages/opportunity_analysis.py`; extracts opportunity need, stage, budget/timeline/competitor signals, commercial assessment, score, risks, next actions, and missing information.

`src/opportunity_skill/extractor.py` composes these stages for backward-compatible host integration. Hosts can call the full skill for the business closed loop, or reuse a stage directly when an adapter only needs normalization, customer profiling, or opportunity scoring.

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

When a shell host can interact with a sales or business user, run:

```bash
opportunity-analysis analyze \
  --input examples/input_visit_note.json \
  --interactive-confirmation \
  --template opportunity_detail \
  --output-dir /tmp/opportunity-analysis-confirmed
```

This first infers uncertain dimensions, asks the generated sales confirmation questions, records answers as `sales_confirmation_answers`, and then reruns the final scoring/storage/rendering pass. Answers such as `未知`, `不确定`, `待确定`, or `待确认` are normalized to `unknown` and still receive the unknown score.

## Detail View

Use the `opportunity_id` returned by `analyze` or `query`:

```bash
opportunity-analysis detail \
  --opportunity-id opp_xxxxx \
  --template opportunity_detail \
  --output-dir /tmp/opportunity-analysis-detail
```

The detail view renders the commercial assessment as:

- Dimension radar charts grouped by category: win likelihood, deal attractiveness, and delivery confidence. The category score is shown as a summary, while each radar axis represents concrete dimensions such as competitors, customer insight, customer relationship, and solution fit.
- A complete dimension-score list for every assessment dimension.
- A dimension table with the current evidence status and confirmation question for each assessment dimension. The business detail page does not render separate sales-confirmation cards; unresolved questions should be handled during the interactive analysis workflow.

## Agent Host Integration

Any host agent can use the package in one of two ways:

- Shell mode: call the Python CLI and read JSON/stdout plus generated HTML/Markdown files.
- Contract mode: follow `SKILL.md`, `schemas/`, `storage/storage_contract.md`, and `display/display_contract.md` manually when shell execution is unavailable.

Raw audio, image, document, email, and webpage inputs should be transcribed, OCRed, parsed, or extracted before this skill runs. The reference runtime accepts either `evidence_list` or text `materials`.

For materials that came from real files, pass the readable local path as `file_path`, `path`, `source_path`, `source_ref`, or inside `attachments`. The default runtime copies those files into an `attachments/` archive next to the rendered output when `--output-dir` is provided, or next to the SQLite database when no output directory is provided. The SQLite adapter records `evidence_files` metadata so a later `detail` render can show thumbnails and clickable file links in the opportunity dossier.

Contacts are intended to represent customer-side people tied to the demand, not every name found in the material. The reference extractor prioritizes requirement owners, project owners, technical/IT evaluators, procurement owners, and final decision makers. The detail view also renders a `decision_chain` table with confirmed and missing nodes.

## Commercial Assessment

The skill separates raw material extraction from commercial judgment. Initial analysis infers a `commercial_assessment` from available evidence, then generates `sales_confirmation_questions` for the business owner. Hosts can pass answered questions back through `sales_confirmation_answers`:

```json
{
  "dimension_id": "customer_purchase_intent",
  "rating": "strong",
  "answer_text": "客户已立项，计划本季度完成方案评审并进入采购。",
  "answered_by": "商务负责人"
}
```

Ratings are `strong`, `medium`, `weak`, or `unknown`; Chinese `强`, `中`, `弱`, `未知`, `不确定`, `待确定`, and `待确认` are accepted. Confirmed answers override inferred ratings and recalculate:

- `win_likelihood_score`
- `deal_attractiveness_score`
- `delivery_confidence_score`
- `overall_opportunity_score`
- `win_probability`
- `assessment_confidence_score`

When a dimension is not confirmed, it remains in `commercial_assessment.dimensions` with `evidence_status=needs_sales_confirmation`, and generated questions remain available in `sales_confirmation_questions`. Hosts should ask those questions during the analysis workflow, collect `sales_confirmation_answers`, and rerun scoring instead of showing separate confirmation cards in the business detail page.

## Adapter Strategy

SQLite is the only implemented storage adapter in this package. Other adapters are intentionally contract stubs:

- `storage/adapters/feishu_adapter.py`: Feishu Docs, Sheets, or Bitable.
- `storage/adapters/crm_adapter.py`: customer CRM APIs or MCP-backed CRM tools.
- `storage/adapters/postgres_adapter.py`: team or enterprise PostgreSQL.

Hosts should provide credentials through configuration references, environment variables, or secret managers. Do not commit API tokens or customer secrets into this package.

External adapters should preserve the same file metadata contract as SQLite. For example, a Feishu adapter may upload archived files to Drive and store the resulting Drive token or URL in the adapter-specific fields while keeping `evidence_id`, `file_name`, `mime_type`, `sha256`, and display link fields available to the renderer.

## Validation

Run the portable validator:

```bash
python3.12 scripts/validate_skill.py
```

It checks JSON files, Python compilation, template safety, evaluation cases, analyze/query/detail runtime behavior, and distribution noise such as `outputs/`, `.skill_data/`, `*.egg-info`, `__pycache__`, and `*.pyc`.
