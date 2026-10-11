#!/usr/bin/env node
/** Author typed simulation ledgers with the bundled Artifact Tool public API. */
import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const args = process.argv.slice(2);
const argument = (name) => {
  const index = args.indexOf(name);
  if (index < 0 || !args[index + 1]) throw new Error(`Missing ${name}`);
  return args[index + 1];
};
const spec = JSON.parse(await fs.readFile(argument('--spec'), 'utf8'));
const output = argument('--out');
const previews = argument('--preview-dir');
const column = (index) => {
  let result = '';
  for (let n = index + 1; n > 0; n = Math.floor((n - 1) / 26)) result = String.fromCharCode(65 + (n - 1) % 26) + result;
  return result;
};
const literal = (value, key = '') => {
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) && /date|start|finish|due/.test(key)) {
    return new Date(`${value}T00:00:00.000Z`);
  }
  return typeof value === 'string' && /^[=+@-]/.test(value) ? `'${value}` : value ?? null;
};
if (!Array.isArray(spec.sheets) || !spec.sheets.length) throw new Error('Sheet data is required');
const workbook = Workbook.create();
const names = new Set();
const previewRanges = [];
for (const [index, data] of spec.sheets.entries()) {
  if (!data.name || data.name.length > 31 || /[\[\]*?:/\\]/.test(data.name) || names.has(data.name)) throw new Error('Invalid sheet name');
  names.add(data.name);
  const sheet = workbook.worksheets.add(data.name);
  sheet.showGridLines = false;
  if (data.summary) sheet.tabColor = '#0966D9';
  const seen = new Map();
  const headers = data.headers.map((value) => {
    const name = String(value), count = (seen.get(name) ?? 0) + 1;
    seen.set(name, count);
    return count > 1 ? `${name} ${count}` : name;
  });
  const start = data.summary ? 5 : 1;
  const rows = data.rows.map(row => headers.map((_, col) => literal(row[col], data.keys?.[col])));
  const values = [headers, ...rows];
  const endColumn = column(headers.length - 1), endRow = start + values.length - 1;
  const range = sheet.getRange(`A${start}:${endColumn}${endRow}`);
  range.values = values;
  range.format.font = { name: 'Arial Unicode MS', size: 10, color: '#0B1220' };
  range.format.verticalAlignment = 'top';
  range.format.wrapText = true;
  range.format.rowHeight = 30;
  const header = sheet.getRange(`A${start}:${endColumn}${start}`);
  header.format = { fill: '#0966D9', font: { name: 'Arial Unicode MS', size: 10, color: '#FFFFFF', bold: true }, horizontalAlignment: 'center', verticalAlignment: 'center', wrapText: true };
  header.format.rowHeight = 34;
  if (data.summary) {
    sheet.getRange('A2').values = [['设备维保工单平台项目概览']];
    sheet.getRange('A2:D2').format.font = { name: 'Arial Unicode MS', size: 14, bold: true, color: '#0B1220' };
    sheet.getRange('A3').values = [[`${spec.project_id} 模拟演练 内部审核`]];
    sheet.getRange('A3:D3').format.font = { name: 'Arial Unicode MS', size: 10, color: '#526075' };
  } else {
    sheet.freezePanes.freezeRows(1);
  }
  if (rows.length) {
    const table = sheet.tables.add(`A${start}:${endColumn}${endRow}`, true, `DeliveryTable${index + 1}`);
    table.showFilterButton = !data.summary;
  }
  for (let col = 0; col < headers.length; col++) {
    const cells = rows.map(row => row[col]);
    const numeric = cells.filter(value => typeof value === 'number');
    const date = cells.some(value => value instanceof Date);
    const maxLength = Math.max(headers[col].length, ...cells.map(value => typeof value === 'string' ? value.length : 0));
    const width = numeric.length && numeric.length === cells.length ? 16 : Math.min(58, Math.max(18, maxLength > 40 ? 48 : maxLength * 1.3));
    const colRange = sheet.getRange(`${column(col)}${start}:${column(col)}${endRow}`);
    colRange.format.columnWidth = data.summary ? [26, 30, 12, 52][col] : width;
    if (numeric.length) sheet.getRange(`${column(col)}${start + 1}:${column(col)}${endRow}`).setNumberFormat('#,##0.00');
    if (date) sheet.getRange(`${column(col)}${start + 1}:${column(col)}${endRow}`).setNumberFormat('yyyy-mm-dd');
  }
  if (rows.length) sheet.getRange(`A${start + 1}:${endColumn}${endRow}`).format.autofitRows();
  previewRanges.push({ name: data.name, range: `A1:${endColumn}${Math.min(endRow, start + 10)}` });
}
workbook.recalculate();
const inspection = await workbook.inspect({ kind: 'table', range: '项目概览!A5:D20', include: 'values,formulas', tableMaxRows: 16, tableMaxCols: 4, maxChars: 3000 });
const errors = await workbook.inspect({ kind: 'match', searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!', options: { useRegex: true, maxResults: 100 }, maxChars: 3000, summary: 'final formula error scan' });
await fs.mkdir(previews, { recursive: true });
for (const [index, previewRange] of previewRanges.entries()) {
  const preview = await workbook.render({ sheetName: previewRange.name, range: previewRange.range, scale: 1.5, format: 'png' });
  await fs.writeFile(path.join(previews, `${String(index + 1).padStart(2, '0')}-${previewRange.name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
await fs.writeFile(path.join(previews, 'artifact-tool-inspection.json'), JSON.stringify({ summary: inspection.ndjson, errors: errors.ndjson, ranges: previewRanges }, null, 2));
await fs.mkdir(path.dirname(output), { recursive: true });
const file = await SpreadsheetFile.exportXlsx(workbook);
await file.save(output);
console.log(JSON.stringify({ output, sheets: spec.sheets.length, previews: previewRanges.length }));
