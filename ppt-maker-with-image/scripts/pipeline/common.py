from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_asset_json(name: str) -> dict[str, Any]:
    return load_json(skill_root() / "assets" / name)


def resolve_output_dir(job: dict[str, Any], cli_output_dir: str, job_path: Path) -> Path:
    if cli_output_dir:
        return Path(cli_output_dir).expanduser().resolve()
    output_dir = job.get("output", {}).get("directory")
    if output_dir:
        return (job_path.parent / output_dir).resolve()
    return (job_path.parent / "artifacts").resolve()


def load_prompt_template(name: str) -> str:
    content = (skill_root() / "references" / "prompt-templates.md").read_text(encoding="utf-8")
    anchor = f"## {name}"
    start = content.index(anchor)
    next_idx = content.find("\n## ", start + 1)
    block = content[start : next_idx if next_idx != -1 else len(content)]
    first = block.find("```text")
    last = block.rfind("```")
    if first == -1 or last == -1 or last <= first:
        raise ValueError(f"Prompt template not found: {name}")
    return block[first + len("```text") : last].strip()


def ensure_huixin_assets(job: dict[str, Any]) -> None:
    template_id = (job.get("template_id") or "").strip().lower()
    template_name = (job.get("template_name") or "").strip()
    if template_id == "huixin" or template_name == "慧新":
        if not job.get("master_style"):
            job["master_style"] = load_asset_json("huixin_master_style_brief.json")
        if not job.get("style"):
            job["style"] = "慧新"


def build_requirement_summary(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "template_id": job.get("template_id"),
        "template_name": job.get("template_name"),
        "topic": job.get("topic"),
        "target_audience": job.get("target_audience"),
        "purpose": job.get("purpose"),
        "style": job.get("style"),
        "page_count": job.get("page_count"),
        "key_points": job.get("key_points", []),
        "must_have_sections": job.get("must_have_sections", []),
        "constraints": job.get("constraints", {}),
    }
