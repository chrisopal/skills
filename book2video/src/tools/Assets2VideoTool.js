import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { ensureDir, writeJson } from '../utils/file.js';

export class Assets2VideoTool {
  async run({ styleBible, storyboard, assetManifest, renderer = 'remotion' }, projectDir) {
    await ensureDir(path.join(projectDir, 'output'));
    const renderPlan = {
      renderer,
      compositionName: 'BookVideoComposition',
      coverCompositionName: 'CoverPosterComposition',
      fps: styleBible.fps,
      width: styleBible.width,
      height: styleBible.height,
      coverWidth: styleBible.coverWidth,
      coverHeight: styleBible.coverHeight,
      durationSec: storyboard.targetDurationSec,
      durationLimitSec: storyboard.durationLimitSec,
      sceneOrder: storyboard.scenes.map((scene) => scene.sceneId),
      globalStyleRef: 'style_bible.json',
      storyboardRef: 'storyboard.json',
      assetManifestRef: 'asset_manifest.json',
      narrationRef: 'narration_script.md',
      defaultTransition: { type: 'fade', durationMs: 320 },
      subtitle: { enabled: true, mode: 'key_sentence', maxLines: 2, highlightColor: '#FF6A00' },
      bgm: { enabled: true, ducking: true, volume: 0.18 },
      export: { format: 'mp4', quality: 'standard', platform: styleBible.platform },
      providerStatus: renderer === 'hyperframe' ? 'adapter-designed-not-implemented' : 'mock-render-plan'
    };

    await writeJson(path.join(projectDir, 'render_plan.json'), renderPlan);
    await writeFile(path.join(projectDir, 'output', 'final_video.mock.txt'), 'Mock render placeholder. Wire a real RenderProvider to produce output/final_video.mp4.\n', 'utf8');
    await writeFile(
      path.join(projectDir, 'render_report.md'),
      [
        '# Render Report',
        '',
        `Renderer: ${renderer}`,
        `Duration: ${storyboard.targetDurationSec} sec`,
        `Scenes: ${storyboard.scenes.length}`,
        '',
        'Status: mock render handoff created.',
        '',
        'Real media still required:',
        '- output/final_video.mp4',
        '- cover.png if a PNG poster is required',
        '- tts_audio/*.mp3',
        '- bgm/main.mp3',
        '',
        `Asset placeholders: ${assetManifest.sceneImages.filter((item) => item.status === 'placeholder').length} scene visuals`,
        ''
      ].join('\n'),
      'utf8'
    );
    await writeFile(path.join(projectDir, 'project_bundle.mock.txt'), 'Bundle handoff placeholder. Zip packaging can be added by deployment tooling.\n', 'utf8');
    return { renderPlan };
  }
}
