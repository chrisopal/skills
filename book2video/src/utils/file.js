import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

export async function ensureDir(dir) {
  await mkdir(dir, { recursive: true });
}

export async function writeJson(filePath, value) {
  await ensureDir(path.dirname(filePath));
  await writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

export async function readJson(filePath) {
  return JSON.parse(await readFile(filePath, 'utf8'));
}

export function relPath(filePath, rootDir) {
  return path.relative(rootDir, filePath).split(path.sep).join('/');
}
