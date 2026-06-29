# Book2Video Project Contract

This project implements the first runnable project baseline for `Book2VideoSkill_spec_v1_1.md`.

## Architecture

```text
Book2VideoSkill
  -> Book2StoryboardTool
  -> Storyboard2AssetsTool
  -> Assets2VideoTool
```

The main skill orchestrates; the tools own their separate stages.

## Current Boundary

Implemented:

- Input normalization and defaults
- `BookCore`
- `StyleBible`
- `CoverPosterPlan`
- `Storyboard`
- Narration and Xiaohongshu publish draft
- SVG component fallback assets
- TTS/music handoff files
- SRT subtitles
- `AssetManifest`
- `RenderPlan`
- Mock render report and project bundle
- Node test coverage for the Pyramid Principle acceptance path

Not implemented:

- Real ImageGen provider
- Real TTS provider
- Real music provider
- Real Remotion render to MP4
- Hyperframe render adapter beyond contract shape

Do not rename scaffold handoff files as real media outputs until the corresponding provider is wired and verified.
