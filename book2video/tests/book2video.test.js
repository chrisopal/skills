import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile, access } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { Book2VideoSkill } from '../src/index.js';
import { validateProjectData } from '../src/utils/validation.js';

test('generates and validates the Pyramid Principle scaffold', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'book2video-node-'));
  try {
    const skill = new Book2VideoSkill();
    const result = await skill.run(
      {
        bookTitle: '金字塔原理',
        bookAuthor: '芭芭拉·明托',
        targetDurationSec: 260
      },
      { outputRoot: root }
    );
    const { bookCore, styleBible, coverPosterPlan, storyboard } = result.storyboardResult;
    assert.deepEqual(validateProjectData({ bookCore, styleBible, coverPosterPlan, storyboard }), []);
    assert.equal(storyboard.scenes.length, 7);
    assert.equal(storyboard.targetDurationSec, 260);
    assert.equal(bookCore.visualModel.type, 'pyramid');
    assert.equal(bookCore.aiSkillCandidate.name, 'AI汇报结构生成器');
    assert.equal(styleBible.visualStyle.palette.primary, '#F97316');
    assert.equal(styleBible.visualStyle.palette.secondary, '#0B5D3B');
    await access(path.join(result.projectDir, 'asset_manifest.json'));
    await access(path.join(result.projectDir, 'render_plan.json'));
    await access(path.join(result.projectDir, 'output', 'final_video.mock.txt'));
    const publishDraft = await readFile(path.join(result.projectDir, 'xiaohongshu_publish.md'), 'utf8');
    assert.match(publishDraft, /AI汇报结构生成器/);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});
