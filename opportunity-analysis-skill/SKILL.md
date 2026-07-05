---
name: opportunity-analysis-skill
description: Portable opportunity analysis capability for enterprise-service agents. Use it to turn visit notes, meeting transcripts, emails, OCR text, documents, or normalized evidence into structured accounts, contacts, opportunities, risks, next actions, local SQLite records, safe queries, and HTML/Markdown views. Designed to run inside different agent hosts such as Claude Code, WorkBuddy, OpenClaw, Hermes Agent, MateClaw, or plain shell automation.
version: 0.3.0
---

# Opportunity Analysis Skill

## Purpose

Convert scattered customer material into a follow-up-ready opportunity asset:

1. Normalize source material into Evidence.
2. Extract account, customer-side requirement contacts, decision chain, needs, budget signals, timeline, systems, competitors, risks, and next actions.
3. Mark critical assumptions as `confirmed`, `inferred`, or `missing`.
4. Store results through a Storage Adapter.
5. Query opportunities through a controlled query object.
6. Render HTML and Markdown views through a Display Renderer.
7. Validate the package with a host-independent script.

This package is both a portable agent skill and a Python reference runtime. The default runtime is intentionally self-contained: no external service is required, and SQLite is the default storage.

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
3. Call the Python runtime for deterministic storage/rendering when a shell is available.
4. If shell execution is unavailable, follow the extraction rules and output contract manually, then persist through the host's equivalent storage adapter.
5. Never write arbitrary SQL from natural language. Convert requests to `schemas/query.schema.json`, then let the adapter execute parameterized queries.
6. Return JSON plus the rendered HTML/Markdown paths or content.

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
- Extraction: `src/opportunity_skill/extractor.py` is a lightweight heuristic reference. Production deployments may replace it with a model call as long as the output contract remains stable.
- Query understanding: natural-language queries should become `schemas/query.schema.json` before storage execution.

## Validation

Run:

```bash
python3.12 scripts/validate_skill.py
```

The validator checks JSON files, Python compilation, template safety, evaluation cases, analyze/query/detail runtime behavior, and accidental distribution artifacts.
