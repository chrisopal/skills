import { writeFile } from 'node:fs/promises';
import path from 'node:path';
import { ensureDir, relPath, writeJson } from '../utils/file.js';
import { sceneToSrt } from '../utils/subtitle.js';
import { buildMusicBrief } from '../utils/audio.js';

function escapeXml(value) {
  return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

async function writeSvgCard(filePath, title, subtitle, width, height) {
  await writeFile(
    filePath,
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="${width}" height="${height}" fill="#FFFDF7"/>
  <rect x="64" y="64" width="${width - 128}" height="${height - 128}" rx="28" fill="#FFFFFF" stroke="#F4A261" stroke-width="4"/>
  <text x="96" y="150" font-family="Arial, sans-serif" font-size="54" font-weight="700" fill="#F97316">${escapeXml(title)}</text>
  <text x="96" y="230" font-family="Arial, sans-serif" font-size="30" fill="#0B5D3B">${escapeXml(subtitle)}</text>
  <line x1="96" y1="282" x2="${width - 96}" y2="282" stroke="#F4A261" stroke-width="4"/>
  <text x="96" y="${height - 110}" font-family="Arial, sans-serif" font-size="28" fill="#333333">Text is rendered by component, not image model.</text>
</svg>
`,
    'utf8'
  );
}

export class Storyboard2AssetsTool {
  async run({ styleBible, storyboard, coverPosterPlan }, projectDir) {
    const sceneDir = path.join(projectDir, 'scene_images');
    const ttsDir = path.join(projectDir, 'tts_audio');
    const subtitleDir = path.join(projectDir, 'subtitles');
    const bgmDir = path.join(projectDir, 'bgm');
    await Promise.all([ensureDir(sceneDir), ensureDir(ttsDir), ensureDir(subtitleDir), ensureDir(bgmDir)]);

    const coverPath = path.join(projectDir, 'cover.svg');
    const mascotPath = path.join(projectDir, 'mascot.svg');
    await writeSvgCard(coverPath, coverPosterPlan.headline, coverPosterPlan.subtitle, styleBible.coverWidth, styleBible.coverHeight);
    await writeSvgCard(mascotPath, '原创书籍角色', '专业、克制、不过度卡通', 512, 512);

    const sceneImages = [];
    const ttsAssets = [];
    const subtitleAssets = [];
    let elapsed = 0;

    for (const scene of storyboard.scenes) {
      const sceneImage = path.join(sceneDir, `${scene.sceneId}.svg`);
      const ttsFile = path.join(ttsDir, `${scene.sceneId}.tts.txt`);
      const subtitleFile = path.join(subtitleDir, `${scene.sceneId}.srt`);
      await writeSvgCard(sceneImage, scene.title, scene.visualDescription.slice(0, 48), styleBible.width, styleBible.height);
      await writeFile(ttsFile, `${scene.narration}\n`, 'utf8');
      await writeFile(subtitleFile, sceneToSrt(scene), 'utf8');

      sceneImages.push({
        sceneId: scene.sceneId,
        path: relPath(sceneImage, projectDir),
        status: 'placeholder',
        provider: 'component_svg_fallback',
        requiresProvider: true,
        prompt: scene.imageSourceStrategy.imagePrompt
      });
      ttsAssets.push({
        sceneId: scene.sceneId,
        path: relPath(ttsFile, projectDir),
        status: 'placeholder',
        provider: 'tts_handoff_text',
        requiresProvider: true,
        durationSec: scene.durationSec
      });
      subtitleAssets.push({
        sceneId: scene.sceneId,
        path: relPath(subtitleFile, projectDir),
        status: 'generated',
        format: 'srt',
        startSec: elapsed,
        durationSec: scene.durationSec
      });
      elapsed += scene.durationSec;
    }

    const bgmPath = path.join(bgmDir, 'main.music.txt');
    await writeFile(bgmPath, `${buildMusicBrief(storyboard)}\n`, 'utf8');

    const assetManifest = {
      projectName: storyboard.projectName,
      durationSec: storyboard.targetDurationSec,
      aspectRatio: styleBible.aspectRatio,
      coverImage: {
        path: relPath(coverPath, projectDir),
        status: 'placeholder',
        provider: 'component_svg_fallback',
        requiresProvider: true
      },
      mascotImage: {
        path: relPath(mascotPath, projectDir),
        status: 'placeholder',
        provider: 'component_svg_fallback',
        requiresProvider: true
      },
      sceneImages,
      ttsAssets,
      subtitleAssets,
      musicAsset: {
        path: relPath(bgmPath, projectDir),
        status: 'placeholder',
        provider: 'music_handoff_text',
        requiresProvider: true,
        durationSec: storyboard.targetDurationSec
      }
    };

    await writeJson(path.join(projectDir, 'asset_manifest.json'), assetManifest);
    await writeFile(
      path.join(projectDir, 'assets_ready_report.md'),
      ['# Assets Ready Report', '', 'Status: scaffold placeholders created.', '', '- Cover and scene visuals are SVG component fallbacks.', '- TTS files are text handoffs for a real TTS provider.', '- BGM is a music brief handoff.', '- Subtitles are generated SRT files.', ''].join('\n'),
      'utf8'
    );

    return { assetManifest };
  }
}
