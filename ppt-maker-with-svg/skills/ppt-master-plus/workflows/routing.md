---
description: Huixin Plus routing with low-context ordinary generation and preserved specialist routes.
---

# Routing Rules

Select one lifecycle, then one profile. This file owns route selection over
older route summaries. Do not load unselected runtimes to compare them.

## 1. Lifecycle

| Request | Authority |
|---|---|
| Create a reusable Brand/Style/Layout/Deck workspace | `create-template.md` |
| Fill a raw PPTX's native slide shells with new material | `template-fill-pptx.md` |
| Keep finished slides stable; add notes/audio/timings/transitions | `native-enhance-pptx.md` |
| Create, reconstruct, or visually regenerate slides | Generate profiles below |

Ask one discriminator only if an existing-deck request genuinely leaves fill,
regenerate, and enhance ambiguous. Honor explicit instructions when prerequisites
exist. A missing prerequisite is not permission to silently switch lifecycle.

## 2. Generate Profile (First Matching Row)

| Condition | Runtime |
|---|---|
| Raster page frames must be reconstructed into editable slides | `profiles/image-to-pptx.md`; Codex-supported, owns Quick activation |
| Existing PPTX must retain wording, count and order 1:1 | `profiles/beautify-pptx.md`; its fidelity rules select Default or explicit Quick |
| Resume a split-mode project with an existing spec/lock | `stages/resume-execute.md` |
| Explicit staged confirmation, multiple design alternatives, spec refinement, interactive preview, or reusable native Master/Layout/placeholder output | `generate-pptx.md` |
| Explicit external workspace, non-Huixin styling, free design, or no template | `profiles/quick-generate.md` |
| Ordinary new PPTX, including explicit quick/fast Huixin requests | `profiles/huixin-generate.md` |

Page count and architecture complexity never force full planning. A request
for a rendered preview/contact sheet is not an interactive-editor request.
Recorded/self-running/video delivery without another fidelity profile uses
`profiles/quick-generate.md` and its video/audio stages; explicit full planning
still wins. Never load Default, Quick and Huixin Generate together.

## 3. Template Selection

Bundled theme workspaces contain only six `huixin_*` Decks. Technical chart,
table, icon, schema and scaffold assets are not competing themes and remain
available on demand. Brand/Style/Layout indexes may be empty; never scan their
directories to invent candidates or restore removed presets.

An exact registered Huixin id or alias selects that Deck directly. Otherwise
use the topic table in `profiles/huixin-generate.md`; read only the Deck index
when needed and only the selected spec/prototypes afterwards. No source deck
or logo may override an explicit user brand instruction.

Explicit external workspaces remain supported; normalize and validate their
exact roots using `stages/apply-template-workspace.md`. A bare unregistered
brand name is a style brief, not a guessed local path. Full Default planning
uses its staged candidate/install/confirmation rules; the lightweight profiles
do not inherit those gates.

## 4. Conditional Stages

| Actual need | Supporting authority |
|---|---|
| Missing source facts / topic-only input | `stages/topic-research.md`, only for identified gaps |
| Value-driven chart geometry | `stages/verify-charts.md` before final SVG check |
| Explicit per-page visual rubric | `stages/visual-review.md` |
| Interactive preview/annotations | Full Default plus `stages/live-preview.md` |
| Recorded/video-directed delivery | `references/video-design.md` (relative to Skill root) |
| Per-object animations or existing `animations.json` | `stages/customize-animations.md` |
| Notes-to-audio or narrated MP4 | `stages/generate-audio.md` |

For reusable native structure, create a validated workspace and generate a new
lock-backed structured deck. Never graft inferred masters onto existing PPTX
or silently claim that flat editable export creates reusable native masters.
Create Template's four child kinds retain their existing contracts. Native
fill/enhance workflows never enter the SVG authoring lifecycle.
