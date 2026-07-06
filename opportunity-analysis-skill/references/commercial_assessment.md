# Commercial Assessment Reference

This reference turns sales opportunity judgment into structured questions for business staff.

The runtime implementation lives in `src/opportunity_skill/assessment.py`. It is dependency-free and can be replaced by a model-backed evaluator as long as the output contract stays stable.

## Rating Scale

- `strong`: clear positive evidence or business confirmation.
- `medium`: partial evidence, plausible but still needs follow-up.
- `weak`: negative signal or material concern.
- `unknown`: not enough information.

## Categories

### Win Likelihood

Question: how likely are we to win this opportunity?

- Customer purchase intent
- Customer insight
- Customer relationship
- Our reputation
- Competitors
- Solution fit
- Value proposition
- Pricing and deal shape
- Partner/team cooperation
- Presentation, demo, or site visit readiness
- Sales team readiness

### Deal Attractiveness

Question: do we want this deal given financial and strategic characteristics?

- Strategic customer value
- Contract scale and type
- Margin and deal shape
- Reuse of existing products, solutions, assets, or templates

### Delivery Confidence

Question: can we deliver successfully with acceptable risk?

- Delivery skills and staffing
- Delivery cost structure
- Delivery risk

## Confirmation Loop

1. Infer a first-pass rating from evidence.
2. Mark uncertain or critical dimensions as `needs_sales_confirmation`.
3. Generate the highest-priority questions for business staff.
4. Accept `sales_confirmation_answers` with `dimension_id`, `rating`, `answer_text`, and optional owner/timestamp fields.
5. Recalculate opportunity score, win probability, confidence level, and unanswered critical count.
