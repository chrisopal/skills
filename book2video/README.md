# book2video

`book2video` is a dependency-light Node project scaffold for turning a book title or Book2Skill-style summary into a short-video production package.

It follows the `Book2VideoSkill_spec_v1_1.md` contract:

- Extract `BookCore` before storyboard generation.
- Generate a Xiaohongshu `4:5` cover poster plan.
- Generate a `6-8` scene, <= 300 second storyboard.
- Keep the main skill as an orchestrator over three tools.
- Preserve honest placeholder handoffs until real Image/TTS/Music/Render providers are connected.

## Run

```bash
npm run book2video -- --input examples/pyramid-principle.input.json --output-root output
```

Or:

```bash
node src/cli/book2video.js --book "金字塔原理" --author "芭芭拉·明托" --output-root output
```

## Verify

```bash
npm test
npm run check
```

Generated projects include JSON, Markdown, SVG placeholder visuals, TTS/music handoff text, SRT subtitles, render plan, render report, and a project bundle. Real `.mp4`, `.png`, `.mp3`, and BGM files require provider integration.
