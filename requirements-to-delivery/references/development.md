# Development

Use development planning and implementation to convert design into small, verifiable changes.

## Task Format

```text
TASK-001 | Title
Requirements: FR-001, NFR-001
Design: DESIGN-001, API-001, DATA-001
Files/modules:
Implementation notes:
Tests:
Risk:
Status:
```

## Execution Rules

- Inspect the existing codebase before editing.
- Keep diffs small and reversible.
- Reuse local utilities, styles, module boundaries, and test conventions.
- Do not add dependencies unless explicitly requested or clearly unavoidable.
- For frontend work, verify responsive layout and no overlapping text or controls.
- For backend work, verify API contracts, validation, permissions, and persistence behavior.

## Development Order

1. Lock behavior with tests when changing existing behavior.
2. Implement shared contracts or schema changes.
3. Implement backend/domain logic.
4. Implement UI or integration surface.
5. Run targeted verification.
6. Update acceptance report and traceability matrix.
