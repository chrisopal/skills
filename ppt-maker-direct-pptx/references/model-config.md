# Model Config

Use separate logical roles only where they materially help. The first version keeps this skill simple:

## Recommended Roles

- `text_model`
  Confirm and normalize incomplete user input, recommend templates, generate outline, master style, and structured page intents.

## Recommended Defaults

- `text_model`
  strong text model with reliable structured JSON output

## Suggested Config Fields

Use or adapt the bundled config:

- `text_model`
- `aspect_ratio`
- `resolution`
- `default_output_mode`
- `language`
- `font_preferences`

Keep the config external so the same workflow can run against different providers.
The direct rendering layer is deterministic Python rendering, not image generation.
