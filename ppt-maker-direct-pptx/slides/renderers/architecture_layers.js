'use strict';

/**
 * Phase-2 stub for pattern 'architecture_layers'. Replaced by the real renderer in Phase 7.
 * Draws a labeled grid of provided slots so intent authors can preview
 * layout shape without polished styling.
 */
const { drawTitle, drawLabeledGrid } = require('./_stub_helpers');

function createSlide(pres, theme, slots, regions) {
  const slide = pres.addSlide();
  const titleText = slots && (slots.title || slots.headline || slots.section_title || slots.before_title);
  drawTitle(slide, theme, regions, titleText);
  if (regions && regions.content) {
    drawLabeledGrid(slide, slots || {}, regions.content, theme);
  }
  return slide;
}

module.exports = { createSlide, patternId: 'architecture_layers' };
