# SRS

Use the SRS phase to create implementation-ready requirements with stable IDs and acceptance criteria.

## Required Sections

- Purpose
- Scope
- Definitions
- User roles
- Business process
- Functional requirements
- Non-functional requirements
- Business rules
- Data requirements
- External interfaces
- Reporting/audit requirements
- Acceptance criteria
- Out of scope
- Open questions

## Functional Requirement Format

```text
FR-001 | Title
Source: BR-001, EVID-001
Role:
Trigger:
Preconditions:
Main flow:
Alternate flow:
Validation:
Acceptance criteria:
Priority:
Status:
```

## Non-Functional Requirement Format

```text
NFR-001 | Category | Requirement | Measurement | Priority | Source
```

Categories: performance, security, privacy, reliability, usability, accessibility, compatibility, observability, maintainability, compliance.

## Quality Rules

- Every `FR-*` must name a role, trigger, and acceptance criteria.
- Every must-have requirement must map to at least one test in the test spec.
- If a requirement depends on an unverified fact, mark status as `Unconfirmed`.
