# Workflow

## Stage 1: Book2StoryboardTool

Input may be a book title, book summary, Book2Skill output, or manually specified topic.

Produce:

- `video_brief.md`
- `book_core.json`
- `style_bible.json`
- `cover_poster_plan.json`
- `storyboard.json`
- `narration_script.md`
- `xiaohongshu_publish.md`

Quality gate:

- BookCore is present before storyboard.
- One core question drives the video.
- Storyboard has `6-8` scenes.
- Total duration <= duration limit.
- Style preset is orange-primary / green-secondary unless the user explicitly overrides it.
- No long book excerpts or unsupported author claims.

## Stage 2: Storyboard2AssetsTool

Input:

- `style_bible.json`
- `storyboard.json`
- `narration_script.md`
- `cover_poster_plan.json`

Produce:

- `asset_manifest.json`
- Cover asset or cover handoff
- Mascot asset or mascot handoff
- Scene images or image handoff files
- TTS audio or TTS handoff files
- BGM or music handoff file
- Subtitles
- `assets_ready_report.md`

Fallback policy:

- Try configured image provider priority first.
- If image generation fails, produce component/SVG card fallback and record the warning.
- If TTS fails, preserve narration text and mark audio missing or placeholder.
- If BGM fails, render without BGM or use a local default; do not fail the whole project.

## Stage 3: Assets2VideoTool

Input:

- `style_bible.json`
- `storyboard.json`
- `asset_manifest.json`
- `render_plan.json`

Produce:

- `render_plan.json`
- `render_report.md`
- `output/final_video.mp4` when real rendering succeeds
- `output/final_video.mock.txt` when only scaffold rendering is available
- `output/cover.png` when real cover rendering succeeds
- `project_bundle.zip`

Default render provider is Remotion. Hyperframe is an adapter target; do not claim implementation unless it exists.

## Modes

- Full scaffold: run all three scripts and create a project bundle.
- Storyboard-only: stop after Stage 1.
- Cover-only: generate BookCore, CoverPosterPlan, and cover handoff/component output.
- Real render: require provider configuration, run actual render command, and fail clearly if outputs are missing.

## Validation

Run `validate_book2video_project.py` before claiming completion.

Use `--require-render` only when the task requires actual MP4/PNG/audio media rather than scaffold outputs.

For 《金字塔原理》, additionally check the four core principles, pyramid model, AI汇报结构生成器, orange/green palette, and the series label `一本书，一个AI Skill`.
