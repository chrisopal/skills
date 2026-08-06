# ppt-hybrid-studio Design Specification (Approved)

Date: 2026-08-06
Method: `superpowers:brainstorming`
Status: approved, ready for implementation planning
Skill name: `ppt-hybrid-studio`

## 1. Purpose

`ppt-hybrid-studio` is a standalone, portable skill for producing visually rich but practically editable PowerPoint decks from mixed source materials.

It combines two complementary techniques:

- Image generation creates visual-only backgrounds, scenes, decorative frames, icons, and non-semantic illustrations.
- A deterministic PowerPoint composer adds editable text and, where required, editable diagrams, charts, tables, nodes, and connectors.

The skill must not treat every slide as a flattened image. Data-heavy slides, technical architecture slides, and highly editable process diagrams must preserve more of their structure as native PowerPoint objects.

## 2. Confirmed Product Decisions

The brainstorming session confirmed the following decisions:

1. Build a standalone skill rather than a runtime wrapper around `ppt-master`.
2. Reuse and adapt the useful source-normalization behavior from `ppt-master`, but include the required implementation in this skill so it has no runtime dependency on `ppt-master`.
3. Require user approval for the storyline and deck outline.
4. Require user approval for per-slide content, layout, and render mode.
5. Generate one or two representative visual anchor slides before batch generation.
6. Provide a local browser review workspace with structured editing, approval, annotations, and single-slide regeneration.
7. Do not attempt to build a full drag-and-drop PowerPoint editor in the browser.
8. Recommend a render mode automatically for each slide, while allowing the user to override it during slide-plan review.
9. Default to the image-generation capability available in the current agent environment, normally Imagegen, while retaining adapters for other image-generation skills or providers.
10. Default to PptxGenJS for PowerPoint composition.
11. Keep the PowerPoint composition engine pluggable behind a stable adapter contract.
12. Preserve original source files, normalized per-source Markdown, source locators, a consolidated source bundle, and an evidence index.

## 3. Design Principles

### 3.1 Editable truth, generated decoration

Information that must remain exact or editable belongs in native PowerPoint objects. Generated images may express style, atmosphere, metaphor, or non-semantic decoration, but must not encode critical wording, numbers, topology, or directional logic.

### 3.2 Confirmation before expensive generation

The skill confirms the storyline first, then the page plan, then one or two visual anchors. Batch image generation starts only after these gates are approved.

### 3.3 File-based, resumable workflow

Every stage writes explicit Markdown, JSON, image, preview, or presentation artifacts. A failed run can resume from the last valid stage without repeating source extraction or approved planning work.

### 3.4 Visible mode changes

The system must not silently change a slide from a native or hybrid representation into a flattened image. Any render-mode, provider, or significant layout change creates a new version and returns the slide to review.

### 3.5 Portable orchestration

Codex, WorkBuddy, Claude Code, or another capable agent may execute the skill. Environment-specific image generation is isolated behind an adapter, while project artifacts and slide contracts remain consistent.

## 4. Approaches Considered

### 4.1 Selected: standalone orchestrator with shared contracts

The selected approach is an independent skill containing source normalization, storyline planning, page planning, browser review, render routing, image generation adapters, and PowerPoint composer adapters.

This has the highest initial design cost, but it creates stable boundaries and avoids hidden runtime dependencies.

### 4.2 Rejected: extend `ppt-maker-direct-pptx` directly

This would provide a faster initial implementation, but would couple source ingestion, human approval, image generation, browser review, and presentation rendering inside an already substantial native-PPT skill.

### 4.3 Rejected: thin wrapper around existing PPT skills

This would minimize new code, but would depend on several installed skills with different intermediate formats and failure semantics. It would not satisfy the confirmed standalone and portable requirement.

## 5. End-to-End Workflow

```text
Mixed source files
    -> source normalization and evidence indexing
    -> storyline and deck outline
    -> user approval gate 1
    -> per-slide content, layout, and render-mode plan
    -> user approval gate 2
    -> generate one or two visual anchor slides
    -> user approval gate 3
    -> batch image/native-object generation
    -> per-slide browser preview and selective regeneration
    -> PowerPoint composition
    -> rendering, inspection, and export
```

The stages are:

1. Intake and requirements
2. Source normalization
3. Storyline and outline
4. Per-slide plan
5. Visual anchors
6. Batch generation and browser review
7. Composition, quality assurance, and export

## 6. Source Normalization

The skill accepts text plus common office and media formats, including:

- PDF
- Word
- Excel
- PowerPoint
- Markdown and plain text
- Images

The source-to-Markdown behavior is adapted from the proven converters and conventions in `ppt-master`. The minimum required converter set covers PDF, Word, Excel, PowerPoint, web/text, and image references. Reused implementation must retain applicable attribution and licensing notices.

Each normalized Markdown file records:

- `source_id`
- original file name and media type
- extraction status
- PDF page number
- Word heading and paragraph locator
- Excel sheet name and cell range
- PowerPoint slide number
- extracted image/table/chart references
- warnings or unsupported content

Original files are never replaced by normalized outputs.

The normalization stage produces:

- one Markdown file per source
- extracted source assets
- `source_bundle.md`, a consolidated reading bundle
- `evidence_index.json`, mapping claims and data to source locators

A single-source conversion failure does not stop other sources. The pipeline stops before storyline generation only when no usable material remains.

## 7. Project Artifacts

Each deck run uses a self-contained project directory:

```text
project/
├── sources/
│   ├── original/
│   ├── normalized/
│   └── assets/
├── source_bundle.md
├── evidence_index.json
├── requirements.json
├── storyline.json
├── outline.json
├── slide_intents.json
├── slide_specs.json
├── master_style.json
├── image_manifest.json
├── images/
│   └── backgrounds/
├── previews/
├── reviews/
│   └── annotations.json
├── exports/
└── manifest.json
```

`manifest.json` is the authoritative run ledger. It records stage completion, approvals, current slide versions, selected adapters, errors, and export state.

## 8. Storyline and Outline Contracts

`storyline.json` records:

- target audience
- presentation objective
- desired audience action
- core thesis
- supporting arguments
- narrative progression
- tone and visual posture
- constraints such as language, slide count, and duration

`outline.json` records sections and slides. Each slide entry includes a working title, purpose, core message, evidence references, and relationship to adjacent slides.

The browser workspace permits structured editing, reordering, adding, removing, approving, or returning these items for revision.

## 9. Unified Slide Contract

Every slide is described by one `slide_spec` consumed by all composer implementations.

Required fields include:

```json
{
  "slide_id": "S05",
  "title": "智能工厂落地载体",
  "purpose": "说明业务场景、能力底座与落地价值之间的关系",
  "content_blocks": [],
  "evidence_refs": ["EVID-012", "EVID-018"],
  "layout": {
    "type": "three-layer-architecture",
    "regions": []
  },
  "render_mode": "hybrid_native",
  "editability": "high",
  "image_prompt": {
    "visual_only": true,
    "reserved_regions": []
  },
  "review_status": "awaiting_approval"
}
```

The full schema also records slide dimensions, style tokens, native object specifications, image safe areas, object stacking, speaker notes, source citations, generation version, and validation results.

## 10. Render Modes

### 10.1 `image_background`

Use for covers, vision pages, concept pages, scenario pages, and marketing-style narratives.

The generated image contains only visual structure and decoration. Titles, body copy, page numbers, sources, labels, and critical numbers are native PowerPoint text.

### 10.2 `hybrid_native`

Use when strong visual presentation must coexist with exact, editable structure.

The generated image may contain a background scene or decorative frame. Native PowerPoint objects provide charts, tables, architecture nodes, connectors, labels, metrics, and other semantic content.

### 10.3 `fully_native`

Use for data-dense pages, technical architecture, process diagrams, organization structures, system topology, tables, charts, and content expected to change frequently.

Generated imagery is optional and decorative only. The structure and semantics remain native PowerPoint objects.

## 11. Automatic Render-Mode Routing

The router recommends a mode and writes its reasons into the slide plan. The user can override the recommendation before approval.

Hard routing rules are:

- A table, quantitative chart, or critical numeric comparison requires `hybrid_native` or `fully_native`.
- Exact node counts, connector directions, dependencies, or topology require native objects.
- A request for high editability defaults to `fully_native`.
- Technical architecture and multi-step process diagrams default to `fully_native`.
- Critical wording, numbers, labels, and evidence citations must never be baked into a generated image.

Soft routing rules are:

- Hero, vision, scene, metaphor, and concept slides prefer `image_background`.
- Case-study and product-capability slides may use `image_background` or `hybrid_native` depending on exactness needs.
- Mixed evidence and narrative pages prefer `hybrid_native`.

A post-approval mode change creates a new slide version and requires renewed approval.

## 12. Image Generation Adapter

The image layer uses an `ImageProviderAdapter` contract rather than embedding one vendor API throughout the pipeline.

The runtime agent discovers capabilities in this order:

1. Built-in Imagegen in the current environment
2. Another installed image-generation skill
3. A configured external image provider
4. `generation_blocked`

The agent environment may choose the available implementation, but the adapter must write the same result contract. The image manifest records:

- provider and capability identifier
- prompt and negative constraints
- reference images
- aspect ratio and output dimensions
- generation time
- output path and hash
- slide and version identifiers

After visual anchors are approved, the batch stage must not silently change providers. If the approved provider becomes unavailable, affected pages remain blocked with their prompts and plans intact.

All background prompts explicitly request no title, no body text, no numbers, no labels, no watermark, and no pseudo-text. Reserved text and native-object regions are supplied as composition constraints.

## 13. PowerPoint Composer Adapter

PptxGenJS is the default local composition engine. It is hidden behind a stable interface:

```text
PptComposerAdapter
├── validate(project, slide_specs)
├── compose(project)
├── render_preview(slide_id)
├── inspect(slide_id)
└── export(format)
```

The default project configuration is:

```json
{
  "ppt_engine": "pptxgenjs",
  "image_provider": "auto"
}
```

Alternative engines may be added by implementing the same contract. Upstream source artifacts, browser review, slide specifications, and quality reports must not depend on PptxGenJS-specific data structures.

The PptxGenJS implementation may reuse proven native-object patterns from `ppt-maker-direct-pptx`, including text fitting, geometry, connectors, charts, tables, layout linting, preview rendering, and object inspection.

## 14. Browser Review Workspace

The browser workspace is a local project control surface. It reads and writes the project artifacts directly and does not require a cloud database.

It contains these views:

| View | Purpose |
| --- | --- |
| Sources | Inspect originals, normalized content, extraction warnings, and evidence locators |
| Storyline | Edit and approve objective, thesis, arguments, narrative, and sections |
| Slide Plan | Edit titles, content blocks, evidence, layouts, editability, and render modes |
| Anchor Review | Review one or two representative visual slides before batch generation |
| Slides | Preview, annotate, approve, return, and regenerate individual slides |
| QA & Export | Review blocking issues and export PPTX, PDF, or slide images |

The first version supports structured editing, not arbitrary object dragging, free resizing, or pixel-level WYSIWYG editing.

## 15. Approval Gates and State

The required approval gates are:

1. Storyline and outline approval
2. Per-slide content, layout, and render-mode approval
3. Visual anchor approval

Batch generation cannot start until all three gates are satisfied.

The page state machine is:

```text
draft
  -> awaiting_approval
  -> approved
  -> generating
  -> preview_ready
  -> changes_requested
  -> regenerating
  -> preview_ready
  -> approved
  -> locked
  -> exported
```

The exact transitions allow `changes_requested` to return to `draft` before generation and allow a preview to return directly to `approved` when accepted.

All slides must be `locked` before final export. Blocking QA issues prevent `locked` and `exported` transitions.

## 16. Slide Versioning and Regeneration

Regeneration is versioned and never destroys the previously approved result:

```text
slides/S05/
├── v001/
│   ├── slide_spec.json
│   ├── background.png
│   └── preview.png
├── v002/
│   ├── slide_spec.json
│   ├── background.png
│   └── preview.png
└── current.json
```

The user may regenerate:

- native text only
- background image only
- layout and composition only
- the slide after changing render mode
- the complete slide

Text-only changes recompose the slide without invoking image generation. Render-mode changes return the slide to `awaiting_approval`.

## 17. Error Handling

### 17.1 Source errors

- Record per-source conversion failures and continue processing usable sources.
- Stop before storyline generation when no usable source remains.
- Summarize oversized Excel sheets while retaining sheet and cell locators.
- Preserve unrecognized images as assets and mark them for manual description.

### 17.2 Image-generation errors

- Keep the prompt, slide specification, and manifest entry when no provider is available.
- Reject generated pseudo-text, unexpected labels, or missing reserved regions.
- Retry generation according to a bounded policy.
- After repeated composition failure, recommend a visible switch to `hybrid_native` or `fully_native`; do not switch automatically after approval.

### 17.3 Composition errors

- Text overflow, object overlap, out-of-bounds geometry, missing chart data, or broken connector endpoints block the slide from becoming `locked`.
- Composer failure preserves all upstream artifacts so another engine can resume from the same project.
- Missing or unverifiable data must never be replaced with invented values.

## 18. Quality Assurance

### 18.1 Content and evidence

- Confirm the storyline covers the stated objective.
- Confirm each major conclusion has supporting material or is explicitly marked as an assumption.
- Validate every evidence reference against `evidence_index.json`.
- Detect empty, duplicated, or logically disconnected slides.

### 18.2 Generated backgrounds

- Detect probable pseudo-text with OCR and visual checks.
- Verify safe regions for native text and objects.
- Verify slide ratio, resolution, crop safety, and style consistency with approved anchors.
- Reject backgrounds that visually encode exact process, topology, or data relationships assigned to native objects.

### 18.3 Native PowerPoint objects

- Validate text fitting, font availability, line spacing, contrast, and bounds.
- Validate chart data, table content, connector direction, endpoint attachment, and stacking order.
- Confirm the background is placed beneath native objects.
- Confirm object composition matches the selected render mode.

### 18.4 Final render inspection

- Render every slide to an image.
- Inspect overflow, clipping, overlap, contrast, alignment, and visual balance.
- Produce a contact sheet for deck-level consistency review.
- Display every blocking issue in the browser QA view.
- Export the final deck only when blocking issues are closed.

## 19. Compatibility

The primary compatibility target is Microsoft PowerPoint. WPS Presentation is best-effort compatible. LibreOffice may be used for automated preview rendering and basic validation but is not the pixel-perfect reference renderer.

The default slide ratio is 16:9 and can be overridden in requirements. The standard export is `.pptx`; optional outputs are preview PDF and per-slide PNG images.

Advanced animation, macros, complex SmartArt, embedded video interactions, and vendor-specific PowerPoint features are outside the first-version compatibility target.

## 20. Test Strategy

The implementation plan must include tests for:

- PDF, Word, Excel, PowerPoint, image, Markdown, and text normalization
- source locator preservation and evidence indexing
- storyline, outline, and slide-schema validation
- automatic render-mode routing and user overrides
- approval gates and page-state transitions
- slide version creation and rollback
- image capability discovery and blocked generation
- pseudo-text and reserved-region validation
- PptxGenJS composer output and native object types
- text overflow, object bounds, chart data, and connector validation
- browser workspace artifact reading and writing
- an end-to-end sample deck containing all three render modes

## 21. First-Version Acceptance Criteria

The first version is accepted only when it can:

1. Convert mixed-format source material into a traceable Markdown bundle.
2. Let a user review and modify the storyline in the browser workspace.
3. Let a user review and modify per-slide content, layout, and render mode.
4. Generate and approve one or two visual anchors before batch generation.
5. Use the runtime's Imagegen capability by default to create text-free backgrounds.
6. Keep every title and body text element editable in PowerPoint.
7. Create editable native diagrams, charts, tables, and connectors for appropriate slides.
8. Regenerate a single slide or layer without rebuilding the complete deck.
9. Compose with PptxGenJS by default and allow another composer implementation.
10. Render and inspect every slide before exporting a final PPTX.

## 22. Explicitly Out of Scope

The first version does not include:

- a complete online PowerPoint editor
- free object dragging and pixel-level browser layout editing
- real-time multi-user collaboration
- cloud accounts or permission management
- automatic publishing to online office platforms
- advanced PowerPoint animation editing
- post-processing that attempts to erase text from an already generated image

Text-free backgrounds must be generated correctly at the source rather than repaired after generation.

## 23. Implementation-Planning Boundary

This document approves product behavior, architecture, contracts, workflow gates, quality rules, and first-version scope. It does not approve implementation work by itself.

The next step is user review of this written specification. After that review is approved, the project transitions to `superpowers:writing-plans` to create a concrete implementation plan with file ownership, task ordering, tests, and verification commands.
