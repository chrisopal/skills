# Local workflow additions

## Script entrypoint and runtime

Run `python3 <skill-dir>/scripts/run.py <command> ...` from the caller's workspace.
Commands: `check`, `tokens`, `preflight`, `rectify`, `mask`, `fit`, `typeset`,
`prepare`, `compare`, `readback`. Arguments and exit codes are forwarded to the
original scripts; `run.py prepare --help` shows compiler options. This is a dispatch
entrypoint, not an automatic creative pipeline or an image-generation client.

Dependency lookup checks the current interpreter, `CAP_PYTHON`, caller/ancestor
`.venv` directories, then `~/.local/share/yingzao/venv/bin/python`. It never installs
packages. Create an isolated environment explicitly if none works. On this machine
the user environment has already been prepared; no global Python changes are needed.

## Bound typeset reports

Render the guide and its report in the same `typeset` call. Reports now contain
`integrity.spec_sha256` and `integrity.guide_sha256`. `prepare` rejects old reports
or changed inputs. Rerun `typeset`; never manually patch hashes to reuse a report.
`--validate-only` cannot produce a generation-ready guide report.

## Optional series

Use only for a requested series, not ordinary single images. Save shared decisions
once as a series JSON outside the skill package and reuse the same file across runs:

```json
{
  "schema_version": 1,
  "series_id": "city-2026",
  "shared": {
    "palette": "mineral red and warm white",
    "display_glyph": "narrow carved strokes with consistent optical weight",
    "material": "fine paper grain",
    "identity_policy": "preserve each photographed building's real roof and inscriptions"
  }
}
```

Add `--series-spec /absolute/path/series.json` to `prepare`. These four shared fields
are required, nonempty text and must agree with each image's creative brief. The
compiler records the content/hash and appends it to the exact final model prompt.
The call signature changes with the series content. This constrains input intent;
it does not guarantee matching generated pixels. Keep per-photo layout choices.

## Explicit visual readback

First open the final image using the Agent's image-reading tool. Record observations
in JSON, with exactly `subject`, `background`, `glyphs`, `interaction`, `reference`.
Each value contains `status` (`pass`, `issue`, or `uncertain`) and a nonempty `evidence`
string describing visible details. Check required text against the requested copy;
use `uncertain` if it cannot be read reliably. A structural shape or text error must
remain an issue even when the rest of the poster looks good.

```json
{
  "subject": {"status": "pass", "evidence": "The source roof outline and asymmetric doorway remain visible."},
  "background": {"status": "pass", "evidence": "A distinct mineral-red field frames the roof."},
  "glyphs": {"status": "uncertain", "evidence": "Small place-name text is not readable at this scale."},
  "interaction": {"status": "pass", "evidence": "The roof overlaps the lower title edge."},
  "reference": {"status": "pass", "evidence": "The selected reference's offset title/subject relationship is visible."}
}
```

These are illustrative observations, not reusable verdicts. Write evidence from
the actual image. Include `--manifest` for normal delivery; a series manifest also
requires a sixth `series` observation comparing the shared constraints.

```bash
python3 <skill-dir>/scripts/run.py readback \
  --image /absolute/path/final/poster.png \
  --observations /absolute/path/analysis/readback-observations.json \
  --manifest /absolute/path/analysis/generation-call.json \
  --output /absolute/path/analysis/readback.md
```

The recorder checks completeness, verifies the image can be decoded, and records
image/manifest fingerprints. It cannot determine whether observations are true.
Report the most important 0–3 problems to the user; do not automatically retry.
