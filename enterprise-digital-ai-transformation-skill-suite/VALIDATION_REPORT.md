# Validation Report

- **Package**: Enterprise Digital & AI Transformation Skill Suite
- **Version**: 1.2.0 — runtime contracts hardened
- **Validation date**: 2026-09-01
- **Command**: `/tmp/dtx-skill-suite-verify/bin/python scripts/validate_suite.py`

## Result

- Files checked: 76
- JSON Schemas: 11
- Skills: 17
- Workflows: 3
- Validation errors: 0

## Automated checks

1. All JSON and YAML files parse successfully.
2. All schemas pass JSON Schema Draft 2020-12 meta-validation.
3. JSON and YAML Target 4A package examples validate against `four-a-architecture-package.schema.json`.
4. The sample `architecture_framework_profile` validates against `architecture-framework-profile.schema.json`.
5. Every Skill directory name matches its Manifest name.
6. Every `SKILL.md` version matches its Manifest version.
7. Required inputs, optional inputs, outputs and dependencies are consistent between `SKILL.md` and `manifest.yaml`.
8. All Skill dependencies and shared Schema references resolve.
9. All Workflow Skill references and required 4A outputs resolve to declared Skill outputs.
10. Task Card、Quality Review Report 与 Slide Content Pack 示例通过对应 Schema。
11. Skill 依赖无环，Workflow 内依赖顺序正确，Reviewer 不得自审。
12. Full、Rapid、AI-First 均要求逐阶段独立质量报告。
13. 4A Package 与 Slide Content Pack 的 `artifact_header` 单独通过 Artifact Header Schema。

## Enforced 4A invariants

- Enterprise Architecture domains are fixed to BA, IA, AA and TA.
- TOGAF Data Architecture is represented internally as IA Information Architecture.
- Operating Model and BA reuse the same Value Stream, Capability, Process, Organization, Governance and KPI Node IDs.
- Integration, Security & Trust, AI & Knowledge, NFR & Resilience and Architecture Governance are cross-cutting views rather than additional architecture domains.
- As-Is, To-Be and Transition Architecture are separate states.
- AA objects require BA and IA traceability; TA objects require AA/IA/NFR traceability.
- Roadmap Waves consume Transition Architecture rather than only a project list.
- PPT generation consumes approved artifacts and cannot create new architecture facts.
- 4A 类型页面必须声明 `architecture_domains` 与 `architecture_view_ids`，并声明至少一种输出格式。

## Scope of validation

This report verifies structural and contract consistency. It does not replace domain-expert review of a real client's strategy, process design, architecture decisions, estimates or transformation priorities. Those remain subject to Evidence rules and Gates G0-G8.
