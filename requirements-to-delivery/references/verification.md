# Verification

Use verification to prove the delivery claim, not to decorate the final answer.

## Artifact Validation

Run:

```bash
python3 requirements-to-delivery/scripts/validate_delivery_artifacts.py delivery/<project-slug> --profile full
```

Use a narrower profile when the user requested only one phase.

## Test Evidence

Record:

- Commands run
- Exit status
- Important pass/fail lines
- Manual checks
- Screenshots or local URLs for visual prototypes
- Known gaps
- Residual risks

## Acceptance Report

Include:

- Scope delivered
- Requirements covered
- Tests performed
- Defects found and fixed
- Not tested
- Open questions
- Recommendation: proceed, proceed with risk, or do not proceed
