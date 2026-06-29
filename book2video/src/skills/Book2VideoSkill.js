import path from 'node:path';
import { defaultInput } from '../config/defaultConfig.js';
import { Book2StoryboardTool, slugifyBook } from '../tools/Book2StoryboardTool.js';
import { Storyboard2AssetsTool } from '../tools/Storyboard2AssetsTool.js';
import { Assets2VideoTool } from '../tools/Assets2VideoTool.js';

export class Book2VideoSkill {
  constructor({
    book2StoryboardTool = new Book2StoryboardTool(),
    storyboard2AssetsTool = new Storyboard2AssetsTool(),
    assets2VideoTool = new Assets2VideoTool()
  } = {}) {
    this.book2StoryboardTool = book2StoryboardTool;
    this.storyboard2AssetsTool = storyboard2AssetsTool;
    this.assets2VideoTool = assets2VideoTool;
  }

  normalizeInput(input) {
    const normalized = { ...defaultInput, ...input };
    if (!normalized.bookTitle) throw new Error('bookTitle is required');
    normalized.durationLimitSec = Number(normalized.durationLimitSec);
    normalized.targetDurationSec = Math.min(Number(normalized.targetDurationSec), normalized.durationLimitSec);
    return normalized;
  }

  async run(input, { outputRoot = 'output', outputDir, storyboardOnly = false, coverOnly = false } = {}) {
    const normalized = this.normalizeInput(input);
    const projectDir = outputDir || path.join(outputRoot, slugifyBook(normalized.bookTitle));
    const storyboardResult = await this.book2StoryboardTool.run(normalized, projectDir);
    if (storyboardOnly) return { projectDir, input: normalized, storyboardResult };
    const assetResult = await this.storyboard2AssetsTool.run(storyboardResult, projectDir);
    if (coverOnly) return { projectDir, input: normalized, storyboardResult, assetResult };
    const renderResult = await this.assets2VideoTool.run(
      {
        ...storyboardResult,
        assetManifest: assetResult.assetManifest,
        renderer: normalized.outputMode
      },
      projectDir
    );
    return { projectDir, input: normalized, storyboardResult, assetResult, renderResult };
  }
}
