/**
 * Shared helpers for Phase-2 renderer stubs.
 *
 * The real renderer implementations land in Phase 7; until then, every stub
 * draws a labeled grid showing where each slot will live so that intent
 * authors can preview layout shape without final styling.
 */

'use strict';

function inchesToCols(region, slotCount) {
  const cols = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(slotCount))));
  const rows = Math.ceil(slotCount / cols);
  return { cols, rows };
}

function drawTitle(slide, theme, regions, title) {
  if (!title) return;
  slide.addText(title, {
    x: regions.title.x,
    y: regions.title.y,
    w: regions.title.w,
    h: regions.title.h,
    fontSize: 24,
    bold: true,
    color: (theme && theme.text_primary) || '1E1E1E',
  });
}

function drawLabeledGrid(slide, slots, region, theme) {
  const slotEntries = Object.entries(slots).filter(
    ([key, value]) => typeof value === 'string' && value.length > 0,
  );
  const { cols, rows } = inchesToCols(region, slotEntries.length || 1);
  const cellW = region.w / cols;
  const cellH = region.h / rows;
  const stroke = (theme && theme.primary_green) || 'A8D86B';

  slotEntries.forEach(([slotName, value], idx) => {
    const col = idx % cols;
    const row = Math.floor(idx / cols);
    const x = region.x + col * cellW + 0.05;
    const y = region.y + row * cellH + 0.05;
    const w = cellW - 0.1;
    const h = cellH - 0.1;
    slide.addShape('roundRect', {
      x, y, w, h,
      line: { color: stroke, width: 1 },
      fill: { color: 'FFFFFF' },
      rectRadius: 0.1,
    });
    slide.addText(slotName, {
      x: x + 0.1,
      y: y + 0.1,
      w: w - 0.2,
      h: 0.3,
      fontSize: 10,
      color: '6B7280',
    });
    slide.addText(String(value), {
      x: x + 0.1,
      y: y + 0.4,
      w: w - 0.2,
      h: h - 0.5,
      fontSize: 14,
      color: '1E1E1E',
    });
  });
}

module.exports = { drawTitle, drawLabeledGrid };
