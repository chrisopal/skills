---
name: opportunity-analysis-skill
description: Portable opportunity analysis capability for enterprise-service agents. Use it to turn visit notes, meeting transcripts, emails, OCR text, documents, or normalized evidence into structured accounts, contacts, opportunities, risks, next actions, local SQLite records, safe queries, and HTML/Markdown views. Designed to run inside different agent hosts such as Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or plain shell automation.
version: 0.3.0
---

# Opportunity Analysis Skill

## Purpose

Convert scattered customer material into a follow-up-ready opportunity asset:

1. Run `evidence_normalization`: normalize source material into Evidence.
2. Run `account_profile_extraction`: extract account profile, customer-side requirement contacts, current systems, pain points, and decision chain.
3. Run `opportunity_analysis`: extract need, stage, budget signal, timeline, competitors, risks, next actions, commercial confirmation questions, score, and win probability.
4. Mark critical assumptions as `confirmed`, `inferred`, `needs_sales_confirmation`, or `missing`.
5. Store results through a Storage Adapter.
6. Query opportunities through a controlled query object.
7. Render HTML and Markdown views through a Display Renderer.
8. Validate the package with a host-independent script.

This package is both a portable agent skill and a Python reference runtime. The default runtime is intentionally self-contained: no external service is required, and SQLite is the default storage.

The package is intentionally one P0 closed-loop skill, not three separate skills. The internal stages live under `src/opportunity_skill/stages/` so future agents, adapters, or model-backed extractors can reuse one stage without breaking the end-to-end `analyze/query/detail` workflow.

## Quick Run

From this folder:

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
opportunity-analysis analyze --input examples/input_visit_note.json --output-dir /tmp/opportunity-analysis-demo
opportunity-analysis query --min-score 60 --render-html --output-dir /tmp/opportunity-analysis-query
```

Without installation:

```bash
PYTHONPATH=src python3.12 -m opportunity_skill.cli analyze --input examples/input_visit_note.json
```

If `--db` is omitted, the runtime writes to:

- `$SKILL_DATA_DIR/opportunity-analysis/opportunity.db`, when `SKILL_DATA_DIR` is set;
- otherwise `./.skill_data/opportunity-analysis/opportunity.db` relative to the current working directory.

## Agent Workflow

When using this skill inside any agent host:

1. Inspect the input type.
2. If the input is raw audio, image, PDF, DOCX, PPTX, XLSX, webpage, or email, first obtain text or normalized Evidence through the host's available parser/OCR/transcription tools.
3. Treat the logical pipeline as `evidence_normalization -> account_profile_extraction -> opportunity_analysis -> storage -> display`.
4. Call the Python runtime for deterministic storage/rendering when a shell is available.
5. If shell execution is unavailable, follow the extraction rules and output contract manually, then persist through the host's equivalent storage adapter.
6. Never write arbitrary SQL from natural language. Convert requests to `schemas/query.schema.json`, then let the adapter execute parameterized queries.
7. Return JSON plus the rendered HTML/Markdown paths or content.

## Input Contract

Preferred input is `evidence_list`, where each item contains:

- `evidence_id`
- `source_type`
- `source_name`
- `content`
- `confidence`
- `source_refs`
- `requires_human_confirmation`
- optional `file_path` or `attachments` for source files that should be archived with the opportunity dossier

The reference runtime also accepts `materials` with text content and wraps them into Evidence objects.
When `file_path`, `path`, `source_path`, `source_ref`, or `attachments` points to a readable local file, the runtime copies it into an `attachments/` archive folder, records file metadata in SQLite, and exposes thumbnails or file links in the detail view.

Optional `sales_confirmation_answers` lets a host pass business staff answers back into the skill. Each answer should include `dimension_id`, `rating` (`strong`, `medium`, `weak`, or `unknown`), optional `answer_text`, and optional `answered_by`. These answers override inferred ratings and recalculate the commercial assessment and win probability.

The detail renderer must make unconfirmed commercial dimensions operational: show a radar chart for the major score categories, show each dimension score, and surface every `needs_sales_confirmation` dimension as a sales confirmation card with the exact `dimension_id` and question that the business staff should answer.

## Output Contract

Every successful analyze run returns:

```json
{
  "human_summary": "business-readable summary",
  "structured_data": {
    "account": {},
    "contacts": [],
    "decision_chain": [],
    "opportunity": {},
    "commercial_assessment": {},
    "sales_confirmation_questions": [],
    "sales_confirmation_answers": [],
    "risks": [],
    "next_actions": [],
    "evidence": [],
    "archived_files": [],
    "missing_information": [],
    "evidence_map": []
  },
  "storage_result": {
    "adapter": "sqlite",
    "saved": true,
    "account_id": "...",
    "opportunity_id": "...",
    "db_path": "..."
  },
  "display_result": {
    "template_id": "opportunity_card",
    "html": "...",
    "markdown": "...",
    "html_path": "...",
    "markdown_path": "...",
    "rendered_view_id": "..."
  }
}
```

## Quality Rules

- Do not invent customer names, contact names, phone numbers, emails, budget amounts, or signed commitments.
- Emit explicit budget amounts only when the source text states them.
- Stages, scores, win probabilities, and risk levels may be inferred, but include a reason and evidence mapping.
- Next actions must connect to missing information, stage movement, or risk mitigation.
- Key fields should reference Evidence when evidence exists.
- Render HTML from structured data only; escape user-controlled values.
- Templates must not include `<script>`, inline event handlers, or `javascript:` URLs.
- External adapter credentials must be provided by the host and must not be committed into this package.

## Extension Points

- Storage: default SQLite is implemented. Feishu, CRM/MCP, and PostgreSQL adapters are extension points under `storage/adapters/`.
- Display: default HTML/Markdown templates live under `display/templates/`. Hosts can replace templates while preserving the data contract.
- Extraction stages: `src/opportunity_skill/stages/evidence_normalization.py`, `account_profile_extraction.py`, and `opportunity_analysis.py` are lightweight heuristic references. Production deployments may replace one stage or the whole extractor with a model call as long as the output contract remains stable.
- Orchestration: `src/opportunity_skill/extractor.py` remains a compatibility wrapper that composes the three stages into one skill workflow.
- Query understanding: natural-language queries should become `schemas/query.schema.json` before storage execution.

## Validation

Run:

```bash
python3.12 scripts/validate_skill.py
```

The validator checks JSON files, Python compilation, template safety, evaluation cases, analyze/query/detail runtime behavior, and accidental distribution artifacts.
