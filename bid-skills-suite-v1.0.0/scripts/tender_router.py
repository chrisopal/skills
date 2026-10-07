#!/usr/bin/env python3
"""Build an evidence-bound tender classification brief and routing candidate.

The host/model performs semantic classification after ``brief``.  This script
does not call a model and never turns a candidate into an approved project fact.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError as exc:  # pragma: no cover - the suite declares jsonschema
    raise RuntimeError("tender_router需要jsonschema") from exc


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "assets/tender-routing/catalog.json"
DECISION_SCHEMA_PATH = ROOT / "assets/tender-routing/decision.schema.json"
CATEGORIES = {
    "construction",
    "hardware_supply",
    "software_integration",
    "service_outsourcing",
}
TENDER_ROLES = {"main", "technical", "commercial", "clarification", "addendum"}
BRIEF_ARTIFACT_ID = "ART-02-TENDER-ROUTING-BRIEF"
ROUTE_ARTIFACT_ID = "ART-02-TENDER-ROUTING"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"JSON读取失败：{path}") from exc


def _project_root(project: str | os.PathLike[str]) -> Path:
    root = Path(project).expanduser().resolve()
    if not root.is_dir():
        raise ValueError("项目目录不存在")
    return root


def safe_project_path(project: Path, value: str | os.PathLike[str], *, label: str, must_exist: bool = False) -> Path:
    """Resolve a path while rejecting traversal and symlink escapes."""

    raw = Path(value).expanduser()
    if ".." in raw.parts:
        raise ValueError(f"{label}路径包含越界片段")
    candidate = raw if raw.is_absolute() else project / raw
    resolved = candidate.resolve()
    if not resolved.is_relative_to(project):
        raise ValueError(f"{label}路径越界或符号链接指向项目外")
    if must_exist and not resolved.is_file():
        raise ValueError(f"{label}不存在或不是文件")
    return resolved


def _write_new(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError("输出已存在，请使用新的产物路径/版本")
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except FileExistsError as exc:
        raise ValueError("输出已存在，请使用新的产物路径/版本") from exc


def _project_id(project: Path) -> str:
    metadata = safe_project_path(project, "work/project.json", label="项目元数据", must_exist=True)
    value = _read_json(metadata).get("project_id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("项目元数据缺少project_id")
    return value


def _load_source_registry(project: Path) -> dict[str, dict[str, Any]]:
    path = safe_project_path(
        project,
        "inputs/source-registry.json",
        label="来源登记表",
        must_exist=True,
    )
    value = _read_json(path)
    if not isinstance(value, dict) or not isinstance(value.get("sources"), list):
        raise ValueError("来源登记表结构无效")
    sources: dict[str, dict[str, Any]] = {}
    for source in value["sources"]:
        if not isinstance(source, dict):
            raise ValueError("来源登记表条目无效")
        source_id = source.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("来源登记表缺少source_id")
        if source_id in sources:
            raise ValueError("来源登记表存在重复source_id：" + source_id)
        if not isinstance(source.get("relative_path"), str) or not source["relative_path"].strip():
            raise ValueError("来源登记表缺少relative_path：" + source_id)
        if not isinstance(source.get("sha256"), str):
            raise ValueError("来源登记表缺少sha256：" + source_id)
        if (
            not isinstance(source.get("revision"), int)
            or isinstance(source["revision"], bool)
            or source["revision"] < 1
        ):
            raise ValueError("来源登记表缺少有效revision：" + source_id)
        if not isinstance(source.get("bytes"), int) or isinstance(source["bytes"], bool) or source["bytes"] < 0:
            raise ValueError("来源登记表缺少有效bytes：" + source_id)
        if source.get("role") not in TENDER_ROLES | {"supplier", "unknown"}:
            raise ValueError("来源登记表角色无效：" + source_id)
        sources[source_id] = source
    return sources


def _load_catalog() -> tuple[dict[str, Any], str]:
    catalog = _read_json(CATALOG_PATH)
    if not isinstance(catalog, dict) or not isinstance(catalog.get("templates"), list):
        raise ValueError("路由目录结构无效")
    template_categories_list = [
        item.get("category") for item in catalog["templates"] if isinstance(item, dict)
    ]
    if any(not isinstance(category, str) for category in template_categories_list):
        raise ValueError("路由目录存在无效category")
    if len(template_categories_list) != len(set(template_categories_list)):
        raise ValueError("路由目录存在重复category")
    template_categories = set(template_categories_list)
    if template_categories != CATEGORIES:
        raise ValueError("路由目录必须恰好包含四个基础类别模板")
    return catalog, sha256(CATALOG_PATH)


def _load_decision_schema() -> dict[str, Any]:
    schema = _read_json(DECISION_SCHEMA_PATH)
    if not isinstance(schema, dict):
        raise ValueError("决策schema结构无效")
    return schema


def _validate_schema(value: dict[str, Any], schema: dict[str, Any]) -> None:
    errors = sorted(
        Draft202012Validator(schema).iter_errors(value),
        key=lambda error: tuple(str(part) for part in error.path),
    )
    if errors:
        details = "; ".join(
            f"{'.'.join(str(part) for part in error.path) or '$'}: {error.message}"
            for error in errors[:8]
        )
        raise ValueError(f"分类决策不符合schema：{details}")


def _normalize(value: str) -> str:
    return "".join(value.split())


def _source_readiness(intake: dict[str, Any]) -> tuple[dict[str, Any], list[str], list[str]]:
    data = intake.get("data") if isinstance(intake.get("data"), dict) else {}
    coverage = data.get("coverage", "unknown")
    warnings = list(intake.get("warnings") or [])
    blockers = list(intake.get("blockers") or [])
    if coverage in {"partial", "unknown"}:
        warnings.append(f"原文覆盖为{coverage}；路由候选保留该缺口，不能视为完整读取。")
    readiness = {
        "status": intake.get("status", "unknown"),
        "coverage": coverage,
        "partial": coverage != "complete",
        "warnings": warnings,
        "blockers": blockers,
    }
    return readiness, warnings, blockers


def _validate_intake(project: Path, intake_path: Path) -> tuple[dict[str, Any], str, dict[str, Any]]:
    intake = _read_json(intake_path)
    if not isinstance(intake, dict):
        raise ValueError("intake必须是JSON对象")
    expected_project = _project_id(project)
    if intake.get("project_id") != expected_project:
        raise ValueError("intake项目与工作目录不一致")
    if not isinstance(intake.get("artifact_id"), str) or not intake["artifact_id"].strip():
        raise ValueError("intake缺少artifact_id")
    if (
        not isinstance(intake.get("revision"), int)
        or isinstance(intake["revision"], bool)
        or intake["revision"] < 1
    ):
        raise ValueError("intake缺少有效revision")
    inputs = intake.get("inputs")
    if not isinstance(inputs, list):
        raise ValueError("intake缺少inputs来源哈希清单")
    data = intake.get("data")
    if not isinstance(data, dict):
        raise ValueError("intake缺少data")
    registry = _load_source_registry(project)
    documents = data.get("documents")
    if not isinstance(documents, list):
        raise ValueError("intake缺少data.documents来源清单")
    document_by_id: dict[str, dict[str, Any]] = {}
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("intake.documents条目无效")
        source_id = document.get("source_id")
        if not isinstance(source_id, str) or not source_id.strip():
            raise ValueError("intake.documents缺少source_id")
        if source_id in document_by_id:
            raise ValueError("intake.documents存在重复source_id：" + source_id)
        if not isinstance(document.get("relative_path"), str) or not document["relative_path"].strip():
            raise ValueError("intake.documents缺少relative_path：" + source_id)
        if not isinstance(document.get("sha256"), str):
            raise ValueError("intake.documents缺少sha256：" + source_id)
        if (
            not isinstance(document.get("revision"), int)
            or isinstance(document["revision"], bool)
            or document["revision"] < 1
        ):
            raise ValueError("intake.documents缺少有效revision：" + source_id)
        if document.get("role") not in TENDER_ROLES | {"supplier", "unknown"}:
            raise ValueError("intake.documents角色无效：" + source_id)
        authoritative = registry.get(source_id)
        if authoritative is None:
            raise ValueError("intake.documents来源未登记：" + source_id)
        for field in ("relative_path", "sha256", "revision", "role", "bytes"):
            if document.get(field) != authoritative.get(field):
                raise ValueError(f"来源{source_id}的{field}与source-registry不一致")
        document_by_id[source_id] = document

    if inputs:
        input_by_id: dict[str, dict[str, Any]] = {}
        for row in inputs:
            if not isinstance(row, dict) or not isinstance(row.get("artifact_id"), str):
                raise ValueError("intake.inputs缺少artifact_id")
            source_id = row["artifact_id"]
            if not source_id.strip():
                raise ValueError("intake.inputs的artifact_id不能为空")
            if source_id in input_by_id:
                raise ValueError("intake.inputs存在重复artifact_id：" + source_id)
            if not isinstance(row.get("relative_path"), str) or not row["relative_path"].strip():
                raise ValueError("intake.inputs缺少relative_path：" + source_id)
            if not isinstance(row.get("sha256"), str):
                raise ValueError("intake.inputs缺少sha256：" + source_id)
            if (
                not isinstance(row.get("revision"), int)
                or isinstance(row["revision"], bool)
                or row["revision"] < 1
            ):
                raise ValueError("intake.inputs缺少有效revision：" + source_id)
            input_by_id[source_id] = row
        if set(input_by_id) != set(document_by_id):
            raise ValueError("intake.inputs与data.documents来源集合不一致")
        for source_id, document in document_by_id.items():
            row = input_by_id[source_id]
            for field in ("relative_path", "sha256", "revision"):
                if row.get(field) != document.get(field):
                    raise ValueError(f"来源{source_id}的{field}与data.documents不一致")
    elif not documents:
        raise ValueError("intake缺少来源哈希清单")

    seen_paths: set[str] = set()
    for source_id, document in document_by_id.items():
        relative_path = document["relative_path"]
        if relative_path in seen_paths:
            raise ValueError("intake来源路径重复：" + relative_path)
        seen_paths.add(relative_path)
        source_path = safe_project_path(project, relative_path, label="intake来源", must_exist=True)
        if (
            sha256(source_path) != document["sha256"]
            or source_path.stat().st_size != document["bytes"]
        ):
            raise ValueError(f"原件身份已变化：{source_id}")

    blocks = data.get("blocks")
    if not isinstance(blocks, list):
        raise ValueError("intake缺少data.blocks原文块")
    for block in blocks:
        if not isinstance(block, dict) or not all(
            isinstance(block.get(key), str) and block[key]
            for key in ("source_id", "location")
        ):
            raise ValueError("intake原文块缺少source_id/location")
        if block["source_id"] not in document_by_id:
            raise ValueError("原文块引用了未登记来源：" + block["source_id"])
        if not isinstance(block.get("text"), str):
            raise ValueError("intake原文块text必须是字符串")

    source_inventory = [
        {
            "source_id": source_id,
            "relative_path": document["relative_path"],
            "sha256": document["sha256"],
            "revision": document["revision"],
            "role": document["role"],
            "client_tender_basis": document["role"] in TENDER_ROLES,
        }
        for source_id, document in document_by_id.items()
    ]
    source_roles = {item["source_id"]: item["role"] for item in source_inventory}
    tender_block_count = sum(
        1 for block in blocks if source_roles[block["source_id"]] in TENDER_ROLES
    )
    readiness, warnings, blockers = _source_readiness(intake)
    if tender_block_count == 0:
        message = "没有可作为客户招标依据的tender原文块；supplier/unknown来源不能支持分类。"
        warnings.append(message)
        blockers.append(message)
    readiness.update(
        {
            "source_inventory": source_inventory,
            "tender_block_count": tender_block_count,
            "client_tender_source_ids": sorted(
                source_id for source_id, role in source_roles.items() if role in TENDER_ROLES
            ),
        }
    )
    readiness["warnings"] = warnings
    readiness["blockers"] = blockers
    return intake, sha256(intake_path), readiness


def _next_revision(project: Path, artifact_id: str, explicit: int | None) -> int:
    highest = 0
    for directory_name in ("work", "artifacts", "reviews"):
        directory = project / directory_name
        if not directory.is_dir():
            continue
        for path in directory.rglob("*.json"):
            if path.is_symlink():
                continue
            try:
                value = _read_json(path)
            except ValueError:
                continue
            if not isinstance(value, dict) or value.get("artifact_id") != artifact_id:
                continue
            if value.get("project_id") != _project_id(project):
                raise ValueError("同artifact_id产物属于其他项目")
            revision = value.get("revision")
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                raise ValueError("同artifact_id产物revision无效")
            highest = max(highest, revision)
    if explicit is not None:
        if isinstance(explicit, bool) or explicit < 1 or explicit <= highest:
            raise ValueError("revision必须大于当前最高revision")
        return explicit
    return highest + 1


def _catalog_snapshot(catalog: dict[str, Any], catalog_hash: str, templates: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "catalog_id": catalog["catalog_id"],
        "catalog_version": catalog["catalog_version"],
        "sha256": catalog_hash,
        "source_kind": catalog.get("source_kind", "instruction_catalog_only"),
        "classification": copy.deepcopy(catalog["classification"]),
        "common_extraction_plan": copy.deepcopy(catalog["common_extraction_plan"]),
        "templates": copy.deepcopy(templates if templates is not None else catalog["templates"]),
    }


def _context(project_arg: str | os.PathLike[str], intake_arg: str | os.PathLike[str]) -> tuple[Path, Path, dict[str, Any], str, dict[str, Any], dict[str, Any], str]:
    project = _project_root(project_arg)
    intake_path = safe_project_path(project, intake_arg, label="intake", must_exist=True)
    intake, intake_hash, readiness = _validate_intake(project, intake_path)
    catalog, catalog_hash = _load_catalog()
    return project, intake_path, intake, intake_hash, readiness, catalog, catalog_hash


def _artifact_input(project: Path, path: Path, artifact_id: str, revision: int, file_hash: str) -> dict[str, Any]:
    return {
        "artifact_id": artifact_id,
        "revision": revision,
        "relative_path": path.relative_to(project).as_posix(),
        "sha256": file_hash,
    }


def _annotated_blocks(intake: dict[str, Any]) -> list[dict[str, Any]]:
    documents = intake["data"]["documents"]
    roles = {document["source_id"]: document["role"] for document in documents}
    return [
        {
            **copy.deepcopy(block),
            "source_role": roles[block["source_id"]],
            "client_tender_basis": roles[block["source_id"]] in TENDER_ROLES,
        }
        for block in intake["data"]["blocks"]
    ]


def build_brief(
    project_arg: str | os.PathLike[str],
    intake_arg: str | os.PathLike[str],
    out_arg: str | os.PathLike[str],
    *,
    revision: int | None = None,
) -> dict[str, Any]:
    project, intake_path, intake, intake_hash, readiness, catalog, catalog_hash = _context(project_arg, intake_arg)
    out = safe_project_path(project, out_arg, label="brief输出")
    result = {
        "schema_version": "1.0",
        "skill_id": "bid-project-profile",
        "artifact_id": BRIEF_ARTIFACT_ID,
        "revision": _next_revision(project, BRIEF_ARTIFACT_ID, revision),
        "created_at": _now(),
        "project_id": _project_id(project),
        "status": "needs_review",
        "inputs": [
            _artifact_input(
                project,
                intake_path,
                intake["artifact_id"],
                intake["revision"],
                intake_hash,
            )
        ],
        "intake_sha256": intake_hash,
        "catalog_sha256": catalog_hash,
        "source_readiness": readiness,
        "source_inventory": copy.deepcopy(readiness["source_inventory"]),
        "source_blocks": _annotated_blocks(intake),
        "classification_blocks": [
            block for block in _annotated_blocks(intake) if block["client_tender_basis"]
        ],
        "catalog": _catalog_snapshot(catalog, catalog_hash),
        "decision_contract": _load_decision_schema(),
        "scope": {
            "included": ["按标包判断四类基础采购范围", "为基础信息、需求、评分和否决抽取选择指导模板"],
            "excluded": ["项目事实确认", "法规适用性判断", "投标响应承诺", "人工批准"],
            "boundary": "仅供宿主读取原文后生成候选分类；unknown必须保留并由后续人工/宿主流程处理。",
        },
        "warnings": readiness["warnings"],
        "blockers": readiness["blockers"],
    }
    _write_new(out, result)
    return result


def _validate_evidence(
    evidence: dict[str, Any],
    blocks: list[dict[str, Any]],
    source_roles: dict[str, str],
    label: str,
) -> None:
    if not isinstance(evidence, dict) or set(evidence) != {"source_id", "location", "quote"}:
        raise ValueError(f"{label}证据字段无效")
    source_id, location, quote = evidence["source_id"], evidence["location"], evidence["quote"]
    if not all(isinstance(value, str) and value.strip() for value in (source_id, location, quote)):
        raise ValueError(f"{label}证据字段不能为空")
    if source_roles.get(source_id) not in TENDER_ROLES:
        raise ValueError(f"{label}证据不能来自supplier/unknown来源：{source_id}")
    candidates = [block for block in blocks if block.get("source_id") == source_id and block.get("location") == location]
    if not candidates:
        raise ValueError(f"{label}证据未找到原文位置：{source_id}/{location}")
    normalized_quote = _normalize(quote)
    if not normalized_quote or not any(normalized_quote in _normalize(block.get("text", "")) for block in candidates):
        raise ValueError(f"{label}证据quote不是该原文块的连续文字：{source_id}/{location}")


def _validate_decision(
    decision: dict[str, Any],
    project: Path,
    intake: dict[str, Any],
    intake_hash: str,
    catalog_hash: str,
) -> None:
    _validate_schema(decision, _load_decision_schema())
    expected_project = _project_id(project)
    if decision["project_id"] != expected_project:
        raise ValueError("分类决策项目与工作目录不一致")
    if decision["intake_sha256"] != intake_hash:
        raise ValueError("分类决策未绑定当前intake")
    if decision["catalog_sha256"] != catalog_hash:
        raise ValueError("分类决策未绑定当前catalog")
    blocks = intake["data"]["blocks"]
    source_roles = {
        document["source_id"]: document["role"] for document in intake["data"]["documents"]
    }
    for index, evidence in enumerate(decision["lot_structure_evidence"]):
        _validate_evidence(evidence, blocks, source_roles, f"标包结构[{index}]")
    lots = decision["lots"]
    lot_ids: set[str] = set()
    for lot_index, lot in enumerate(lots):
        lot_label = f"标包[{lot_index}]"
        if lot["lot_id"] in lot_ids:
            raise ValueError("标包lot_id重复：" + lot["lot_id"])
        lot_ids.add(lot["lot_id"])
        if not lot["lot_name"].strip():
            raise ValueError(lot_label + "lot_name不能为空")
        categories: set[str] = set()
        for component_index, component in enumerate(lot["components"]):
            category = component["category"]
            if category not in CATEGORIES:
                raise ValueError("不支持的基础类别：" + str(category))
            if category in categories:
                raise ValueError(f"{lot_label}基础类别重复：{category}")
            categories.add(category)
            if not component["rationale"].strip():
                raise ValueError(f"{lot_label}类别{category}缺少rationale")
            for evidence_index, evidence in enumerate(component["evidence"]):
                _validate_evidence(
                    evidence,
                    blocks,
                    source_roles,
                    f"{lot_label}类别{category}证据[{evidence_index}]",
                )
        expected_mode = "single" if len(categories) == 1 else "mixed" if len(categories) >= 2 else "unknown"
        if lot["mode"] != expected_mode:
            raise ValueError(f"{lot_label}mode与components数量不一致，应为{expected_mode}")
        if expected_mode == "unknown" and not any(value.strip() for value in lot["unknowns"]):
            raise ValueError(f"{lot_label}未分类时必须填写unknowns原因")
        scenario_tags = set(lot["scenario_tags"])
        scenario_evidence_tags: set[str] = set()
        for scenario_index, scenario in enumerate(lot["scenario_evidence"]):
            tag = scenario["tag"]
            if tag in scenario_evidence_tags:
                raise ValueError(f"{lot_label}scenario_evidence标签重复：{tag}")
            scenario_evidence_tags.add(tag)
            if tag not in scenario_tags:
                raise ValueError(f"{lot_label}scenario_evidence标签未列入scenario_tags：{tag}")
            if not scenario["rationale"].strip():
                raise ValueError(f"{lot_label}场景标签{tag}缺少rationale")
            for evidence_index, evidence in enumerate(scenario["evidence"]):
                _validate_evidence(
                    evidence,
                    blocks,
                    source_roles,
                    f"{lot_label}场景{tag}证据[{evidence_index}]",
                )
        if scenario_evidence_tags != scenario_tags:
            raise ValueError(f"{lot_label}scenario_evidence与scenario_tags不一致")
    structure = decision["lot_structure"]
    if structure == "single":
        if len(lots) != 1:
            raise ValueError("single lot_structure必须恰好包含一个标包")
        if not decision["lot_structure_evidence"]:
            raise ValueError("single lot_structure必须提供原文范围依据；无法确认时应使用unknown")
    elif structure == "multiple":
        if len(lots) < 2:
            raise ValueError("multiple lot_structure至少需要两个标包")
        if not decision["lot_structure_evidence"]:
            raise ValueError("multiple lot_structure必须提供原文证据")


def _template_by_category(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {template["category"]: template for template in catalog["templates"]}


def compose_route(
    project_arg: str | os.PathLike[str],
    intake_arg: str | os.PathLike[str],
    decision_arg: str | os.PathLike[str],
    out_arg: str | os.PathLike[str],
    *,
    revision: int | None = None,
) -> dict[str, Any]:
    project, intake_path, intake, intake_hash, readiness, catalog, catalog_hash = _context(project_arg, intake_arg)
    decision_path = safe_project_path(project, decision_arg, label="分类决策", must_exist=True)
    decision = _read_json(decision_path)
    if not isinstance(decision, dict):
        raise ValueError("分类决策必须是JSON对象")
    _validate_decision(decision, project, intake, intake_hash, catalog_hash)
    out = safe_project_path(project, out_arg, label="路由输出")
    decision_hash = sha256(decision_path)
    by_category = _template_by_category(catalog)
    lots: list[dict[str, Any]] = []
    all_selected: dict[str, dict[str, Any]] = {}
    for lot in decision["lots"]:
        selected = [copy.deepcopy(by_category[component["category"]]) for component in lot["components"]]
        for template in selected:
            all_selected[template["category"]] = copy.deepcopy(template)
        lots.append(
            {
                "lot_id": lot["lot_id"],
                "lot_name": lot["lot_name"],
                "mode": lot["mode"],
                "components": copy.deepcopy(lot["components"]),
                "scenario_tags": copy.deepcopy(lot["scenario_tags"]),
                "scenario_evidence": copy.deepcopy(lot["scenario_evidence"]),
                "unknowns": copy.deepcopy(lot["unknowns"]),
                "selected_templates": selected,
            }
        )
    warnings = list(readiness["warnings"])
    blockers = list(readiness["blockers"])
    if decision["lot_structure"] == "unknown":
        blockers.append("标包结构仍为unknown，不能视为完整分类。")
    for lot in decision["lots"]:
        if lot["mode"] == "unknown":
            blockers.append(f"标包{lot['lot_id']}的基础类别仍为unknown：" + "；".join(lot["unknowns"]))
    result = {
        "schema_version": "1.0",
        "skill_id": "bid-project-profile",
        "artifact_id": ROUTE_ARTIFACT_ID,
        "revision": _next_revision(project, ROUTE_ARTIFACT_ID, revision),
        "created_at": _now(),
        "project_id": _project_id(project),
        "status": "needs_review",
        "review_required": True,
        "inputs": [
            _artifact_input(
                project,
                intake_path,
                intake["artifact_id"],
                intake["revision"],
                intake_hash,
            ),
            _artifact_input(
                project,
                decision_path,
                "HOST-CLASSIFICATION",
                1,
                decision_hash,
            ),
        ],
        "intake_sha256": intake_hash,
        "catalog_sha256": catalog_hash,
        "decision_sha256": decision_hash,
        "decision_path": decision_path.relative_to(project).as_posix(),
        "classification": copy.deepcopy(decision),
        "source_readiness": readiness,
        "source_inventory": copy.deepcopy(readiness["source_inventory"]),
        "catalog": _catalog_snapshot(catalog, catalog_hash),
        "selected_template_categories": sorted(all_selected),
        "lots": lots,
        "extraction_plan": {
            "source_kind": "instruction",
            "notice": "common/domain字段是抽取指导，不是项目事实；事实必须由后续技能从当前intake回读。",
            "common": copy.deepcopy(catalog["common_extraction_plan"]),
            "per_lot": [
                {
                    "lot_id": lot["lot_id"],
                    "templates": [copy.deepcopy(by_category[item["category"]]) for item in lot["components"]],
                }
                for lot in decision["lots"]
            ],
        },
        "scope": {
            "included": ["按已提供原文证据选择标包类别", "为basic_info、requirements、scoring、disqualification保留共同指导", "为每个标包冻结选中的领域模板"],
            "excluded": ["确认采购事实", "确认资格或否决条件适用性", "确认法律后果", "批准分类或投标响应"],
            "boundary": "这是可复核的needs_review路由候选；source_readiness、unknowns和blockers必须由下游保留。",
        },
        "warnings": warnings,
        "blockers": blockers,
    }
    _write_new(out, result)
    return result


# Short names keep the two host-facing operations convenient to import.
brief = build_brief
route = compose_route


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    brief_parser = subparsers.add_parser("brief", help="生成供宿主/模型读取的分类简报")
    brief_parser.add_argument("--project", required=True)
    brief_parser.add_argument("--intake", required=True)
    brief_parser.add_argument("--out", required=True)
    brief_parser.add_argument("--revision", type=int)
    route_parser = subparsers.add_parser("route", help="校验宿主分类并组合冻结模板")
    route_parser.add_argument("--project", required=True)
    route_parser.add_argument("--intake", required=True)
    route_parser.add_argument("--decision", required=True)
    route_parser.add_argument("--out", required=True)
    route_parser.add_argument("--revision", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "brief":
            result = build_brief(args.project, args.intake, args.out, revision=args.revision)
        else:
            result = compose_route(args.project, args.intake, args.decision, args.out, revision=args.revision)
        print(json.dumps({"output": args.out, "artifact_id": result["artifact_id"], "revision": result["revision"], "status": result["status"]}, ensure_ascii=False))
        return 0
    except (OSError, TypeError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
