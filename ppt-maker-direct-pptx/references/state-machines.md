# State Machines

Two state machines drive interactive gate progress.

## Page state machine (per slide)

Three layers — `outline_status`, `intent_status`, `image_status` — each
following the same 4-state graph (except `image_status`, which is derived).

```
        ┌──────────────┐
        │    draft     │
        └──────┬───────┘
               │
               ▼
       ┌───────────────────┐
       │  pending_review   │ ◀───────┐
       └────────┬──────────┘         │
                │                    │
        ┌───────┴───────┐            │
        ▼               ▼            │
  ┌──────────┐   ┌────────────────┐  │
  │  locked  │ ◀─│  needs_rework  │──┘
  └────┬─────┘   └───┬────────────┘
       │             ▲
       └─────────────┘
       (re-open via reset_pages)
```

### Cross-layer rule

`intent_status` is only allowed to advance into `pending_review` or `locked`
when the corresponding `outline_status` is already `locked`. The state
machine raises `IllegalTransitionError` if you try otherwise.

### Transition triggers

| Trigger                                    | Layer affected         | New state         |
|--------------------------------------------|------------------------|-------------------|
| Outline draft generated                    | outline_status         | pending_review    |
| User approves outline                      | outline_status         | locked            |
| Slide prompt drafted                       | intent_status          | pending_review    |
| User approves intent                       | intent_status          | locked            |
| Lint reports `fail` for the page           | matching layer         | needs_rework      |
| `regenerate_single_slide.py`               | intent_status (if not draft) | pending_review |
| `lock_pages.py --layer intent`             | intent_status          | locked            |
| `reset_pages.py --layer intent`            | intent_status          | needs_rework      |

Persistence: status fields live on the slide entries inside `outline.json`
and `slide_prompts.json`. The PageStateMachine class mutates dicts in
place; `persist_machine` writes them back.

## Image lifecycle (per placeholder)

Each `image_placeholder` carries one `status`:

```
         ┌─────────┐
         │ pending │
         └────┬────┘
              │ first generate scan
              ▼
         ┌─────────────┐    user opts out at gate 6
         │ placeholder │ ──────────────────────┐
         └────┬─────┬──┘                       │
              │     │ user requests real img   ▼
              │     │                       ┌─────────┐
              │     ▼                       │ skipped │
              │  ┌───────────────┐          └─────────┘
              │  │ regenerating  │
              │  └────┬─────┬────┘
              │       │     │
       success │      │     │ failure
              ▼       ▼     ▼
         ┌───────────┐  ┌─────────────────────────┐
         │ generated │  │ placeholder + fallback  │
         └─────┬─────┘  └──────────┬──────────────┘
               │ user dislikes      │ retry
               ▼                    │
         (back to regenerating) ◀───┘
```

### Renderer behavior

- `placeholder` — draws a styled placeholder frame (no model call).
- `generated` — embeds `generated_path` via PptxGenJS `addImage`.
- `skipped` — region is dropped from layout; content reflows.
- `pending` — orchestrator should not reach renderer with this status.
- `regenerating` — rendered as `placeholder` until the next generation pass.

`generate_image_assets.py --respect-status` only acts on `pending` and
`regenerating`; explicit `--ids` overrides the filter.

The PageStateMachine's `aggregate_image_status(page_no)` rolls per-placeholder
states up to one of `{no_image, placeholder_only, partially_generated,
fully_generated, has_failures}` for dashboard display.

## Audit trail

Every state transition appends an entry to `placeholder["history"]` (image
layer) or `PageStateMachine.history` (page layers) carrying
`(ts, from, to, reason?)`. Auto-fix fixes append to `lint_report.fixes_applied`.
