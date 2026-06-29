#!/usr/bin/env node
import { readFile } from 'node:fs/promises';
import { Book2VideoSkill } from '../skills/Book2VideoSkill.js';
import { logStep } from '../utils/logger.js';

function parseArgs(argv) {
  const args = {};
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (!token.startsWith('--')) continue;
    const key = token.slice(2);
    if (['storyboard-only', 'cover-only'].includes(key)) {
      args[key] = true;
    } else {
      args[key] = argv[index + 1];
      index += 1;
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const input = args.input ? JSON.parse(await readFile(args.input, 'utf8')) : {};
  if (args.book) input.bookTitle = args.book;
  if (args.author) input.bookAuthor = args.author;
  if (args.platform) input.targetPlatform = args.platform;
  if (args.duration) input.targetDurationSec = Number(args.duration);
  if (args.ratio) input.aspectRatio = args.ratio;
  if (args.renderer) input.outputMode = args.renderer;
  if (args.style) input.stylePreset = args.style;

  const skill = new Book2VideoSkill();
  const result = await skill.run(input, {
    outputRoot: args['output-root'] || 'output',
    outputDir: args['output-dir'],
    storyboardOnly: Boolean(args['storyboard-only']),
    coverOnly: Boolean(args['cover-only'])
  });

  logStep('project', result.projectDir);
  logStep('book', result.input.bookTitle);
  logStep('scenes', result.storyboardResult.storyboard.scenes.length);
  logStep('duration_sec', result.storyboardResult.storyboard.targetDurationSec);
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exitCode = 1;
});
