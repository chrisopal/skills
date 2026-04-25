'use strict';

/**
 * Verify every renderer stub exports createSlide and patternId.
 *
 * Invoked by tests/test_renderer_stubs.py via subprocess. Exits 0 on success,
 * non-zero on the first failure with a diagnostic to stderr.
 */

const path = require('path');
const fs = require('fs');

const RENDERERS_DIR = path.resolve(__dirname, '..', 'slides', 'renderers');

const EXPECTED = [
  'architecture_layers',
  'before_after',
  'conclusion_top_modules',
  'cover',
  'evidence_grid',
  'four_card_matrix',
  'freeform',
  'kpi_strip',
  'section_divider',
  'summary_takeaways',
  'three_stage_path',
  'two_column_compare',
];

function fail(msg) {
  process.stderr.write(msg + '\n');
  process.exit(1);
}

const onDisk = fs
  .readdirSync(RENDERERS_DIR)
  .filter((f) => f.endsWith('.js') && !f.startsWith('_'))
  .map((f) => f.replace(/\.js$/, ''))
  .sort();

const expectedSorted = [...EXPECTED].sort();
if (onDisk.join(',') !== expectedSorted.join(',')) {
  fail(
    `Renderer set mismatch.\n  expected: ${expectedSorted.join(', ')}\n  found:    ${onDisk.join(', ')}`,
  );
}

// Build a minimal fake `pres` so createSlide can run end-to-end without pptxgenjs.
function makeFakePres() {
  const slide = {
    shapes: [],
    addText: function (text, opts) {
      this.shapes.push({ kind: 'text', text, opts });
      return this;
    },
    addShape: function (shape, opts) {
      this.shapes.push({ kind: 'shape', shape, opts });
      return this;
    },
  };
  return {
    addSlide: () => slide,
    _slide: slide,
  };
}

const stubRegions = {
  title: { x: 0.5, y: 0.4, w: 12.333, h: 1.0 },
  content: { x: 0.5, y: 1.6, w: 12.333, h: 5.0 },
};
const stubSlots = {
  title: 'Sample Title',
  headline: 'Sample Headline',
  section_title: 'Sample Section',
  cell_1_label: 'Label A',
  cell_1_value: '38%',
  cell_1_desc: 'demo description',
};

for (const id of EXPECTED) {
  const modulePath = path.join(RENDERERS_DIR, `${id}.js`);
  let mod;
  try {
    mod = require(modulePath);
  } catch (err) {
    fail(`require failed for ${id}: ${err.message}`);
  }
  if (typeof mod.createSlide !== 'function') {
    fail(`${id}: createSlide is not a function (got ${typeof mod.createSlide})`);
  }
  if (mod.patternId !== id) {
    fail(`${id}: patternId mismatch (got ${mod.patternId})`);
  }
  const pres = makeFakePres();
  let result;
  try {
    result = mod.createSlide(pres, { primary_green: 'A8D86B' }, stubSlots, stubRegions);
  } catch (err) {
    fail(`${id}: createSlide threw: ${err.message}`);
  }
  if (!result) {
    fail(`${id}: createSlide returned no slide`);
  }
  if (pres._slide.shapes.length === 0) {
    fail(`${id}: createSlide added no shapes`);
  }
}

process.stdout.write(`OK ${EXPECTED.length} renderers verified\n`);
