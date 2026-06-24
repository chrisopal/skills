---
name: requirements-to-delivery
description: End-to-end software/product delivery workflow for turning ideas, business requests, or vague feature asks into requirements research, technical solution, SRS, system design, prototype plan or prototype implementation, development tasks, tests, and acceptance evidence. Use when the user asks to do demand research, requirements discovery, technical方案, 需求规格说明书/SRS, 系统设计, 原型, development planning, or a full process from idea to implementation.
---

# Requirements To Delivery

Use this skill to run a traceable product/software delivery workflow from an unclear request to implementation-ready or implemented artifacts.

## Operating Rules

- Keep a single traceability chain from evidence to acceptance: `EVID-* -> BR-* -> FR-* / NFR-* -> DESIGN-* / API-* / DATA-* -> TASK-* -> TEST-*`.
- Prefer working in the user's current repo when the request targets an existing system. Reuse its architecture, UI conventions, test tools, and terminology.
- Do not invent business facts, stakeholders, metrics, APIs, legal constraints, or system behavior. Mark thin facts as `Unconfirmed` or `未确认`.
- Ask only when a missing answer creates an irreversible or materially branching decision. Otherwise proceed with explicit assumptions.
- Produce the smallest complete artifact set for the requested stage. If the user asks for the whole process, create all stage artifacts.
- Before development, verify that requirements, design, and test intent are represented. If the user explicitly asks for fast prototyping, keep a lightweight SRS and design note instead of skipping them.

## Quick Start

1. Create a delivery workspace when a durable artifact set is needed:

   ```bash
   python3 requirements-to-delivery/scripts/init_delivery_workspace.py <project-slug>
   ```

2. Load only the reference file for the active phase:

   - Intake and scoping: `references/intake.md`
   - Research and interviews: `references/requirements-research.md`
   - Technical方案: `references/technical-solution.md`
   - SRS: `references/srs.md`
   - System design: `references/system-design.md`
   - Prototype: `references/prototype.md`
   - Development: `references/development.md`
   - Verification: `references/verification.md`

3. Validate artifacts before claiming completion:

   ```bash
   python3 requirements-to-delivery/scripts/validate_delivery_artifacts.py delivery/<project-slug> --profile full
   ```

## Workflow

### 1. Intake

Read `references/intake.md`. Clarify goal, users, scope boundary, current system context, constraints, target output, and decision deadlines.

Output:
- `00-intake.md`
- Open questions with explicit default assumptions

### 2. Requirements Research

Read `references/requirements-research.md`. Build a research plan, interview guide, stakeholder map, scenario inventory, and evidence log.

Output:
- `01-research-plan.md`
- Evidence IDs such as `EVID-001`
- Business requirement IDs such as `BR-001`

### 3. Requirements Analysis and SRS

Read `references/srs.md`. Convert research into structured requirements and acceptance criteria.

Output:
- `02-requirements-analysis.md`
- `04-srs.md`
- Functional IDs `FR-*`, non-functional IDs `NFR-*`, rule IDs `RULE-*`

### 4. Technical Solution

Read `references/technical-solution.md`. Compare feasible approaches, name the preferred path, record rejected alternatives, and surface risks.

Output:
- `03-technical-solution.md`
- Decision IDs `DEC-*`

### 5. System Design

Read `references/system-design.md`. Define modules, domain model, APIs, data model, permissions, state transitions, integration points, and deployment/runtime concerns.

Output:
- `05-system-design.md`
- Design IDs `DESIGN-*`, API IDs `API-*`, data IDs `DATA-*`

### 6. Prototype

Read `references/prototype.md`. Choose the lightest prototype that answers the product question: paper flow, static HTML, existing frontend route, or clickable UI.

Output:
- `06-prototype/`
- `06-prototype/prototype-brief.md`
- Screenshot or local URL when a runnable prototype exists

### 7. Development

Read `references/development.md`. Split tasks, implement in the existing codebase style, and keep changes tied to requirement/design/test IDs.

Output:
- `07-development-plan.md`
- Code changes when requested
- Test implementation or manual verification record

### 8. Verification and Acceptance

Read `references/verification.md`. Validate required artifacts, run tests, and update the traceability matrix.

Output:
- `08-test-spec.md`
- `09-acceptance-report.md`
- `traceability-matrix.md`

## Stage Gate

Continue to the next stage only when the current stage has enough evidence for the next decision:

- Research gate: target users, scenarios, constraints, and unresolved assumptions are visible.
- SRS gate: every important feature has a `FR-*` ID and acceptance criteria.
- Solution gate: the selected technical approach names tradeoffs and rejected alternatives.
- Design gate: module, API/data, permission, and state impacts are explicit.
- Prototype gate: the prototype purpose and validation target are clear.
- Development gate: tasks map back to requirements and tests.
- Acceptance gate: tests or manual checks prove the requested outcome, with residual risks stated.

## Templates

When creating artifacts manually, copy from `assets/templates/`. When creating a full workspace, prefer the initialization script so filenames and placeholders stay consistent.
