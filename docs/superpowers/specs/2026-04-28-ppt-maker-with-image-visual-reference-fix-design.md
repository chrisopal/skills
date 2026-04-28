# ppt-maker-with-image Visual Reference Fix Design

Date: 2026-04-28
Status: approved for implementation

## Context

The approved redesign requires deterministic style headers, optional first-slide reference anchoring, and review-mode-controlled render progression. Current implementation is only partial:

- `STYLE_HEADER` exposes spacing and typography tokens such as `40-56px`, `20-28px`, and `caption=12-14px` directly to the image model.
- The rendered slide can treat those design tokens as visible slide copy, creating unwanted size labels and design annotations.
- `ImageRenderRequest` does not carry `seed` or `reference_images`.
- `stage_render` ignores `job.consistency`, so slide 2..N cannot use slide 1 as a reference image.

## Goal

Bring Phase B visual consistency behavior back in line with the approved redesign:

- Keep spacing, sizing, color, and typography rules as invisible rendering constraints.
- Explicitly forbid visible design annotations, including `px`, `pt`, `R=`, margin/spacing labels, caption-size labels, red measurement boxes, and any UI-spec text.
- Add first-slide reference image support as an opt-in consistency mode.
- Preserve safe fallback when a provider does not support reference images.

## Behavior

### Prompt Visibility Rules

`STYLE_HEADER` remains deterministic, but every size and spacing token is framed as an invisible design constraint. The image render wrapper adds a hard negative instruction:

- Do not render font-size numbers.
- Do not render spacing or margin measurements.
- Do not render `Caption: 12-14px`, `40-56px`, `20-28px`, `56-72px`, `R=14px`, `stroke=1pt`, or similar design-spec labels.
- Do not render red boxes, rulers, alignment guides, wireframe annotations, or prompt/schema text.

Per-slide prompt generation should produce page-specific content only. It must not restate font-size, spacing, radius, stroke, shadow, or layout measurement values.

### Reference Image Mode

`job.json` supports:

```json
"consistency": {
  "use_reference_image": false,
  "reference_source": "first_slide",
  "seed": null
}
```

Rules:

- Slide 1 always renders without reference images.
- Slide 2..N use `images/slide_01.png` as `reference_images=[...]` only when `use_reference_image=true`.
- If the provider does not support reference images, the run logs a warning/capability note and continues without the reference.
- Single-slide regeneration should use slide 1 as the reference when available and should not use neighboring slides as references.

### Provider Contract

`ImageRenderRequest` adds:

- `seed: int | None`
- `reference_images: Sequence[bytes] | None`

`ImageProvider` adds capability metadata:

- `supports_reference_images`
- `supports_seed`

Providers that cannot support a feature either ignore seed or raise `UnsupportedFeatureError` for reference images. The render stage catches unsupported reference images once per run and continues.

## Acceptance Criteria

- Generated prompts no longer instruct the image model to draw visible size labels.
- A prompt containing layout/font constraints includes an explicit "invisible constraints only" rule.
- Rendering with `consistency.use_reference_image=false` behaves as before.
- Rendering with `consistency.use_reference_image=true` sends slide 1 bytes to slide 2..N when the provider supports reference images.
- If a provider does not support reference images, image generation still completes and records the fallback.
- Tests cover prompt sanitization/visibility rules and reference-image routing.

## Out of Scope

- Full `review_mode` migration beyond the render-confirmation behavior already designed.
- Vision-model post-render QA.
- Changing named template presets beyond prompt visibility fixes.
