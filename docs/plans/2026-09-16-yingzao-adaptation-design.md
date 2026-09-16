# Yingzao local adaptation

## Scope and rationale

The upstream baseline is preserved separately at commit `ead1462`, from
`op7418/guizang-yingzao-skill` revision `58c9b8738858bae0ab2c669d0a0fead90d4a80c9`.
Maintain this reusable skill under `yingzao/` and synchronize the installed copy
after validation and push. Existing unrelated workspace changes are outside scope.

Use small additions around the original renderer and compiler. A full workflow
engine would duplicate the Agent's creative decisions; prompt-only guidance would
not fix stale reports or runtime discovery. Keep the original image roles, Token
contracts, required quantity, and feedback-based regeneration boundary.

## Changes

1. A dispatch entrypoint forwards arguments and exit codes to existing scripts,
   preserving caller cwd. Runtime discovery adds an optional user-owned environment
   at `~/.local/share/yingzao/venv`; no installation happens during discovery.
   Do not deduplicate virtualenvs by their resolved Python binary.
2. Successful rendering fingerprints the exact spec and output guide. The compiler
   rejects missing or mismatched fingerprints, including legacy reports. Regenerate
   the report and guide to migrate. Hashes detect stale inputs, not report forgery.
3. A readback recorder validates explicit Agent observations in five visual domains,
   retains issues and uncertainty, and fingerprints the inspected image. It performs
   no aesthetic inference, OCR, model invocation, scoring, or regeneration.
4. An optional shared series JSON fixes palette, display glyph, material and identity
   policy. The compiler validates and includes it in the final prompt and manifest;
   per-image geometry remains governed by the existing design plan. When the readback
   is attached to a series manifest it also requires a series observation.

## Acceptance

- Upstream tests continue passing; changed spec/guide and legacy reports fail before READY.
- Real renderer output contains correct hashes; series content reaches tool_arguments.
- Default Python discovers the compatible local environment and the runner preserves failures.
- Incomplete readback is rejected; input images cannot be overwritten by reports.
- Skill and catalog validators pass; repository and installed trees match after sync.
- No live image generation is required for this change. Visual quality and cross-image
  consistency remain unverified until exercised with real photographs and a model.
