# Model Config

Use separate logical roles even if the implementation ultimately uses one provider.

## Recommended Roles

- `requirement_model`
  Confirm and normalize incomplete user input.
- `outline_model`
  Generate the full deck outline.
- `prompt_model`
  Generate all per-slide prompts in one pass.
- `image_model`
  Render full-slide images.

## Recommended Defaults

- requirement / outline / prompt:
  strong text model with reliable structured output
- image:
  slide-capable image model that supports crisp text and large layouts

## Suggested Config Fields

Use or adapt the bundled config:

- `text_model`
- `image_model`
- `aspect_ratio`
- `resolution`
- `default_output_mode`
- `language`
- `font_preferences`

Keep the config external so the same workflow can run against different providers.
