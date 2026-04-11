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

Return JSON only:
- summary
- missing_fields
- recommended_follow_up_questions
```

## Template Recommendation Prompt

Use this pattern when requirement fields are complete but no concrete template has been confirmed:

```text
You are a presentation template recommender.
Choose the best template for the following requirement.

Requirement:
{requirement_json}

Available templates:
{templates_json}

Return JSON only:
- recommended_template_id
- recommended_template_name
- reason

Constraints:
- choose exactly one template
- prioritize consistency with purpose, audience, and stated style
- if the style clearly matches one template, choose that exact template
```

## Outline Generation Prompt

Use this pattern for outline generation:

```text
You are a senior presentation strategist.
Based on the confirmed requirement below, generate a complete PPT deck outline.

Requirement:
{requirement_json}

Return JSON only:
- storyline
- deck_structure
- slides

Each slide must contain:
- page_no
- title
- subtitle
- purpose
- layout_type
- key_blocks

Constraints:
- keep the narrative coherent
- match the audience and scenario
- avoid redundant slides
- keep language concise and presentation-ready
- make each page role clear and non-overlapping
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

Return JSON only with:
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
You are a presentation page-intent designer.
Given the confirmed requirement, the deck-level style brief, and the approved outline, generate structured page intents for every slide in one batch.

Requirement:
{requirement_json}

Master style:
{master_style_json}

Outline:
{outline_json}

Return JSON only:
- slides

Each slide item must contain:
- page_no
- title
- subtitle
- page_goal
- layout_type
- key_blocks
- visual_focus
- detail_notes

Constraints:
- maintain a consistent visual system across all slides
- preserve a coherent deck narrative
- keep structure suitable for later deterministic prompt compilation
- avoid vague filler descriptions
- write visible page content and invisible guidance separately in intent fields
```

## Image Rendering Wrapper Prompt

Use this pattern when sending a compiled prompt to an image model:

```text
You are a professional slide designer. Generate a complete presentation slide as an image.
The output must be a 16:9 slide image at {resolution}.
Render the full slide itself, including all intended text and visual elements.
Do not generate a background only.
Do not add page numbers, watermarks, corner labels, template names, 16:9 text, audience labels, or extra decorative microcopy unless explicitly requested.

Slide specification:
{image_prompt}
```

## Single Slide Prompt Regeneration Prompt

Use this pattern only when a future flow needs the model to rewrite page-intent fields. The default v1 implementation recompiles deterministically instead of relying on this prompt.

```text
You are a presentation page-intent editor.
Refine the current slide intent while preserving deck-level consistency.

Requirement:
{requirement_json}

Master style:
{master_style_json}

Whole outline:
{outline_json}

Current slide:
{slide_json}

Existing slide prompt:
{existing_prompt_json}

Additional instruction:
{regeneration_instruction}

Return JSON only with:
- page_no
- title
- subtitle
- page_goal
- layout_type
- key_blocks
- visual_focus
- detail_notes
```
