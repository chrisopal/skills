# Model Config

Use separate logical roles only where they materially help. The first version keeps this skill simple:

## Recommended Roles

- `text_model`
  Confirm and normalize incomplete user input, recommend templates, generate outline, master style, and structured page intents.
- `pptx_js_model`
  Generate and repair page-level PptxGenJS modules. Defaults to `text_model` when omitted.
- `image_model`
  Optional image model used by `generate_image_assets.py` for slide image placeholders.

## Recommended Defaults

- `text_model`
  strong text model with reliable structured JSON output
- `pptx_js_model`
  strong code-capable model that can follow PptxGenJS constraints
- `image_model`
  image-capable model that can return a data URI or image URL

## Suggested Config Fields

Use or adapt the bundled config:

- `text_model`
- `pptx_js_model`
- `image_model`
- `aspect_ratio`
- `resolution`
- `default_output_mode`
- `language`
- `font_preferences`

Keep the config external so the same workflow can run against different providers.
The direct rendering layer generates page-level PptxGenJS modules, not images.
