# System Design

Use system design to map requirements to concrete software structure.

## Required Sections

- Design summary
- Module boundaries
- Domain model
- API contracts
- Data model
- State transitions
- Permissions and audit
- Integration points
- Error handling
- Observability
- Deployment/runtime notes
- Migration/backfill plan when relevant
- Test strategy hooks

## ID Formats

```text
DESIGN-001 | Concern | Decision | Requirements covered | Rationale
API-001 | Method/path or interface | Request | Response | Errors | Auth | Requirements covered
DATA-001 | Entity/table/document | Fields | Constraints | Lifecycle | Requirements covered
STATE-001 | Entity | From | To | Trigger | Guard | Side effects
```

## Design Discipline

- Prefer existing module boundaries and local helper APIs over new abstractions.
- Add abstractions only when they remove real complexity or match established patterns.
- Name operational risks that requirements do not reveal, especially data migration, compatibility, concurrency, observability, and permission drift.
