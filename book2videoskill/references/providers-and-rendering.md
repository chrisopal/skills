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

1. `codex_image_plugin`
2. `imagegen`
3. Component/SVG fallback

Do not send long Chinese poster text into the image prompt. Render text in components.

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

## Render Plan Defaults

- Renderer: `remotion`
- FPS: `30`
- Width/height for `9:16`: `1080x1920`
- Cover `4:5`: `1080x1350`
- Transitions: `fade`, `slide-left`, `slide-up`, `soft-zoom`
- Subtitles: enabled, key sentence mode, max 2 lines
- BGM: enabled, ducking enabled, volume `0.18`

## Honest Scaffold Outputs

When real providers are not configured, create explicit handoff files:

- SVG cover or scene cards instead of fake PNGs
- `.tts.txt` narration handoff instead of fake MP3s
- `.music.txt` BGM brief instead of fake audio
- `final_video.mock.txt` instead of fake MP4

The asset manifest should mark each placeholder with `status: "placeholder"` and `requiresProvider: true`.
