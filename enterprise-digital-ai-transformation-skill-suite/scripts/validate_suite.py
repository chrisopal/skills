#!/usr/bin/env python3
"""Validate the Enterprise Digital & AI Transformation Skill Suite.

Checks:
1. JSON/YAML syntax.
2. JSON Schema Draft 2020-12 validity.
3. Example 4A packages and architecture framework profile.
4. SKILL.md/manifest name, version, input, optional input, output, dependency parity.
5. Referenced schemas, reviewer independence, dependency ordering, and workflow contracts.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def markdown_section(text: str, heading: str, next_headings: list[str]) -> str:
    start = text.find(heading)
    if start < 0:
        return ""
    end = len(text)
    for candidate in next_headings:
        pos = text.find(candidate, start + len(heading))
        if pos >= 0:
            end = min(end, pos)
    return text[start + len(heading) : end]


def backtick_bullets(section: str) -> list[str]:
    return re.findall(r"^- `([^`]+)`", section, flags=re.MULTILINE)


def main() -> int:
    errors: list[str] = []

    json_files = list(ROOT.rglob("*.json"))
    yaml_files = list(ROOT.rglob("*.yaml")) + list(ROOT.rglob("*.yml"))

    for path in json_files:
        try:
            read_json(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"JSON parse failure: {path.relative_to(ROOT)}: {exc}")

    for path in yaml_files:
        try:
            read_yaml(path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"YAML parse failure: {path.relative_to(ROOT)}: {exc}")

    schemas: dict[str, dict[str, Any]] = {}
    for path in sorted((ROOT / "shared/schemas").glob("*.json")):
        try:
            schema = read_json(path)
            Draft202012Validator.check_schema(schema)
            schemas[path.name] = schema
        except Exception as exc:  # noqa: BLE001
            errors.append(f"Schema failure: {path.relative_to(ROOT)}: {exc}")

    package_examples = [
        ROOT / "examples/sample-project/target-4a-architecture.example.json",
        ROOT / "examples/sample-project/target-4a-architecture-package.example.yaml",
    ]
    package_schema = schemas.get("four-a-architecture-package.schema.json")
    if package_schema:
        validator = Draft202012Validator(package_schema)
        for path in package_examples:
            data = read_json(path) if path.suffix == ".json" else read_yaml(path)
            for err in validator.iter_errors(data):
                errors.append(
                    f"4A package example failure: {path.relative_to(ROOT)} "
                    f"at {list(err.path)}: {err.message}"
                )

    profile_schema = schemas.get("architecture-framework-profile.schema.json")
    if profile_schema:
        context = read_yaml(ROOT / "examples/sample-project/project-context.yaml")
        profile = context.get("architecture_framework_profile")
        for err in Draft202012Validator(profile_schema).iter_errors(profile):
            errors.append(
                f"Architecture framework profile failure at {list(err.path)}: {err.message}"
            )

    contract_examples = {
        "task-card.schema.json": ROOT / "examples/sample-project/task-card.example.yaml",
        "quality-review-report.schema.json": ROOT
        / "examples/sample-project/quality-review-report.example.yaml",
        "slide-content-pack.schema.json": ROOT
        / "examples/sample-project/slide-content-pack.example.yaml",
    }
    for schema_name, path in contract_examples.items():
        schema = schemas.get(schema_name)
        if schema:
            data = read_yaml(path)
            for err in Draft202012Validator(schema).iter_errors(data):
                errors.append(
                    f"Contract example failure: {path.relative_to(ROOT)} "
                    f"at {list(err.path)}: {err.message}"
                )

    artifact_header_schema = schemas.get("artifact-header.schema.json")
    if artifact_header_schema:
        header_validator = Draft202012Validator(artifact_header_schema)
        header_examples = package_examples + [
            ROOT / "examples/sample-project/slide-content-pack.example.yaml"
        ]
        for path in header_examples:
            data = read_json(path) if path.suffix == ".json" else read_yaml(path)
            for err in header_validator.iter_errors(data.get("artifact_header", {})):
                errors.append(
                    f"Artifact header failure: {path.relative_to(ROOT)} "
                    f"at {list(err.path)}: {err.message}"
                )

    skill_root = ROOT / ".agents/skills"
    skill_dirs = sorted(path for path in skill_root.iterdir() if path.is_dir())
    skill_names = {path.name for path in skill_dirs}
    manifests: dict[str, dict[str, Any]] = {}
    produced_outputs: set[str] = set()

    for directory in skill_dirs:
        skill_file = directory / "SKILL.md"
        manifest_file = directory / "manifest.yaml"
        if not skill_file.exists() or not manifest_file.exists():
            errors.append(f"Missing SKILL.md or manifest.yaml: {directory.relative_to(ROOT)}")
            continue

        text = skill_file.read_text(encoding="utf-8")
        manifest = read_yaml(manifest_file)
        manifests[directory.name] = manifest

        if manifest.get("name") != directory.name:
            errors.append(
                f"Skill name mismatch: directory={directory.name}, manifest={manifest.get('name')}"
            )

        version_match = re.search(r"\*\*Version\*\*: `([^`]+)`", text)
        markdown_version = version_match.group(1) if version_match else None
        if markdown_version != str(manifest.get("version")):
            errors.append(
                f"Skill version mismatch: {directory.name}, "
                f"SKILL.md={markdown_version}, manifest={manifest.get('version')}"
            )

        required_inputs = backtick_bullets(
            markdown_section(
                text,
                "## 必需输入",
                ["## 可选输入", "## 标准输出", "## 执行步骤"],
            )
        )
        optional_inputs = backtick_bullets(
            markdown_section(text, "## 可选输入", ["## 标准输出", "## 执行步骤"])
        )
        outputs = backtick_bullets(
            markdown_section(text, "## 标准输出", ["## 执行步骤", "## 质量规则"])
        )
        dependencies = backtick_bullets(
            markdown_section(
                text,
                "## 依赖 Skill",
                ["## Artifact 规则", "## 失败与降级", "## 最小验收"],
            )
        )

        contracts = [
            ("required inputs", required_inputs, manifest.get("inputs", [])),
            ("optional inputs", optional_inputs, manifest.get("optional_inputs", [])),
            ("outputs", outputs, manifest.get("outputs", [])),
            ("dependencies", dependencies, manifest.get("dependencies", [])),
        ]
        for label, markdown_values, manifest_values in contracts:
            if set(markdown_values) != set(manifest_values):
                errors.append(
                    f"{label} mismatch for {directory.name}: "
                    f"SKILL-only={sorted(set(markdown_values) - set(manifest_values))}, "
                    f"manifest-only={sorted(set(manifest_values) - set(markdown_values))}"
                )

        for dependency in manifest.get("dependencies", []):
            if dependency not in skill_names:
                errors.append(f"Unknown dependency: {directory.name} -> {dependency}")

        for schema_name in manifest.get("shared_schemas", []):
            if schema_name not in schemas:
                errors.append(f"Unknown schema reference: {directory.name} -> {schema_name}")

        review_skill = manifest.get("review_skill")
        if directory.name == "consulting-quality-review":
            if review_skill:
                errors.append("consulting-quality-review must not review itself")
        elif review_skill != "consulting-quality-review":
            errors.append(
                f"Invalid review skill: {directory.name} -> {review_skill}; "
                "expected consulting-quality-review"
            )

        produced_outputs.update(manifest.get("outputs", []))

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit_dependency(skill_name: str, trail: list[str]) -> None:
        if skill_name in visiting:
            errors.append(f"Skill dependency cycle: {' -> '.join(trail + [skill_name])}")
            return
        if skill_name in visited:
            return
        visiting.add(skill_name)
        for dependency in manifests.get(skill_name, {}).get("dependencies", []):
            visit_dependency(dependency, trail + [skill_name])
        visiting.remove(skill_name)
        visited.add(skill_name)

    for skill_name in sorted(manifests):
        visit_dependency(skill_name, [])

    for path in sorted((ROOT / "shared/workflows").glob("*.yaml")):
        workflow = read_yaml(path)
        review_policy = workflow.get("review_policy", {})
        if review_policy.get("after_each_stage") != "consulting-quality-review":
            errors.append(
                f"Workflow missing after-stage quality review: {path.name}"
            )
        if review_policy.get("reviewer_must_be_independent") is not True:
            errors.append(
                f"Workflow does not require reviewer independence: {path.name}"
            )
        if review_policy.get("gate_requires_report") is not True:
            errors.append(
                f"Workflow gate does not require a review report: {path.name}"
            )

        completed_skills: set[str] = set()
        for stage in workflow.get("stages", []):
            for skill_name in stage.get("skills", []):
                if skill_name not in skill_names:
                    errors.append(
                        f"Unknown workflow skill: {path.name}/{stage.get('id')} -> {skill_name}"
                    )
                    continue
                if skill_name == "consulting-quality-review":
                    errors.append(
                        f"Quality reviewer must be applied by review_policy, not as a stage skill: "
                        f"{path.name}/{stage.get('id')}"
                    )
                for dependency in manifests.get(skill_name, {}).get("dependencies", []):
                    if dependency not in completed_skills:
                        errors.append(
                            f"Workflow dependency order failure: {path.name}/{stage.get('id')} "
                            f"runs {skill_name} before {dependency}"
                        )
                completed_skills.add(skill_name)
            for artifact in stage.get("required_architecture_outputs", []):
                if artifact not in produced_outputs:
                    errors.append(
                        f"Workflow requires an unproduced artifact: "
                        f"{path.name}/{stage.get('id')} -> {artifact}"
                    )
            completed_skills.add("consulting-quality-review")

    file_count = sum(1 for path in ROOT.rglob("*") if path.is_file())
    print(
        f"Validated {file_count} files, {len(schemas)} schemas, "
        f"{len(skill_names)} skills, {len(list((ROOT / 'shared/workflows').glob('*.yaml')))} workflows."
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"Validation failed with {len(errors)} error(s).", file=sys.stderr)
        return 1

    print("Validation passed with 0 errors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
