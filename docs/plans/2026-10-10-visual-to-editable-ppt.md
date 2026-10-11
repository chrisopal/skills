# Visual-to-editable PPT — approved design and implementation

Goal: accept a confirmed outline, exact slide content and visual style, generate
beautiful per-slide designs through the host image tool, then reconstruct and
validate an editable PPTX. Seven themes cover consulting blue/red/purple/green,
product solutions, marketing and annual celebrations.

Architecture: reuse consulting-ppt-image content schema and production state
(init/register/review/select/sync/audit); supply theme-aware prompts because its
current planner hardcodes ink green. Hand selected immutable images plus exact
content and source data to image-to-editable-ppt. Extend its existing backend
contract to support an observed native host tool, preserving existing defaults.
No second state machine, converter, added dependencies, customer assets or model
API included. Visual fidelity and editability are both inspected on final renders.

## Delivery steps

- [x] Baseline: inspect the two existing skills against purple-theme, non-Codex,
  title/order revision, partial-deck and authoritative-text scenarios.
- [x] Bridge tests first: reject draft rendering, preserve theme/content, select
  only approved versions, maintain order and hashes, reject stale selections,
  propagate exact content/data, refuse overwrite and mark partial exports.
- [x] Implement a small Python bridge using existing consulting pipeline APIs:
  theme prompt planning and immutable editable handoff only; all selection,
  review and sync continue through the original pipeline.
- [x] Add seven declarative theme profiles and reusable page composition recipes.
  Include exact palette, font hierarchy, layout and editable reconstruction rules.
- [x] Add host-tool contract support and regressions in the existing converter;
  preserve its state commands and source-faithful asset requirements.
- [x] Write SKILL.md, runtime/conversion/quality references, one draft input
  example, UI metadata, install/use README and root discovery entry.
- [x] Run bridge and dependency suites, syntax/JSON/link/skill checks, plus an
  independent realistic application of the new skill without live image calls.
- [x] Record measured results and untested visual/cross-host limits in STATUS;
  commit and push the feature branch, open a reviewable PR against main.

## Acceptance boundaries

Generated source pictures are intermediate artifacts. Editable output uses native
text/structure and separate bitmap artwork; no flattened full-slide background
with duplicate text. Source content corrects image/OCR errors; chart data are
never inferred from decorative raster geometry. Revision invalidates affected
images before conversion. Partial runs explicitly map stable IDs to local page
IDs; they are never labeled full decks. Run/page state remains editppt-owned.

Local contract and synthetic tests cannot prove live model visual quality or
installation in WorkBuddy/Claude Code. Report those separately. New runtime
support must be real code with propagation tests, not platform-name promises.

## Verification evidence

Baseline inspection found fixed green prompts, no generic host backend, and no
shared stale-conversion/content handoff. Implementation addresses those gaps
without changing consulting-ppt-image. Bridge regressions were first run red
for missing planning/handoff, native text audit, notes carrier and geometry
behavior, then green (23 tests). The existing 32 consulting tests remain green.
Converter adds six tests (including malformed-contract variants) to its existing
82. Independent forward testing used actual prepare with synthetic local images
and a fixture host-tool contract, and verified reordered partial mapping, old
handoff rejection and exact Chinese speaker notes. No live image calls occurred.

The bridge additionally verifies final native text and source-raster rejection;
this is explicitly not visual acceptance. The conversion carrier is input-only
and preserves original image bytes plus notes. All new Python/JSON/YAML parses,
relative Markdown links and Skill metadata were checked. Runtime sources are
covered by the converter suite; no new dependency was introduced.
