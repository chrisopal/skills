#!/usr/bin/env python3
"""Create a portable Codex skill from a book's BookCore output."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path

from book2video_common import read_json, slugify_book, slugify_skill_name, write_json


def write_openai_yaml(skill_dir: Path, skill_name: str, book_title: str, ai_skill_name: str) -> None:
    agents_dir = skill_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "openai.yaml").write_text(
        "\n".join(
            [
                "interface:",
                f'  display_name: "{ai_skill_name}"',
                f'  short_description: "Apply the extracted method from {book_title}"',
                f'  default_prompt: "Use ${skill_name} to apply this book-derived method to my material."',
                "",
            ]
        ),
        encoding="utf-8",
    )


def zip_dir(source_dir: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive.write(path, path.relative_to(source_dir.parent).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True, help="Book2Video project directory")
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    book_core = read_json(project_dir / "book_core.json")
    skill_candidate = book_core["aiSkillCandidate"]
    book_title = book_core["bookTitle"]
    skill_name = slugify_skill_name(skill_candidate["name"])
    if len(skill_name) < 8:
        skill_name = f"{slugify_book(book_title)}-skill"
    skill_root = project_dir / "extracted_skill"
    skill_dir = skill_root / skill_name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    (skill_dir / "references").mkdir(parents=True, exist_ok=True)
    (skill_dir / "assets").mkdir(parents=True, exist_ok=True)

    description = (
        f"Book-derived workflow skill extracted from {book_title}. Use when the user wants to apply "
        f"{skill_candidate['name']} to inputs such as {', '.join(skill_candidate.get('input', [])[:4])}, "
        f"and produce {', '.join(skill_candidate.get('output', [])[:4])}."
    )
    (skill_dir / "SKILL.md").write_text(
        "\n".join(
            [
                "---",
                f"name: {skill_name}",
                f'description: "{description}"',
                "---",
                "",
                f"# {skill_candidate['name']}",
                "",
                f"Use this skill to apply the method extracted from `{book_title}`.",
                "",
                "## Operating Rules",
                "",
                "- Start from the user's concrete material; do not give generic advice.",
                "- Preserve uncertainty. Mark weak or missing facts as `未确认`.",
                "- Produce the requested outputs in a reusable structure, not just commentary.",
                "- When conflicts or failures appear, convert them into explicit principles or rules.",
                "",
                "## Workflow",
                "",
                *[
                    f"{item['step']}. {item['title']}: {item['action']} -> {item['output']}"
                    for item in book_core.get("sop", [])
                ],
                "",
                "## Inputs",
                "",
                *[f"- {item}" for item in skill_candidate.get("input", [])],
                "",
                "## Outputs",
                "",
                *[f"- {item}" for item in skill_candidate.get("output", [])],
                "",
                "## Reference",
                "",
                "Read `references/book_core.json` for the extracted concepts, visual model, SOP, and use cases.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    write_openai_yaml(skill_dir, skill_name, book_title, skill_candidate["name"])
    write_json(skill_dir / "references" / "book_core.json", book_core)
    research_path = project_dir / "book_research.json"
    if research_path.exists():
        shutil.copy2(research_path, skill_dir / "references" / "book_research.json")
    (skill_dir / "assets" / "example-input.md").write_text(
        "\n".join(
            [
                "# Example Input",
                "",
                "Paste meeting notes, project facts, failure records, decision context, or source material here.",
                "The skill should convert them into the structured outputs defined in `SKILL.md`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    zip_path = project_dir / f"{skill_name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    zip_dir(skill_dir, zip_path)
    print(f"extracted_skill: {skill_dir}")
    print(f"skill_zip: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
