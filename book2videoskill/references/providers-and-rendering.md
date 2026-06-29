# Providers And Rendering

## Provider Contracts

Use provider adapters rather than embedding provider logic in the main skill.

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

The pipeline should also write a runnable `remotion/` directory per book project. Use Remotion primitives such as `Composition`, `Sequence`/`Series`, `Img`, and `staticFile` so the generated project can be rendered by the Remotion plugin or CLI. The Remotion composition should take scene order and durations from `storyboard.json` and display the composited imagegen storyboard frames from `scene_images/`.

## Render Plan Defaults

- Renderer: `remotion`
- FPS: `30`
- Width/height for `9:16`: `1080x1920`
- Cover `4:5`: `1080x1350`
- Transitions: `fade`, `slide-left`, `slide-up`, `soft-zoom`
- Subtitles: enabled, key sentence mode, max 2 lines
- BGM: enabled, ducking enabled, volume `0.18`

## Honest Scaffold Outputs

When real audio providers are not configured, create explicit handoff files:

- `.tts.txt` narration handoff instead of fake MP3s
- `.music.txt` BGM brief instead of fake audio

The local component renderer may produce fallback poster PNGs, scene PNGs, and `output/final_video.mp4` without TTS/BGM. The asset manifest should mark the default image provider as `imagegen`, keep `imagegen_prompts.json` for project-bound generation, and mark local component media as fallback assets with `requiresProvider: false`. Videos should include image-rich scene visuals, not only text cards.
