# Requirements Research

Use research to collect evidence before writing requirements. Do not turn guesses into requirements.

## Research Plan

- Stakeholder map: buyer, operator, reviewer, admin, maintainer, downstream consumer
- Interview guide: goals, current workflow, pain points, exception cases, reporting needs
- Observation targets: existing forms, spreadsheets, tickets, system logs, approval records
- Source inventory: docs, code, API traces, database tables, screenshots, policies

## Evidence IDs

Record evidence as:

```text
EVID-001 | Source | Date | Claim | Confidence | Link/path
```

Confidence values:

- High: verified from source artifact or multiple aligned stakeholders
- Medium: single credible source
- Low: inferred, stale, or not directly observed

## Requirement Extraction

Convert evidence into business requirements:

```text
BR-001 | User/role | Need | Business value | Evidence | Priority | Open issues
```

Use `Must`, `Should`, `Could`, `Won't now` for priority unless the user provides another system.
