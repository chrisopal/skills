---
name: book2videoskill
description: Book-to-short-video production workflow for turning a book title, book summary, or Book2Skill output into a 5-minute-or-less knowledge-video package. Use when the user asks to create Book2VideoSkill outputs, book-to-video storyboards, Xiaohongshu book knowledge posters/covers, narration scripts, scene asset plans, TTS/BGM/render plans, Remotion/Hyperframe-ready project data, or a reusable pipeline for “一本书，一个 AI Skill”.
---

# Book2VideoSkill

Use this skill to turn a book or book-methodology breakdown into a short-video production package: `BookCore -> CoverPosterPlan -> Storyboard -> Assets -> RenderPlan -> Publish Draft`.

## Operating Rules

- Build one video around one core methodological claim. Do not summarize the whole book.
- Treat the main skill as an orchestrator. Keep the three tools independent:
  - `Book2StoryboardTool`: content, BookCore, cover plan, storyboard, narration, publish draft.
  - `Storyboard2AssetsTool`: image/TTS/BGM/subtitle asset plan and provider handoff.
  - `Assets2VideoTool`: render plan, report, bundle, and final render handoff.
- Default to Xiaohongshu vertical video: `9:16`, <= `300` seconds, `6-8` scenes, cover poster `4:5`.
- Default visual preset is `orange_primary_green_secondary`: orange primary, green secondary, warm white background, business infographic / knowledge-poster style.
- Generate Chinese text with renderable components whenever possible. Do not rely on image models to render long Chinese text.
- For 《金字塔原理》 / `Pyramid Principle`, include `结论先行`, `以上统下`, `归类分组`, `逻辑递进`, a pyramid structure model, and the AI Skill candidate `AI汇报结构生成器`.
- Mark generated media placeholders honestly. Do not claim real TTS, BGM, PNG, or MP4 exists unless a provider/render command actually produced it.
- Preserve intermediate artifacts and error reports when any provider or renderer fails.

## Quick Start

Create a complete scaffolded project:

```bash
python3 book2videoskill/scripts/run_book2video.py --book "金字塔原理" --author "芭芭拉·明托" --output-root output
```

Validate the project:

```bash
python3 book2videoskill/scripts/validate_book2video_project.py output/pyramid-principle
```

Run tools independently when debugging:

```bash
python3 book2videoskill/scripts/book2storyboard.py --book "金字塔原理" --output-dir output/pyramid-principle
python3 book2videoskill/scripts/storyboard2assets.py --project-dir output/pyramid-principle
python3 book2videoskill/scripts/assets2video.py --project-dir output/pyramid-principle
```

## Workflow

1. Read `references/schemas-and-rules.md` when defining or checking `BookCore`, `StyleBible`, `CoverPosterPlan`, `Storyboard`, `AssetManifest`, or `RenderPlan`.
2. Read `references/workflow.md` when deciding stage gates, quality checks, error handling, or how to handle `storyboard-only` / `cover-only`.
3. Read `references/providers-and-rendering.md` before connecting real ImageGen, TTS, music, Remotion, or Hyperframe providers.
4. Use scripts for repeatable scaffold and validation. Patch scripts only when the workflow contract changes.
5. After generation, verify:
   - `book_core.json`, `cover_poster_plan.json`, `style_bible.json`, `storyboard.json`, and `narration_script.md` exist.
   - Storyboard has `6-8` scenes and total duration <= duration limit.
   - Asset manifest paths exist, even if they are explicit placeholder handoff files.
   - Render plan is consumable by a renderer.
   - Publish draft exists and does not contain unsupported claims.

## Output Contract

The default project directory should contain:

```text
video_brief.md
book_core.json
style_bible.json
cover_poster_plan.json
storyboard.json
narration_script.md
xiaohongshu_publish.md
asset_manifest.json
render_plan.json
assets_ready_report.md
render_report.md
scene_images/
tts_audio/
subtitles/
bgm/
output/
project_bundle.zip
```

Real provider outputs may additionally include `cover.png`, `mascot.png`, `scene_images/*.png`, `tts_audio/*.mp3`, `bgm/main.mp3`, and `output/final_video.mp4`. The scaffold scripts use SVG/text placeholders unless a real provider is wired in.
