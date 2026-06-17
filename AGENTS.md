# Repository Operating Instructions

This repository stores local Codex skills, PPT templates, generated examples, and supporting documentation.

## Required Workflow

- After every repository modification, run verification that matches the changed surface before claiming completion.
- After verification passes, stage the relevant source, template, documentation, or configuration files, create a git commit, and push the branch to its configured remote.
- Commit messages must follow the Lore Commit Protocol when available in the active instructions: intent line first, then useful trailers such as `Tested:` and `Not-tested:`.
- Do not leave completed, verified work uncommitted or unpushed unless the user explicitly asks not to commit or push.

## Artifact Policy

- Do not stage, commit, or push generated outputs unless the user explicitly asks for them.
- Treat these as artifacts by default: preview screenshots, rendered PNG/JPG images, exported PPTX/PDF files, temporary browser outputs, local `projects/` workspaces, `.playwright-mcp/`, cache folders, and one-off validation snapshots.
- If an artifact is needed for verification, keep it local and mention its path in the final response instead of committing or pushing it.
- When committing PPT template work, include reusable template assets and source SVG/spec/index changes, but exclude sample decks, rendered previews, and transient validation files.

## PPT Template Work

- For `ppt-maker-with-svg`, follow `ppt-maker-with-svg/AGENTS.md` in addition to this file.
- Before modifying PPT Master templates or generation code, read the relevant `SKILL.md` and template workflow instructions.
- Keep template additions reusable: editable SVG structures, stable placeholders, consistent canvas size, and registered `design_spec.md` / index metadata.

## Status Updates

- Update `STATUS.md` for meaningful repository changes, especially template library updates, workflow policy changes, verification results, commit state, and push state.
- Keep entries concise and evidence-based: scope, changed files, validation, commit state, and remaining notes.
