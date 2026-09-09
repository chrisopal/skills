# PPT Master Plus v06: Huixin Compact

This distribution retains the upstream 4.5.0 engine and six Huixin Decks.
Ordinary Huixin generation uses one design direction, selective reference
loading, no default speaker notes, and compact validation output. Non-Huixin
Brand/Style/Layout/Deck presets are removed. Generic chart, table and icon
assets remain available; template count is not itself a token measurement.

The compact ZIP omits AI rendering/palette/type comparison PNGs and five optional
`reference_visual.png` inspiration images. All six themes, 129 SVG pages,
production logos/backgrounds, icons, charts, tables and exporter code remain.
No production image is resized or recompressed. Full planning retains its
textual rendering choices, but optional comparison thumbnails are unavailable.
Do not download or regenerate omitted samples during ordinary generation.

## Install or Upgrade

1. Close active PPT generation tasks. Back up the existing `ppt-master-plus`
   directory and move its `projects/` or other user outputs outside the Skill.
2. Replace the whole old Skill directory with the ZIP's `ppt-master-plus/`.
   Do not merge directories: otherwise removed presets can remain installed.
   Do not leave the backup as another discoverable Skill in the same skill root.
3. Use the host's Skill import function or its configured local Skill directory.
   Start a new task so the host reloads the entry instructions.
4. With one Python 3.10+ interpreter, run:

```bash
python3 -m pip install -r /absolute/path/ppt-master-plus/requirements-core.txt
python3 /absolute/path/ppt-master-plus/scripts/huixin_runtime.py preflight
```

On Windows, use `python` if `python3` is unavailable. Use the same interpreter
for installation, conversion and export. The base deck path needs no API key,
image provider, TTS service or preview server. Input converters and advanced
features may need their existing optional packages from `requirements.txt`;
install those only when used. Font and visual-renderer availability are checked
by the host for the actual deck; base preflight does not certify those features.

## Usage

Ask for a monthly report, sales dashboard, product architecture, consulting
proposal, training deck or promotion deck. Huixin is selected automatically.
Give the audience, page count, source material and factual constraints. An exact
registered Huixin name/id selects that theme; unsupported page roles are composed
in the same identity instead of forced into an unsuitable prototype.

Request multiple design options, staged confirmation, an interactive editor or
reusable native master structure explicitly to use the full workflow. Existing
PPTX filling, faithful reconstruction, narration and custom external templates
remain available through their dedicated routes.

## Distribution Check

```bash
python3 /absolute/path/ppt-master-plus/scripts/attribution_guard.py
python3 /absolute/path/ppt-master-plus/scripts/package_huixin.py /outside/skill/ppt-master-plus-v06.zip
```

For maintainers who need the reference gallery, build from the full source
checkout with `--include-reference-images` and a different output filename.
The compact install contains the preset metadata, not those optional PNGs.

The packager retains source, licensed reusable assets and runtime documents;
excludes projects, sample PPTX/PDFs, logs, caches, hidden credentials and ZIPs;
checks Huixin-only catalogs; and reports file count, bytes and SHA-256.
Keep required license and attribution files intact. Future upstream syncs must
preserve the Plus routing overlay and rerun the Huixin-only package checks.

Token savings require a same-input, same-model before/after benchmark. Reduced
instruction size and tool chatter are verified mechanisms, not a promised
billing percentage.
