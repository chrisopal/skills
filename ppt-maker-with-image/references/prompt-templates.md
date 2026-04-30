# Prompt Templates

## Requirement Confirmation Prompt

Use this pattern to confirm missing inputs:

```text
You are a presentation requirements analyst.
Extract and confirm the following fields from the user's request:
- topic
- target audience
- purpose / scenario
- preferred style
- page count
- key points
- must-have sections
- hard constraints

Return:
1. a concise summary of what is already clear
2. only the missing questions required to continue
```

## Outline Generation Prompt

Use this pattern for outline generation:

```text
You are a senior presentation strategist.
Based on the confirmed requirement below, generate a complete PPT deck outline.

Requirement:
{requirement_json}

Return:
- storyline summary
- deck structure
- exactly {page_count} slides
- for each slide: page_no, title, subtitle, purpose, layout_type, key_blocks

Constraints:
- keep the narrative coherent
- match the audience and scenario
- avoid redundant slides
- keep language concise and presentation-ready
```

## Master Style Brief Generation Prompt

Use this pattern after the requirement is confirmed and before per-slide prompt generation:

```text
You are a senior presentation design director.
Generate a structured deck-level master style brief for this presentation.

Requirement:
{requirement_json}

Template preset:
{template_preset_json}

Return a JSON object containing:
- visual_positioning
- deck_voice
- color_strategy
- typography
- title_hierarchy_rules
- layout_system
- module_layout_patterns
- chart_rules
- icon_rules
- forbidden_elements
- prompt_block

Constraints:
- keep the output practical and reusable across the whole deck
- define title hierarchy, module layout rules, chart style, and forbidden elements explicitly
- align to the named template preset if one exists
```

## Per-Slide Prompt Generation Prompt

Use this pattern after the outline is confirmed:

```text
You are a presentation visual prompt designer.
Given the confirmed requirement, the deck-level style brief, and the approved outline, generate image prompts for every slide in one batch.

Requirement:
{requirement_json}

Master style:
{master_style_json}

Page intent:
{page_intent_json}

Outline:
{outline_json}

Style header:
{style_header}

Return for each slide:
- page_no
- title
- slide_role
- key_blocks
- image_prompt

Constraints:
- maintain a consistent visual system across all slides
- keep prompts specific to layout, hierarchy, and modules
- avoid random page furniture and microcopy
- optimize for full-slide image rendering
- image_prompt must contain page-specific visible content and layout intent only; do not restate font-size ranges, spacing values, margin values, radius values, stroke values, shadow values, or caption-size labels.
```

## Image Rendering Wrapper Prompt

Use this pattern when sending a prompt to an image model:

```text
You are a professional slide designer. Generate a complete presentation slide as an image.
The output must be a 16:9 slide image at {resolution}.
Render the full slide itself, including all intended text and visual elements.
Do not generate a background only.
Do not add page numbers, watermarks, corner labels, or extra decorative microcopy unless explicitly requested.
Visible slide copy must only include presentation content.
Treat all style measurements, font sizes, spacing values, radius values, stroke values, and shadow values as invisible design instructions.
Never render measurement labels or design annotations such as "40-56px", "20-28px", "56-72px", "Caption: 12-14px", "R=14px", "stroke=1pt", red boxes, rulers, alignment guides, wireframes, or prompt/schema text.

Slide specification:
{image_prompt}
```

## Single Slide Prompt Regeneration Prompt

Use this pattern when regenerating one slide after manual edits or review feedback:

```text
You are a presentation visual prompt designer.
Regenerate the image prompt for a single slide while preserving deck-level consistency.

Requirement:
{requirement_json}

Master style:
{master_style_json}

Page intent:
{page_intent_json}

Whole outline:
{outline_json}

Style header:
{style_header}

Current slide:
{slide_json}

Existing slide prompt:
{existing_prompt_json}

Additional instruction:
{regeneration_instruction}

Return a JSON object containing:
- page_no
- title
- slide_role
- key_blocks
- image_prompt

Constraints:
- preserve the same deck-level style and template rules
- treat `style_header` as the only deck-level style source when it is provided
- only adjust what is necessary for this slide
- keep the slide aligned with the deck narrative
- avoid extra corner labels, decorative microcopy, and random page furniture
- image_prompt must contain page-specific visible content and layout intent only; do not restate font-size ranges, spacing values, margin values, radius values, stroke values, shadow values, or caption-size labels.
- treat all style measurements, font sizes, spacing values, radius values, stroke values, and shadow values as invisible design instructions rather than visible slide copy.
```
