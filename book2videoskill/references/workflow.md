# Workflow

## Stage 1: Book2StoryboardTool

Input may be a book title, book summary, Book2Skill output, or manually specified topic.

Produce:

- `video_brief.md`
- `book_research.json`
- `book_core.json`
- `style_bible.json`
- `cover_poster_plan.json`
- `storyboard.json`
- `narration_script.md`
- `xiaohongshu_publish.md`

Quality gate:

- BookCore is present before storyboard.
- BookResearch is present before imagegen shot design.
- BookResearch includes author/book/cover visual anchors from online or provided sources before imagegen shot design.
- One core question drives the video.
- Storyboard has `6-8` scenes.
- Every scene has `visualRole` and `recommendedVisualMode`.
- Total duration <= duration limit.
- Style preset is orange-primary / green-secondary unless the user explicitly overrides it.
- No long book excerpts or unsupported author claims.

## Stage 2: Storyboard2VisualPlanTool

Input:

- `storyboard.json`
- `style_bible.json`
- `cover_poster_plan.json`

Produce:

- `visual_plan.json`
- `visual_plan.md`
- `reports/visual_plan_report.md`

Quality gate:

- `visualStrategy.overallMode` is `hybrid_ai_video_motion_graphics`.
- All scenes use `rendererTextOverlay`.
- Image-to-video is reserved for hook/problem/book/AI workflow/use-case/summary scenes.
- Motion Graphics is used for core models, SOP, AI pipelines, and structure-heavy scenes.
- Negative prompts forbid baked Chinese text, watermarks, logos, and over-dramatic camera motion.

## Stage 3: StyleFrameGeneratorTool

Input:

- `style_bible.json`
- `visual_plan.json`
- `cover_poster_plan.json`

Produce:

- `asset_manifest.json`
- `imagegen_prompts.json`
- `imagegen_sources/` directory for selected imagegen outputs
- `style_frames_manifest.json`
- `style_frames/*.png`
- `poster.png`
- `scene_images/*.png`
- Cover asset or cover handoff
- Mascot asset or mascot handoff
- Scene images or image handoff files
- TTS audio or TTS handoff files
- BGM or music handoff file
- Visible subtitles composited into scene frames plus SRT/ASS sidecar subtitles
- `assets_ready_report.md`
- `reports/style_frame_report.md`

Fallback policy:

- Try configured image provider priority first.
- Default image provider is built-in `imagegen`; copy selected imagegen outputs back into the book project paths.
- Imagegen prompt targets must live under `imagegen_sources/`; rerun asset composition after copying selected generated images there.
- If image generation fails or is unavailable, produce component/SVG/PNG card fallback and record the warning.
- TTS defaults to OpenRouter through `OPENROUTER_API_KEY` from the environment or Hermes system config. If OpenRouter is missing or logged out, record the provider note and use the configured local fallback only for development renders.
- If TTS fails and no fallback is available, preserve narration text and mark audio missing or placeholder.
- If BGM fails, render without BGM or use a local default; do not fail the whole project.

## Stage 4: Image2VideoTool

Input:

- `style_bible.json`
- `visual_plan.json`
- `style_frames_manifest.json`
- `render_timing.json`

Produce:

- `openrouter_video_manifest.json` when attempted
- `video_clips/openrouter/*.mp4` when provider succeeds
- `dynamic_video_manifest.json`
- `reports/image2video_report.md`

Default provider is OpenRouter video. If OpenRouter video fails, partially completes, times out, or runs out of credits, record the failure and let FinalAssembler use local fallback for missing scenes.

## Stage 5: MotionGraphicsTool

Input:

- `style_bible.json`
- `storyboard.json`
- `visual_plan.json`
- `style_frames_manifest.json`

Produce:

- `motion_graphics_manifest.json`
- `motion_graphics/*.svg`
- `reports/motion_report.md`

SVG Motion is the default fallback provider. Use staggered element timing, draw-line style for connectors, card/icon scale/fade/slide entry, and avoid motion that competes with narration.

## Stage 6: FinalAssemblerTool

Input:

- `style_bible.json`
- `storyboard.json`
- `visual_plan.json`
- `asset_manifest.json`
- `dynamic_video_manifest.json`
- `motion_graphics_manifest.json`
- `render_plan.json`

Produce:

- `render_plan.json`
- `render_report.md`
- `output/final_video.mp4`
- `output/narration.m4a`
- `output/poster.png`
- `render_timing.json`
- `dynamic_video_manifest.json`
- `assembly_timeline.json`
- `openrouter_video_manifest.json` when OpenRouter video succeeds or is attempted
- `subtitles/all.ass`
- `remotion/` project with `src/Root.tsx` and static assets

Default render provider is OpenRouter video. Hyperframe is an adapter target; do not claim implementation unless it exists.
The fallback MP4 must mux narration audio when TTS assets exist. It should derive scene durations from real TTS length through `render_timing.json`, so source storyboard durations do not create long silent holds. OpenRouter video should generate one short clip per scene and record results in `openrouter_video_manifest.json`. If any OpenRouter clip is missing, failed, or timed out, fall back to local Remotion/ffmpeg motion-segment rendering for the missing scenes. Chinese titles and subtitles must be applied as local overlays on top of OpenRouter clips. Because not all local ffmpeg builds include subtitle filters, scene PNGs must already contain readable subtitles; ASS/SRT files remain sidecars for Remotion or later editing.

## Stage 7: Extracted Skill

Input:

- `book_core.json`

Produce:

- `extracted_skill/<skill-name>/SKILL.md`
- `extracted_skill/<skill-name>/agents/openai.yaml`
- `extracted_skill/<skill-name>/references/book_core.json`
- `<skill-name>.zip`

The extracted skill must be portable: the zip should contain the skill folder and enough references/assets to install or move it without the source project.

## Modes

- Full scaffold: run storyboard, assets, extracted-skill packaging, and render.
- Hybrid: default v1.2 six-tool flow with VisualPlan, StyleFrames, Image-to-Video, Motion Graphics, and FinalAssembler outputs.
- Legacy: v1.1-compatible three-tool flow for narrow debugging.
- Storyboard-only: stop after Stage 1.
- Visual-plan-only: stop after Stage 2.
- Style-frames-only: stop after Stage 3.
- Image2video-only: stop after Stage 4.
- Motion-only: stop after Stage 5.
- Assemble-only: rerun FinalAssemblerTool for an existing project.
- Cover-only: generate BookCore, CoverPosterPlan, and cover handoff/component output.
- Render: try OpenRouter video clips first, create a Remotion project, and produce a local MP4. If OpenRouter video fails, use the local Remotion/ffmpeg fallback and disclose the provider status.
- Imagegen refresh: after adding or replacing files under `imagegen_sources/`, rerun `storyboard2assets.py` and `assets2video.py`.
- OpenRouter video assembly: `openrouter_video.py` should read `storyboard.json` plus `render_timing.json`, create one 9:16 clip per scene, and store clips in `video_clips/openrouter/`.
- Remotion fallback assembly: Remotion should read `storyboard.json` for scene order/duration and render `scene_images/<sceneId>.png` frames generated from imagegen sources plus the deterministic text overlay.
- TTS refresh: rerun `openrouter_tts.py --project-dir <book-project>` after configuring `OPENROUTER_API_KEY` or Hermes OpenRouter auth, then rerun `assets2video.py`.
- Timing refresh: rerun `assets2video.py` after any TTS update so `render_timing.json`, subtitles, Remotion props, and final MP4 duration stay aligned.

## Validation

Run `validate_book2video_project.py` before claiming completion.

Use `--require-render` only when the task requires actual MP4/PNG/audio media rather than scaffold outputs.

For 《金字塔原理》, additionally check the four core principles, pyramid model, AI汇报结构生成器, orange/green palette, and the series label `一本书，一个AI Skill`.

For 《原则》, additionally check book research, the five core concepts, feedback-loop model, AI原则复盘教练, orange/green palette, visual-first imagegen/video prompts grounded in book/author/cover research, poster PNG, final MP4 with audio stream, visible subtitles, `render_timing.json`, OpenRouter video manifest when successful, Remotion fallback project, extracted-skill zip, and absence of `project_bundle.zip`.
