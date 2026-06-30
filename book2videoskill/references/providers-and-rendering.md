# Providers And Rendering

## Provider Contracts

Use provider adapters rather than embedding provider logic in the main skill.

Provider priority by layer:

- Image/style frames: `imagegen`, then component/SVG/PNG fallback.
- Image-to-video: OpenRouter video as the current real provider, then local Remotion/ffmpeg fallback. The spec-compatible abstract priority is `runway`, `luma`, `kling`, `veo`, `mock`.
- Motion Graphics: `svg_motion`, `lottie`, `remotion_motion`, `after_effects`.
- Final assembly: `remotion`, `ffmpeg`, `after_effects`.

### ImageProvider

Input:

- `prompt`
- `query`
- `styleBible`
- `aspectRatio`

Output:

- `ok`
- `assetPath`
- `providerName`
- `metadata`

Priority:

1. `imagegen`
2. Component/SVG/PNG fallback

Do not send long Chinese poster text into the image prompt. Render text in components.
When using built-in imagegen, copy the selected output from `$CODEX_HOME/generated_images/...` back into the current book project path before referencing it.
Use `imagegen_sources/<asset-id>.png` as the project-bound landing path for selected imagegen assets. The composition step overlays reliable Chinese text and UI labels on top of these images.

### TTSProvider

Input:

- `text`
- `voice`
- `speed`
- `pitch`
- `emotion`
- `outputPath`

Output:

- `ok`
- `audioPath`
- `durationSec`
- `metadata`

Generate one TTS asset per scene. Warn if generated audio is materially longer than scene duration.

Default provider:

1. OpenRouter speech API via `OPENROUTER_API_KEY`.
2. Resolve the key from the process environment first, then the Hermes env path from `hermes config env-path`, then common local config files.
3. If OpenRouter is not authenticated or the key is missing, record the exact provider error in `tts_manifest.json`.
4. Use macOS `say` only as a local development fallback so the video still has sound; do not label fallback audio as OpenRouter output.

Default tested OpenRouter values:

- model: `microsoft/mai-voice-2`
- voice: `zh-CN-XiaoxiaoNeural`

### MusicProvider

Input:

- `style`
- `durationSec`
- `loopable`
- `outputPath`

Default BGM should be calm, structured, loopable, and ducked under narration.

### RenderProvider

Input:

- `styleBible`
- `storyboard`
- `assetManifest`
- `renderPlan`

Output:

- `ok`
- `finalVideoPath`
- `coverPath`
- `reportPath`
- `metadata`

### OpenRouterVideoProvider

Default provider for final scene motion:

- endpoint: `POST /api/v1/videos`, then poll the returned `polling_url`
- default model: `bytedance/seedance-2.0-fast`
- aspect ratio: `9:16`
- resolution: `720p`
- duration: integer seconds derived from `render_timing.json`, clamped to the model-supported short clip range

Generate one clip per scene and store it under `video_clips/openrouter/<sceneId>.mp4`. Write `openrouter_video_manifest.json` with the model, resolution, job ids, paths, and errors. Do not ask the video model to render Chinese subtitles or long text; final titles and subtitles remain renderer overlays from `output/video_overlays/*.png`.

Fallback rule: if OpenRouter video fails, partially completes, or times out, keep the manifest/run log and use the local Remotion/ffmpeg motion-segment renderer for missing scenes. If only some clips exist, mix OpenRouter clips for those scenes with local fallback clips for the rest and disclose the partial provider status.

### MotionGraphicsProvider

Default provider: `svg_motion`.

Input:

- `motionGraphicsSpec`
- `styleBible`
- `outputPath`
- `width`
- `height`
- `fps`
- `transparentBackground`

Output:

- `ok`
- `assetPath`
- `providerName`
- `metadata`

Motion quality defaults:

- use staggered element entry
- use `draw_line` for connectors
- use fade/slide/scale for cards and icons
- keep transparent backgrounds so the layer can be composited
- do not bake long Chinese copy into AI-generated raster/video outputs

### FinalAssemblyProvider

Input:

- `assembly_timeline.json`
- `styleBible`
- `outputPath`

Output:

- `finalVideoPath`
- `coverPath`
- `renderReportMarkdown`
- `metadata`

Final assembly order: background video or style frame, motion graphics, renderer text overlays, subtitles, TTS, BGM. TTS and scene timings must align through `render_timing.json` and `assembly_timeline.json`.

## Remotion Requirements

Create two compositions in a real implementation:

- `BookVideoComposition`: 9:16 video, scenes, transitions, captions, TTS, BGM.
- `CoverPosterComposition`: 4:5 poster, one-frame render.

Components:

- `Scene`
- `Caption`
- `Transition`
- `CoverPoster`
- `PyramidDiagram`
- `ProcessFlow`
- `ConceptList`
- `Mascot`
- `TagBar`

Keep all scene styling sourced from `styleBible`; do not let individual scenes invent their own palette.

The pipeline should also write a runnable `remotion/` directory per book project. Use Remotion primitives such as `Composition`, `Sequence`/`Series`, `Img`, and `staticFile` so the generated project can be rendered by the Remotion plugin or CLI. The Remotion composition should take scene order and durations from `storyboard.json`/`render_timing.json` and display the composited storyboard frames from `scene_images/`. This Remotion path is the local fallback whenever OpenRouter video is unavailable.

## Render Plan Defaults

- Renderer: `openrouter-video`
- Fallback renderer: local `remotion` project plus ffmpeg motion segments
- FPS: `30`
- Width/height for `9:16`: `1080x1920`
- Cover `4:5`: `1080x1350`
- Transitions: `fade`, `slide-left`, `slide-up`, `soft-zoom`
- Subtitles: enabled, key sentence mode, max 2 lines
- BGM: enabled, ducking enabled, volume `0.18`
- Render timing: derive `render_timing.json` from real TTS duration when audio exists.
- Motion: OpenRouter video clips first; local fallback render should generate per-scene motion segments with subtle zoom/pan before muxing audio.

## Honest Scaffold Outputs

When real audio providers are not configured, create explicit handoff files:

- `.tts.txt` narration handoff instead of fake MP3s
- `.music.txt` BGM brief instead of fake audio

The local component renderer may produce fallback poster PNGs, scene PNGs, per-scene TTS files, `render_timing.json`, `output/narration.m4a`, `subtitles/all.ass`, and `output/final_video.mp4`. OpenRouter video may additionally produce `openrouter_video_manifest.json` and `video_clips/openrouter/*.mp4`. Visible subtitles should be composited into `scene_images/*.png`; ASS/SRT files are sidecar assets for editing and downstream renderer replacement. The asset manifest should mark the default image provider as `imagegen`, keep `imagegen_prompts.json` for project-bound generation, and mark local component media as fallback assets with `requiresProvider: false`. Videos should include image-rich scene visuals, readable subtitles, subtle per-scene motion, and no debug/footer filler.
