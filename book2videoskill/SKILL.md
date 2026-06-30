---
name: book2videoskill
description: Book-to-short-video production workflow for turning a book title, book summary, or Book2Skill output into a 5-minute-or-less knowledge-video package. Use when the user asks to create Book2VideoSkill outputs, book-to-video storyboards, Xiaohongshu book knowledge posters/covers, narration scripts, scene asset plans, TTS/BGM/render plans, Remotion/Hyperframe-ready project data, or a reusable pipeline for “一本书，一个 AI Skill”.
---

# Book2VideoSkill

Use this skill to turn a book or book-methodology breakdown into a portable short-video project: `BookResearch -> BookCore -> CoverPosterPlan -> Storyboard -> ImagegenShots -> Assets -> ExtractedSkill -> RemotionProject -> Video/Poster`.

## Operating Rules

- Build one video around one core methodological claim. Do not summarize the whole book.
- Research the book, author, publisher/context, cover/reading scene references, and visual metaphors before writing scene prompts.
- Treat the main skill as an orchestrator. Keep the three tools independent:
  - `Book2StoryboardTool`: content, BookCore, cover plan, storyboard, narration, publish draft.
  - `Storyboard2AssetsTool`: image/TTS/BGM/subtitle asset plan and provider handoff.
  - `Assets2VideoTool`: render plan, report, bundle, and final render handoff.
- Default to Xiaohongshu vertical video: `9:16`, <= `300` seconds, `6-8` scenes, cover poster `4:5`.
- Default visual preset is `orange_primary_green_secondary`: orange primary, green secondary, warm white background, business infographic / knowledge-poster style.
- Generate Chinese text with renderable components whenever possible. Do not rely on image models to render long Chinese text.
- For 《金字塔原理》 / `Pyramid Principle`, include `结论先行`, `以上统下`, `归类分组`, `逻辑递进`, a pyramid structure model, and the AI Skill candidate `AI汇报结构生成器`.
- For 《原则》 / `Principles`, include `极度求真`, `极度透明`, `创意择优`, `痛苦 + 反思 = 进步`, `可信度加权决策`, a feedback-loop visual model, and the AI Skill candidate `AI原则复盘教练`.
- Use a durable per-book project directory. The default is `book2videoskill/projects/<book-slug>/`; do not write book projects under `/tmp`.
- Use the built-in `imagegen` plugin as the default image provider for final poster and scene visuals. Keep component-rendered PNGs only as deterministic fallbacks.
- Use OpenRouter TTS by default through `OPENROUTER_API_KEY` from the shell or Hermes system config. If OpenRouter is not configured, create an explicit provider note and use macOS `say` only as a local fallback.
- Scene design must be visual-first: use book/author context, book-object shots, workplace scenes, diagrams, and metaphorical illustrations. Avoid videos made only of text cards.
- Use online book/author/cover research as visual anchors for prompts, but keep generated scenes original: do not copy copyrighted book covers, logos, or recognizable author portraits into the output.
- Use text/research models for the content logic, narration, and shot list. Use imagegen for poster/static visual anchors. Use OpenRouter video models for final per-scene video clips by default, then fall back to local Remotion/ffmpeg rendering when OpenRouter video fails or times out.
- Scene frames must include readable visible subtitles and no debug/footer filler at the bottom of each page.
- Render timing must follow real TTS duration when audio exists. Use `render_timing.json` to avoid long silent holds between scenes.
- Mark generated media honestly. The local component renderer can produce fallback poster/scene PNGs and an MP4; use the generated Remotion project when a Remotion runtime/plugin render is available.
- Preserve intermediate artifacts and error reports when any provider or renderer fails.

## Quick Start

Create a complete scaffolded project:

```bash
python3 book2videoskill/scripts/run_book2video.py --book "金字塔原理" --author "芭芭拉·明托" --output-root output
```

By default, omit `--output-root` to create `book2videoskill/projects/<book-slug>/`:

```bash
python3 book2videoskill/scripts/run_book2video.py --book "原则" --author "瑞·达利欧"
```

Validate the project:

```bash
python3 book2videoskill/scripts/validate_book2video_project.py book2videoskill/projects/principles-ray-dalio --require-render
```

Run tools independently when debugging:

```bash
python3 book2videoskill/scripts/book2storyboard.py --book "金字塔原理" --output-dir output/pyramid-principle
python3 book2videoskill/scripts/storyboard2assets.py --project-dir output/pyramid-principle
python3 book2videoskill/scripts/create_extracted_skill.py --project-dir output/pyramid-principle
python3 book2videoskill/scripts/assets2video.py --project-dir output/pyramid-principle
```

## Workflow

1. Read `references/schemas-and-rules.md` when defining or checking `BookCore`, `StyleBible`, `CoverPosterPlan`, `Storyboard`, `AssetManifest`, or `RenderPlan`.
2. Read `references/workflow.md` when deciding stage gates, quality checks, error handling, or how to handle `storyboard-only` / `cover-only`.
3. Read `references/providers-and-rendering.md` before connecting real ImageGen, TTS, music, Remotion, or Hyperframe providers.
4. Use scripts for repeatable scaffold and validation. Patch scripts only when the workflow contract changes.
5. After generation, verify:
   - `book_research.json`, `book_core.json`, `cover_poster_plan.json`, `style_bible.json`, `storyboard.json`, and `narration_script.md` exist.
   - Storyboard has `6-8` scenes and total duration <= duration limit.
   - Asset manifest paths exist, even if they are explicit placeholder handoff files.
   - `imagegen_prompts.json` exists and declares poster plus per-scene project-bound image prompts under `imagegen_sources/`.
   - `poster.png`, `output/poster.png`, `output/final_video.mp4`, `output/narration.m4a`, `render_timing.json`, `tts_manifest.json`, `subtitles/all.ass`, and `remotion/src/Root.tsx` exist.
   - If `render_plan.providerStatus == "openrouter-video"`, `openrouter_video_manifest.json` exists and references one generated clip per scene.
   - `output/final_video.mp4` has an audio stream and the visual frames include readable subtitles.
   - `extracted_skill/<skill-name>/SKILL.md` and `<skill-name>.zip` exist.
   - `project_bundle.zip` does not exist.
   - Publish draft exists and does not contain unsupported claims.

## Output Contract

The default project directory should contain:

```text
video_brief.md
book_research.json
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
imagegen_prompts.json
imagegen_sources/
scene_images/
tts_audio/
subtitles/
bgm/
tts_manifest.json
render_timing.json
openrouter_video_manifest.json
output/
remotion/
extracted_skill/
<extracted-skill-name>.zip
```

Local generation produces `book_research.json`, `imagegen_prompts.json`, `poster.png`, `scene_images/*.png` with visible subtitles, `tts_manifest.json`, `render_timing.json`, `output/narration.m4a`, `subtitles/all.ass`, `output/final_video.mp4`, a Remotion project, and a portable extracted-skill zip. Use imagegen-selected images as project-bound static references by copying them into `imagegen_sources/` and rerunning assets/render. OpenRouter video clips are preferred for final scene motion and are recorded in `openrouter_video_manifest.json`; when they are unavailable, Remotion/local ffmpeg reads the storyboard and plays the composited scene frames in order. Real providers may additionally add BGM or a Remotion-rendered replacement MP4.
