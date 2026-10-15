#!/usr/bin/env python3
"""Install the sibling skills with conflict preflight and no overwrite."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


SKILLS = (
    "opportunity-analysis-skill", "opportunity-orchestrator", "opportunity-pursuit",
    "opportunity-solution-validation", "opportunity-commercial",
    "opportunity-negotiation", "opportunity-closeout", "opportunity-gtm",
)
EXCLUDED_DIRS = {".git", ".venv", ".skill_data", "__pycache__", "outputs", "output", "projects", "node_modules", ".pytest_cache"}
SOURCE_SUFFIXES = {".md", ".py", ".json", ".yaml", ".yml", ".toml", ".sql", ".css", ".html", ".js", ".txt"}


def source_files(root: Path):
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if path.is_file() and not path.is_symlink() and not any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in relative.parts):
            if path.suffix in SOURCE_SUFFIXES:
                yield relative


def fingerprint(root: Path) -> dict[str, str]:
    return {str(path): hashlib.sha256((root / path).read_bytes()).hexdigest() for path in source_files(root)}


def install(destination: Path, source_root: Path | None = None) -> dict:
    source_root = source_root or Path(__file__).resolve().parents[2]
    destination = destination.expanduser().resolve()
    pending, unchanged = [], []
    # Preflight every skill before creating or mutating the destination.
    for name in SKILLS:
        source, target = source_root / name, destination / name
        if not (source / "SKILL.md").is_file():
            raise FileNotFoundError(f"Missing source skill: {source}")
        if target.is_symlink():
            raise FileExistsError(f"Refusing symlink destination: {target}")
        if target.exists():
            if not target.is_dir() or fingerprint(source) != fingerprint(target):
                raise FileExistsError(f"Different skill already exists: {target}; preserve it and choose another destination.")
            unchanged.append(name)
        else:
            pending.append(name)
    destination.mkdir(parents=True, exist_ok=True)
    installed = []
    with tempfile.TemporaryDirectory(prefix=".opportunity-install-", dir=destination) as temp:
        staging = Path(temp)
        for name in pending:
            for relative in source_files(source_root / name):
                target = staging / name / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_root / name / relative, target)
        try:
            for name in pending:
                target = destination / name
                if target.exists():
                    raise FileExistsError(f"Destination changed after preflight: {target}")
                (staging / name).rename(target)
                installed.append(name)
        except Exception:
            for name in installed:
                shutil.rmtree(destination / name)
            raise
    return {"destination": str(destination), "installed": installed, "unchanged": unchanged}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dest", required=True, type=Path, help="Explicit destination containing sibling skill directories")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.dest), ensure_ascii=False, indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Install failed: {exc}\n")


if __name__ == "__main__":
    main()
