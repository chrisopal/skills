#!/usr/bin/env python3
"""Mechanical host-agent scoring support.

The host agent supplies semantic scores.  This module only freezes project
inputs, checks exact evidence/arithmetic bindings, and renders a supplied
result.  It never calls a model and never invents a score.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import html
import json
import math
import os
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

import bidkit
import review_checks

SKILL_ID = "bid-review-remediation"
ARTIFACT_TYPE = "ai_expert_scoring"
SCORING_FILE = "artifacts/04-scoring.json"
REVIEW_FILE = "reviews/15-review.json"
SCOPES = {"full", "limited"}
STATUSES = {"scored", "unknown", "not_reviewed", "not_applicable"}
SCORING_TYPES = {"subjective", "objective", "price"}
CONFIDENCES = {"high", "medium", "low"}
SEMANTIC_STATES = {"NOT_RUN", "COMPLETED"}
EVIDENCE_MODES = {"real_documents", "synthetic_test"}
DISCLAIMER = (
    "AI模拟评分，非官方评审。仅记录宿主Agent提供的候选结果；脚本不推断、不认证专家语义，"
    "不替代人工评审、资格审查、否决条件或交付门禁。"
)


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _num(value):
    """Return JSON-friendly numbers while rejecting bool/NaN/Infinity."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("数值必须是有限整数或小数")
    if not math.isfinite(value):
        raise ValueError("不接受NaN或Infinity")
    return value


def _decimal(value, field: str) -> Decimal:
    _num(value)
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field}不是有效数值") from exc
    if not result.is_finite():
        raise ValueError(f"{field}不是有限数值")
    return result


def _same_number(a, b) -> bool:
    try:
        return _decimal(a, "数值") == _decimal(b, "数值")
    except ValueError:
        return False


def _canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _source_key(value) -> str:
    return _canonical({k: value.get(k) for k in (
        "source_id", "revision", "sha256", "location", "quote", "kind")})


def _review_binding(project: Path):
    path = bidkit.safe(project, REVIEW_FILE)
    if not path.is_file():
        return None
    value = bidkit.read(path)
    if value.get("project_id") != bidkit.project_id(project):
        raise ValueError("15-review.json项目身份不一致")
    return {
        "relative_path": REVIEW_FILE,
        "sha256": bidkit.digest(path),
        "artifact_id": value.get("artifact_id"),
        "revision": value.get("revision"),
        "release_recommendation": value.get("data", {}).get("release_recommendation"),
        "review_scope": value.get("data", {}).get("review_scope"),
    }


def _inventory(project: Path):
    files = bidkit.scan_content(project)
    return files, bidkit.canonical(files)


def _load_scoring(project: Path):
    path = bidkit.safe(project, SCORING_FILE)
    payload = bidkit.read(path)
    pid = bidkit.project_id(project)
    if payload.get("project_id") != pid:
        raise ValueError("04-scoring.json项目身份不一致")
    data = payload.get("data") or {}
    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("04-scoring.json缺少data.items")
    by_id = {}
    errors = []
    for row in items:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            errors.append("04评分节点缺少有效ID")
            continue
        ident = row["id"]
        if ident in by_id:
            errors.append(f"04评分ID重复：{ident}")
        by_id[ident] = row
    for row in items:
        if not isinstance(row, dict):
            continue
        parent = row.get("parent_id")
        if parent and parent not in by_id:
            errors.append(f"{row.get('id')}: 父ID不存在：{parent}")
        seen = set()
        current = row
        while isinstance(current, dict) and current.get("parent_id"):
            ident = current.get("id")
            if ident in seen:
                errors.append(f"{row.get('id')}: 评分层级循环")
                break
            seen.add(ident)
            current = by_id.get(current.get("parent_id"))
    if errors:
        raise ValueError("；".join(dict.fromkeys(errors)))
    leaves = [row for row in items if row.get("node_type") == "scored"]
    if not leaves:
        raise ValueError("未提供计分叶子，请先补读评分办法，不能建立空评分结果")
    if any(row.get("node_type") not in {"rollup", "scored"} for row in items):
        raise ValueError("04评分节点类型无效")
    if any(any(child.get("parent_id") == row["id"] for child in items)
           for row in leaves):
        raise ValueError("计分叶子不能含子项")
    return payload, items, leaves, by_id


def _load_inputs(project: Path):
    """Load scoring plus optional upstream stages without requiring a full review."""
    _load_scoring(project)
    pid = bidkit.project_id(project)
    optional = (("05-compliance.json", ("rules",)),
                ("09-evidence-selection.json", ("materials", "selections")))
    for name, keys in optional:
        path = bidkit.safe(project, f"artifacts/{name}")
        if not path.is_file():
            continue
        payload = bidkit.read(path)
        if payload.get("project_id") != pid:
            raise ValueError(f"{name}: 项目身份不一致")
        data = payload.get("data") or {}
        for key in keys:
            rows = data.get(key)
            if not isinstance(rows, list):
                raise ValueError(f"{name}: 缺少data.{key}")
            if any(not isinstance(row, dict) or not isinstance(row.get("id"), str) for row in rows):
                raise ValueError(f"{name}: {key}包含无效ID")
            ids = [row["id"] for row in rows]
            if len(ids) != len(set(ids)):
                raise ValueError(f"{name}: {key}上游ID重复")
    return _load_scoring(project)


def _infer_type(item: dict) -> str:
    # A warranty may be evidenced in a quotation form without scoring its price.
    value = " ".join(str(item.get(k, "")) for k in ("title", "rule_text")).lower()
    if any(word in value for word in ("价格", "报价", "最低价", "price", "quote")):
        return "price"
    value += " " + str(item.get("evidence_requirements", "")).lower()
    if any(word in value for word in ("公式", "按", "每份", "每项", "每增加", "否则0", "比例", "计算")):
        return "objective"
    return "subjective"


def _summary(rows, items, scope: str, semantic: str, declared_total=None):
    def total_for(status):
        return sum((_decimal(row["max_score"], "max_score") for row in rows
                    if row["status"] == status and row["max_score"] is not None), Decimal(0))

    known = sum((_decimal(row["simulated_score"], "simulated_score") for row in rows
                 if row["status"] == "scored" and row["simulated_score"] is not None), Decimal(0))
    scored_max = total_for("scored")
    unknown_max = total_for("unknown")
    not_reviewed_max = total_for("not_reviewed")
    not_applicable_max = total_for("not_applicable")
    nominal = (_decimal(declared_total, "declared_total")
               if declared_total is not None else
               sum((_decimal(row["max_score"], "max_score") for row in rows
                    if row["max_score"] is not None), Decimal(0)))
    # A scored leaf's cap is already represented by max_score. Only a
    # non-additive rollup can make adding distinct leaves unsafe.
    non_additive = any(item.get("node_type") != "scored" and
                       item.get("aggregation") in {"max", "capped", "manual"}
                       for item in items)
    complete = bool(rows) and scope == "full" and semantic == "COMPLETED" and all(
        row.get("status") == "scored" and row.get("max_score") is not None for row in rows
    )
    metrics = {
        "known_score": _json_number(known),
        "scored_max": _json_number(scored_max),
        "unknown_max": _json_number(unknown_max),
        "not_reviewed_max": _json_number(not_reviewed_max),
        "not_applicable_max": _json_number(not_applicable_max),
        "nominal_max": _json_number(nominal),
    }
    if non_additive:
        metrics = {key: None for key in metrics}
    return {
        "scope": scope,
        **metrics,
        "aggregate_available": bool(complete and not non_additive),
        "computed_total": _json_number(known) if complete and not non_additive else None,
        "aggregate_explanation": (
            "04包含max/capped/manual聚合，保留逐叶分数；脚本不对叶子重复求和。"
            if non_additive else
            "仅在全部叶子已评分且04为简单sum聚合时提供computed_total。"
        ),
    }


def summarize(rows, scoring_payload, scope: str, semantic: str):
    """Public summary helper for a host agent filling a scoring artifact."""
    data = scoring_payload.get("data", scoring_payload) if isinstance(scoring_payload, dict) else {}
    items = data.get("items", []) if isinstance(data, dict) else []
    declared_total = data.get("declared_total") if isinstance(data, dict) else None
    return _summary(rows, items, scope, semantic, declared_total)


def _json_number(value: Decimal):
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def prepare(project, scope: str = "full"):
    project = Path(project).resolve()
    if scope not in SCOPES:
        raise ValueError("scope必须是full或limited")
    from online_review import basis as online_basis
    online = online_basis(project, scope)
    scoring, items, leaves, _ = _load_inputs(project)
    files, fingerprint = _inventory(project)
    review = _review_binding(project)
    rows = []
    for item in leaves:
        maximum = item.get("max_score")
        if maximum is not None:
            _decimal(maximum, f"{item['id']}.max_score")
        rows.append({
            "target_id": item["id"],
            "title": item.get("title", item["id"]),
            "scoring_type": _infer_type(item),
            "evidence_mode": "real_documents",
            "status": "not_reviewed",
            "max_score": maximum,
            "simulated_score": None,
            "range": None,
            "confidence": "low",
            "rationale": "尚未由宿主Agent提供语义评分，脚本不推断得分。",
            "rubric_basis": item.get("rule_text", ""),
            "tender_refs": copy.deepcopy(item.get("sources", [])),
            "bid_refs": [],
            "material_sources": [],
            "deductions": [],
            "calculation_explanation": "",
            "inspection_scope": None,
            "price_inputs": None,
            "limitations": ["尚未执行宿主Agent语义评估。"],
        })
    artifact = {
        "schema_version": "1.0",
        "skill_id": SKILL_ID,
        "artifact_type": ARTIFACT_TYPE,
        "project_id": bidkit.project_id(project),
        "artifact_id": f"ART-AI-SCORING-{bidkit.project_id(project)}",
        "revision": 1,
        "created_at": _now(),
        "status": "draft",
        "scope": scope,
        "semantic_evaluation": "NOT_RUN",
        "inputs": {
            "content_inventory": files,
            "content_fingerprint": fingerprint,
            "scoring": {
                "relative_path": SCORING_FILE,
                "sha256": bidkit.digest(bidkit.safe(project, SCORING_FILE)),
                "artifact_id": scoring.get("artifact_id"),
                "revision": scoring.get("revision"),
            },
            "review": review,
            **({"online_document": online} if online is not None else {}),
        },
        "evaluator": {"kind": "host_agent", "host": None, "model": None},
        "evaluated_at": None,
        "rows": rows,
        "summary": summarize(rows, scoring, scope, "NOT_RUN"),
        "eligibility": _eligibility(project),
        "notice": DISCLAIMER,
    }
    return artifact


def _eligibility(project: Path):
    path = bidkit.safe(project, REVIEW_FILE)
    if not path.is_file():
        return {
            "review_present": False,
            "release_recommendation": None,
            "review_scope": None,
            "independent": True,
            "note": "未发现15-review；评分结果不形成正式交付建议。",
        }
    review = bidkit.read(path)
    data = review.get("data", {})
    return {
        "review_present": True,
        "release_recommendation": data.get("release_recommendation"),
        "review_scope": data.get("review_scope"),
        "independent": True,
        "note": "该评审建议独立显示；模拟评分不会改变评审、资格或交付门禁。",
    }


def _expected_material_sources(project: Path):
    path = bidkit.safe(project, "artifacts/09-evidence-selection.json")
    if not path.is_file():
        return {}
    payload = bidkit.read(path)
    if payload.get("project_id") != bidkit.project_id(project):
        raise ValueError("09-evidence-selection.json: 项目身份不一致")
    materials = (payload.get("data") or {}).get("materials")
    if not isinstance(materials, list):
        raise ValueError("09-evidence-selection.json: 缺少data.materials")
    result = {}
    for material in materials:
        if not isinstance(material, dict):
            raise ValueError("09-evidence-selection.json: materials包含无效对象")
        sources = material.get("sources", [])
        if not isinstance(sources, list):
            raise ValueError("09-evidence-selection.json: material.sources必须是数组")
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("09-evidence-selection.json: material.sources包含无效引用")
            result[_source_key(source)] = source
    return result


def _price_inputs(row):
    value = row.get("price_inputs")
    return value if isinstance(value, dict) else None


def _check_numeric_tree(value, path="$", errors=None):
    errors = errors if errors is not None else []
    if isinstance(value, float) and not math.isfinite(value):
        errors.append(f"{path}: 不接受NaN或Infinity")
    elif isinstance(value, dict):
        for key, child in value.items():
            _check_numeric_tree(child, f"{path}.{key}", errors)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _check_numeric_tree(child, f"{path}[{index}]", errors)
    return errors


def _check_ref_lists(project, row, errors, warnings):
    cache = {}
    tender_refs = row.get("tender_refs")
    if not isinstance(tender_refs, list) or not tender_refs:
        errors.append(f"{row.get('target_id')}: 缺少招标原文引用")
        tender_refs = []
    for reference in tender_refs:
        if not isinstance(reference, dict):
            errors.append(f"{row.get('target_id')}: 招标引用必须是对象")
            continue
        try:
            review_checks.source_text(project, reference, cache)
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            errors.append(f"{row.get('target_id')}: 招标引用无效：{exc}")
    bid_refs = row.get("bid_refs", [])
    if not isinstance(bid_refs, list):
        errors.append(f"{row.get('target_id')}: bid_refs必须是数组")
        bid_refs = []
    for reference in bid_refs:
        if not isinstance(reference, dict):
            errors.append(f"{row.get('target_id')}: 正文引用必须是对象")
            continue
        try:
            review_checks.reference_text(project, reference)
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            errors.append(f"{row.get('target_id')}: 正文引用无效：{exc}")
    allowed_materials = _expected_material_sources(project)
    mode = row.get("evidence_mode")
    if mode not in EVIDENCE_MODES:
        errors.append(f"{row.get('target_id')}: evidence_mode无效")
    material_sources = row.get("material_sources", [])
    if not isinstance(material_sources, list):
        errors.append(f"{row.get('target_id')}: material_sources必须是数组")
        material_sources = []
    for reference in material_sources:
        if not isinstance(reference, dict):
            errors.append(f"{row.get('target_id')}: 材料引用必须是对象")
            continue
        try:
            review_checks.source_text(project, reference, cache)
        except (OSError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
            errors.append(f"{row.get('target_id')}: 材料引用无效：{exc}")
        if _source_key(reference) not in allowed_materials:
            errors.append(f"{row.get('target_id')}: 材料引用未登记在09-evidence-selection材料台账")
        if reference.get("kind") == "synthetic":
            score = row.get("simulated_score")
            try:
                positive = (row.get("status") == "scored" and score is not None and
                            _decimal(score, f"{row.get('target_id')}.simulated_score") > 0)
            except ValueError:
                positive = False
            if positive and mode == "real_documents":
                errors.append(f"{row.get('target_id')}: real_documents模式下模拟材料不能支持正分")
            elif positive and mode == "synthetic_test":
                disclosure = " ".join(str(value) for value in row.get("limitations", []))
                if not any(token in disclosure.lower() for token in ("模拟", "synthetic", "test only")):
                    errors.append(f"{row.get('target_id')}: synthetic_test正分必须披露模拟证据限制")
                else:
                    warnings.append(f"{row.get('target_id')}: 使用synthetic_test材料，仅限测试，不代表真实资格")
            else:
                warnings.append(f"{row.get('target_id')}: 模拟材料仅用于缺口/零分分析，不构成真实资格")
    return tender_refs


def _validate_row(project, row, expected, errors, warnings):
    ident = row.get("target_id")
    if not isinstance(row, dict):
        errors.append("评分行必须是对象")
        return
    if row.get("scoring_type") not in SCORING_TYPES:
        errors.append(f"{ident}: scoring_type无效")
    if _infer_type(expected) == "price" and row.get("scoring_type") != "price":
        errors.append(f"{ident}: 04评分原文明确价格评分，scoring_type必须是price")
    if row.get("status") not in STATUSES:
        errors.append(f"{ident}: status无效")
    if row.get("confidence") not in CONFIDENCES:
        errors.append(f"{ident}: confidence无效")
    expected_title = expected.get("title", ident)
    if row.get("title") != expected_title:
        errors.append(f"{ident}: title必须与04评分节点原文一致")
    if row.get("max_score") != expected.get("max_score") and not _same_number(
            row.get("max_score"), expected.get("max_score")):
        errors.append(f"{ident}: max_score与04评分原文不一致")
    maximum = row.get("max_score")
    if maximum is not None:
        try:
            maximum_d = _decimal(maximum, f"{ident}.max_score")
            if maximum_d < 0:
                errors.append(f"{ident}: max_score不能为负")
        except ValueError as exc:
            errors.append(f"{ident}: {exc}")
            maximum_d = None
    else:
        maximum_d = None
    status = row.get("status")
    score = row.get("simulated_score")
    score_d = None
    if status == "scored":
        if maximum_d is None:
            errors.append(f"{ident}: 无最高分不能标记scored")
        if score is None:
            errors.append(f"{ident}: scored必须提供simulated_score")
        else:
            try:
                score_d = _decimal(score, f"{ident}.simulated_score")
                if score_d < 0 or (maximum_d is not None and score_d > maximum_d):
                    errors.append(f"{ident}: simulated_score超出[0,max_score]")
            except ValueError as exc:
                errors.append(f"{ident}: {exc}")
    elif score is not None:
        errors.append(f"{ident}: {status}不能填写simulated_score")
    value_range = row.get("range")
    if status == "scored":
        if not isinstance(value_range, dict) or "low" not in value_range or "high" not in value_range:
            errors.append(f"{ident}: scored必须提供range.low/high")
        else:
            try:
                low = _decimal(value_range["low"], f"{ident}.range.low")
                high = _decimal(value_range["high"], f"{ident}.range.high")
                if low < 0 or high < low or (maximum_d is not None and high > maximum_d):
                    errors.append(f"{ident}: range超出有效边界")
                if score_d is not None and not low <= score_d <= high:
                    errors.append(f"{ident}: simulated_score不在range内")
            except (KeyError, ValueError) as exc:
                errors.append(f"{ident}: range无效：{exc}")
    elif value_range is not None:
        errors.append(f"{ident}: 未评分行不能提供range")
    rationale = row.get("rationale")
    if not isinstance(rationale, str) or not rationale.strip():
        errors.append(f"{ident}: 缺少rationale")
    tender_refs = _check_ref_lists(project, row, errors, warnings)
    if status == "scored":
        if not isinstance(row.get("rubric_basis"), str) or not row["rubric_basis"].strip():
            errors.append(f"{ident}: scored缺少实际rubric_basis")
        if score_d is not None and score_d > 0 and not (row.get("bid_refs") or row.get("material_sources")):
            errors.append(f"{ident}: 正分必须有实际正文或材料引用")
        deductions = row.get("deductions")
        if not isinstance(deductions, list):
            errors.append(f"{ident}: scored必须提供deductions数组")
        else:
            total = Decimal(0)
            for deduction in deductions:
                if not isinstance(deduction, dict):
                    errors.append(f"{ident}: deduction必须是对象")
                    continue
                try:
                    points = _decimal(deduction.get("points"), f"{ident}.deduction.points")
                    if points < 0:
                        errors.append(f"{ident}: deduction.points不能为负")
                    total += points
                except ValueError as exc:
                    errors.append(f"{ident}: {exc}")
                for key in ("reason", "action"):
                    if not isinstance(deduction.get(key), str) or not deduction[key].strip():
                        errors.append(f"{ident}: deduction缺少{key}")
            if score_d is not None and maximum_d is not None and total != maximum_d - score_d:
                errors.append(f"{ident}: deductions合计必须等于max_score-simulated_score")
        if row.get("scoring_type") in {"objective", "price"}:
            if not isinstance(row.get("calculation_explanation"), str) or not row["calculation_explanation"].strip():
                errors.append(f"{ident}: objective/price scored必须有calculation_explanation")
        if row.get("scoring_type") == "objective":
            scope = row.get("inspection_scope")
            if not isinstance(scope, str) or not scope.strip():
                errors.append(f"{ident}: objective scored必须说明exact inspection_scope")
            criterion_text = " ".join(str(expected.get(key, "")) for key in
                                       ("title", "rule_text", "evidence_requirements"))
            material_like = any(word in criterion_text for word in
                                ("证书", "合同", "业绩", "资质", "营业执照", "验收证明"))
            if score_d is not None and score_d > 0 and material_like and not row.get("material_sources"):
                errors.append(f"{ident}: 客观证书/合同/业绩正分必须有登记材料引用")
        if row.get("scoring_type") == "price":
            basis = _price_inputs(row)
            if not isinstance(basis, dict):
                errors.append(f"{ident}: price scored缺少报价与基准价price_inputs")
            else:
                quote = basis.get("quote")
                base = basis.get("base")
                if quote is None or base is None:
                    errors.append(f"{ident}: price scored必须同时提供quote和base")
                else:
                    try:
                        if _decimal(quote, f"{ident}.quote") <= 0 or _decimal(base, f"{ident}.base") <= 0:
                            errors.append(f"{ident}: quote/base必须大于0")
                    except ValueError as exc:
                        errors.append(f"{ident}: {exc}")
                if not isinstance(basis.get("formula"), str) or not basis["formula"].strip():
                    errors.append(f"{ident}: price_inputs缺少formula")
    else:
        if row.get("deductions") not in ([], None):
            errors.append(f"{ident}: 未评分行不能提供deductions")
    # Keep this local variable intentionally used: exact tender refs are checked above and
    # the caller compares them to the 04 source set.
    return tender_refs


def _parse_time(value):
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def check(project, payload):
    errors = []
    warnings = []
    try:
        project = Path(project).resolve()
        if not isinstance(payload, dict):
            return {"valid": False, "errors": ["评分产物必须是对象"], "summary": {}}
        errors.extend(_check_numeric_tree(payload))
        if payload.get("skill_id") != SKILL_ID:
            errors.append("skill_id必须是bid-review-remediation")
        if payload.get("artifact_type") != ARTIFACT_TYPE:
            errors.append("artifact_type必须是ai_expert_scoring")
        pid = bidkit.project_id(project)
        if payload.get("project_id") != pid:
            errors.append("评分产物项目身份不一致")
        scope = payload.get("scope")
        if scope not in SCOPES:
            errors.append("scope必须是full或limited")
        semantic = payload.get("semantic_evaluation")
        if semantic not in SEMANTIC_STATES:
            errors.append("semantic_evaluation无效")
        if payload.get("status") not in {"draft", "completed", "blocked"}:
            errors.append("评分产物status无效")
        scoring, items, leaves, by_id = _load_inputs(project)
        inputs = payload.get("inputs") or {}
        from online_review import verify as verify_online
        verify_online(project, inputs.get("online_document"), scope, payload.get("rows"))
        files, fingerprint = _inventory(project)
        if inputs.get("content_fingerprint") != fingerprint:
            errors.append("项目内容已新增或变更，评分输入快照过期")
        if inputs.get("content_inventory") != files:
            errors.append("评分产物未冻结当前完整内容清单")
        scoring_binding = inputs.get("scoring") or {}
        current_scoring_digest = bidkit.digest(bidkit.safe(project, SCORING_FILE))
        if scoring_binding.get("sha256") != current_scoring_digest:
            errors.append("04-scoring.json哈希过期或未绑定")
        review = _review_binding(project)
        if inputs.get("review") != review:
            errors.append("15-review.json哈希/身份已变更，评分产物过期")
        expected_ids = [row["id"] for row in leaves]
        rows = payload.get("rows")
        if not isinstance(rows, list):
            errors.append("缺少rows数组")
            rows = []
        ids = [row.get("target_id") for row in rows if isinstance(row, dict)]
        if len(ids) != len(set(ids)):
            errors.append("评分行target_id重复")
        missing = sorted(set(expected_ids) - set(ids))
        extra = sorted(set(ids) - set(expected_ids))
        if missing:
            errors.append("评分叶子漏项：" + ",".join(missing))
        if extra:
            errors.append("存在未知或汇总节点评分行：" + ",".join(extra))
        expected_by = {row["id"]: row for row in leaves}
        for row in rows:
            if not isinstance(row, dict):
                errors.append("评分行必须是对象")
                continue
            ident = row.get("target_id")
            expected = expected_by.get(ident)
            if expected is None:
                continue
            _validate_row(project, row, expected, errors, warnings)
            provided = row.get("tender_refs")
            actual = expected.get("sources", [])
            actual_keys = {_source_key(ref) for ref in actual}
            provided_keys = {_source_key(ref) for ref in provided or []}
            if actual_keys != provided_keys:
                errors.append(f"{ident}: tender_refs必须与04评分节点原文引用完全一致")
        evaluator = payload.get("evaluator")
        if not isinstance(evaluator, dict) or evaluator.get("kind") != "host_agent":
            errors.append("evaluator.kind必须是host_agent")
        if semantic == "NOT_RUN":
            if payload.get("status") != "draft":
                errors.append("semantic_evaluation=NOT_RUN时status必须是draft")
            if any(row.get("status") != "not_reviewed" or row.get("simulated_score") is not None
                   for row in rows if isinstance(row, dict)):
                errors.append("draft不能包含语义评分结果")
            if payload.get("evaluated_at") is not None:
                errors.append("draft不能填写evaluated_at")
        if semantic == "COMPLETED":
            if payload.get("status") not in {"completed", "blocked"}:
                errors.append("COMPLETED时status必须是completed或blocked")
            if not isinstance(evaluator, dict) or not isinstance(evaluator.get("host"), str) or not evaluator.get("host").strip():
                errors.append("COMPLETED必须记录实际evaluator.host")
            if not _parse_time(payload.get("evaluated_at")):
                errors.append("COMPLETED必须记录有效evaluated_at")
            if rows and all(row.get("status") == "not_reviewed" for row in rows if isinstance(row, dict)):
                errors.append("COMPLETED不能把全部评分叶子保留为not_reviewed")
            if scope == "full" and any(row.get("status") == "not_reviewed" for row in rows):
                errors.append("full完整评分不能保留未评项；限定评读请使用limited")
        computed = summarize(rows, scoring, scope or "full", semantic or "NOT_RUN")
        claimed = payload.get("summary")
        if not isinstance(claimed, dict):
            errors.append("缺少summary")
        else:
            summary_keys = ("known_score", "scored_max", "unknown_max", "not_reviewed_max",
                            "not_applicable_max", "nominal_max")
            for key in summary_keys:
                if key not in claimed:
                    errors.append(f"summary缺少{key}")
                    continue
                if ((claimed[key] is None) != (computed[key] is None) or
                        (claimed[key] is not None and not _same_number(claimed[key], computed[key]))):
                    errors.append(f"summary.{key}与逐项状态不一致")
            if claimed.get("scope") != scope:
                errors.append("summary.scope与scope不一致")
            if claimed.get("aggregate_available") != computed["aggregate_available"]:
                errors.append("summary.aggregate_available与机械汇总规则不一致")
            if "computed_total" not in claimed:
                errors.append("summary缺少computed_total")
            elif ((claimed["computed_total"] is None) != (computed["computed_total"] is None) or
                  (claimed["computed_total"] is not None and
                   not _same_number(claimed["computed_total"], computed["computed_total"]))):
                errors.append("summary.computed_total与机械汇总规则不一致")
            if claimed.get("aggregate_explanation") != computed["aggregate_explanation"]:
                errors.append("summary.aggregate_explanation与机械汇总规则不一致")
        eligibility = payload.get("eligibility")
        current_eligibility = _eligibility(project)
        if not isinstance(eligibility, dict) or eligibility.get("independent") is not True:
            errors.append("eligibility必须明确独立于评审门禁")
        elif any(key not in eligibility for key in ("review_present", "release_recommendation", "review_scope")):
            errors.append("eligibility缺少当前15-review绑定字段")
        else:
            for key in ("review_present", "release_recommendation", "review_scope"):
                if eligibility[key] != current_eligibility[key]:
                    errors.append(f"eligibility.{key}与当前15-review绑定不一致")
        if payload.get("notice") != DISCLAIMER:
            errors.append("缺少或修改了模拟评分免责声明")
        result = {
            "valid": not errors,
            "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)),
            "summary": computed,
            "semantic_acceptance": "HOST_AGENT_SUPPLIED_NOT_CERTIFIED_BY_SCRIPT"
            if semantic == "COMPLETED" else "NOT_RUN",
            "eligibility": current_eligibility,
            "current": not any("过期" in error or "变更" in error for error in errors),
            "review_release_independent": True,
        }
        return result
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        errors.append(str(exc))
        return {
            "valid": False,
            "errors": list(dict.fromkeys(errors)),
            "warnings": list(dict.fromkeys(warnings)),
            "summary": {},
            "semantic_acceptance": "NOT_RUN",
            "review_release_independent": True,
        }


def _output_path(project: Path, value, directory: str):
    path = bidkit.safe(project, value)
    if not path.is_relative_to(project / directory):
        raise ValueError(f"输出必须位于项目{directory}目录")
    if path.exists():
        raise ValueError("拒绝覆盖既有输出：" + str(value))
    return path


def _render_document(project, payload, out="reports/ai-scoring.html", *, write=True):
    """Build the report document, optionally persisting it for the CLI."""
    from urllib.parse import quote
    from render_review_report import CSS

    project = Path(project).resolve()
    result = check(project, payload)
    if not result["valid"]:
        raise ValueError("评分产物未通过校验：" + "; ".join(result["errors"]))
    destination = bidkit.safe(project, out)
    if not destination.is_relative_to(project / "reports"):
        raise ValueError(f"输出必须位于项目reports目录：{out}")
    if write and destination.exists():
        raise ValueError("拒绝覆盖既有输出：" + str(out))
    eligibility = result["eligibility"]
    summary = result["summary"]
    evaluated = payload["semantic_evaluation"] == "COMPLETED"
    status_labels = {"scored": "已评分", "unknown": "待核验", "not_reviewed": "未评",
                     "not_applicable": "不适用"}
    type_labels = {"subjective": "主观模拟", "objective": "客观计分", "price": "价格计算"}
    confidence_labels = {"high": "较高", "medium": "中等", "low": "较低"}
    release_labels = {"blocked": "暂不能建议正式交付", "needs_review": "仍需核心复核",
                      "eligible_for_user_release": "交用户决定正式交付", "draft_only": "仅供内部草稿"}
    sources = {row["source_id"]: row for row in
               bidkit.read(project / "inputs/source-registry.json")["sources"]}

    def esc(value):
        return html.escape("" if value is None else str(value), quote=True)

    def number(value):
        return "—" if value is None else str(value)

    def evidence(ref, label):
        relative = ref.get("relative_path") or sources[ref["source_id"]]["relative_path"]
        if write:
            href = quote(os.path.relpath(project / relative, destination.parent), safe="/")
        else:
            href = "/api/file?path=" + quote(relative, safe="")
        return (f'<div class="evidence"><p class="meta">{esc(label)} · '
                f'<a href="{esc(href)}">{esc(Path(relative).name)}</a> · '
                f'{esc(ref.get("location"))}</p><p class="quote">{esc(ref.get("quote"))}</p></div>')

    rows_html = []
    for row in payload["rows"]:
        interval = row.get("range")
        band = (f'{number(interval["low"])}—{number(interval["high"])} 分'
                if interval else "尚无估计区间")
        deductions = "".join(
            f'<li><strong>扣 {esc(number(item["points"]))} 分：</strong>{esc(item["reason"])}'
            f'<p class="action">提升：{esc(item["action"])}</p></li>'
            for item in row.get("deductions", []))
        actions = f'<ul class="issue-list">{deductions}</ul>' if deductions else ""
        refs = "".join(evidence(ref, label) for key, label in
                       (("tender_refs", "招标原文"), ("bid_refs", "当前正文"),
                        ("material_sources", "证明材料")) for ref in row.get(key, []))
        limitations = "；".join(row.get("limitations", []))
        mode = "合成测试材料，仅供模拟" if row["evidence_mode"] == "synthetic_test" else "登记原件，真实性另行核验"
        details = (f'<details><summary>评分依据与证据</summary><p>{esc(row["rubric_basis"])}</p>'
                   f'<p class="meta">{esc(mode)} · 判断可信程度：'
                   f'{esc(confidence_labels[row["confidence"]])}</p>'
                   f'<p>{esc(row.get("calculation_explanation"))}</p>{refs}</details>')
        status_color = "pending" if row["status"] in {"unknown", "not_reviewed"} else "neutral"
        rows_html.append(
            '<tr><td class="criterion"><strong>' + esc(row["title"]) + '</strong>'
            f'<p class="meta">{esc(row["target_id"])} · {esc(type_labels[row["scoring_type"]])}</p></td>'
            f'<td class="score"><strong>{esc(number(row["simulated_score"]))}</strong>'
            f'<span> / {esc(number(row["max_score"]))} 分</span></td>'
            f'<td class="state"><span class="tag {status_color}">{esc(status_labels[row["status"]])}</span>'
            f'<p class="meta">{esc(band)}</p></td>'
            f'<td class="reason"><p>{esc(row["rationale"])}</p>{actions}'
            f'<p class="meta limit">{esc(limitations)}</p>{details}</td></tr>')
    known = f'{number(summary["known_score"])} / {number(summary["scored_max"])}' if evaluated else "待评分"
    metrics = [("已评模拟分 / 已评上限", known), ("待核验上限", number(summary["unknown_max"])),
               ("未评上限", number(summary["not_reviewed_max"])),
               ("原文总分", number(_load_scoring(project)[0]["data"].get("declared_total")))]
    if summary["not_applicable_max"]:
        metrics.append(("不适用项上限", number(summary["not_applicable_max"])))
    counts = "".join(f'<div class="count"><p class="label">{esc(label)}</p>'
                     f'<p><strong>{esc(value)}</strong>{"" if value == "待评分" else "分"}</p></div>' for label, value in metrics)
    scope = "全部评分项" if payload["scope"] == "full" else "限定章节范围"
    if not evaluated:
        phase = "未执行模型评分。此页是空评分计划，空分数不表示零分。"
    elif summary["aggregate_available"]:
        phase = f'模拟合计 {number(summary["computed_total"])} 分，仅对应本轮输入。'
    elif summary["known_score"] is None:
        phase = "原文含封顶、互斥或人工汇总规则，逐项分数暂不形成可用合计。"
    else:
        phase = "含待核验或未评范围，当前仅展示已评小计，不能作为完整标书得分。"
    release = (release_labels.get(eligibility["release_recommendation"], "核心评审结论待核验")
               if eligibility["review_present"] else "尚无核心评审，不能据此交付")
    context = (f'<details class="context"><summary>本次范围与评读记录</summary>'
               f'<p>{esc(payload["notice"])}</p><p class="meta">项目：{esc(payload["project_id"])}'
               f' · 评分版本：{esc(payload["revision"])} · '
               f'宿主：{esc(payload["evaluator"]["host"] or "尚未评读")} · '
               f'模型：{esc(payload["evaluator"]["model"] or "未记录")} · '
               f'评读时间：{esc(payload["evaluated_at"] or "未执行")}</p></details>')
    css = CSS + '''
:root{--ink:#0B1220;--muted:#526075;--line:#D9DEE7;--accent:#0966D9;--canvas:#F5F7FA;--panel:#FFFFFF}
body{background:var(--canvas)}main{width:min(1200px,100%);background:var(--panel)}
.counts{grid-template-columns:repeat(4,minmax(0,1fr));margin:28px 0}.notice{margin:20px 0}
.scores{table-layout:fixed}.criterion{width:21%}.score{width:14%}.state{width:15%}.reason{width:50%}
.score strong{font-size:22px}.score span{font-size:16px;color:var(--muted)}
.scores td,.scores th{padding:16px 12px}.scores th:nth-child(1){width:21%}
.scores th:nth-child(2){width:14%}.scores th:nth-child(3){width:15%}
.meta{font-size:15px}.limit:empty,.reason>p:empty,details>p:empty{display:none}
.action{margin-top:6px}.quote{white-space:pre-wrap}.evidence a{color:var(--accent);text-decoration:underline}
.context{margin-top:16px}summary:focus-visible,a:focus-visible{outline:2px solid var(--accent);outline-offset:4px}
@media(prefers-color-scheme:dark){:root{--ink:#EDF2F9;--muted:#B8C5D8;--line:#35445A;--accent:#80B5FF;--canvas:#101722;--panel:#182230}
.notice,.evidence,th{background:#1B304D}.decision{background:#1B304D}.decision p{color:var(--muted)}.pending{color:#EDC47A}}
@media(max-width:700px){.counts{grid-template-columns:repeat(2,minmax(0,1fr))}
.scores thead{display:none}.scores,.scores tbody{display:block}.scores tr{display:grid;grid-template-columns:1fr 1fr;border-top:1px solid var(--line);padding:20px 0}
.scores td{display:block;width:auto;border:0;padding:8px 0}.criterion,.reason{grid-column:1/-1}.criterion{font-size:20px}
.score span{font-size:15px}.scores .meta{margin-top:4px}.scores .reason{padding-top:16px}}
@media print{:root{--ink:#24323e;--muted:#53616a;--line:#dbe2e5;--accent:#23584d;--panel:white;--canvas:white}
.scores td,.scores th{padding:9pt 6pt}.score strong{font-size:12pt}.score span,.meta{font-size:9.5pt}.scores tr{break-inside:auto}
.notice,.evidence,th,.decision{background:#f7f9f8}.decision p{color:#53616a}}
'''
    document = (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
                f'<meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>AI模拟专家评分</title><link rel="icon" href="data:,"><style>{css}</style></head>'
                f'<body><main><header><p class="eyebrow">投标工作稿 · {esc(scope)}</p>'
                '<h1>AI 模拟专家评分</h1></header>'
                '<p class="notice">AI模拟评分，非官方评审。资格、材料和否决条件按核心评审单独审核。</p>'
                f'<div class="decision"><h2>{esc(release)}</h2><p>{esc(phase)}</p></div>'
                f'<div class="counts">{counts}</div>{context}'
                f'<section class="section"><h2>逐项评分与提升</h2>'
                '<table class="scores"><thead><tr><th>评分项</th><th>模拟分 / 上限</th>'
                '<th>状态与区间</th><th>理由、扣分与提升</th></tr></thead>'
                f'<tbody>{"".join(rows_html)}</tbody></table></section></main></body></html>')
    if not write:
        return {"html": document, "bytes": len(document.encode("utf-8")), "valid": True}
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return {"path": str(destination), "bytes": destination.stat().st_size,
            "sha256": bidkit.digest(destination), "valid": True}


def render_html(project, payload, out="reports/ai-scoring.html"):
    """Render a validated report in memory without writing any project file."""
    return _render_document(Path(project).resolve(), payload, out, write=False)["html"]


def render(project, payload, out="reports/ai-scoring.html"):
    """Present the supplied judgments without changing scores or release state."""
    return _render_document(Path(project).resolve(), payload, out, write=True)


def _read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--project", required=True)
    prepare_parser.add_argument("--scope", choices=sorted(SCOPES), default="full")
    prepare_parser.add_argument("--out", default="reviews/ai-scoring.json")
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--project", required=True)
    check_parser.add_argument("--scoring", required=True)
    render_parser = sub.add_parser("render")
    render_parser.add_argument("--project", required=True)
    render_parser.add_argument("--scoring", required=True)
    render_parser.add_argument("--out", default="reports/ai-scoring.html")
    args = parser.parse_args()
    try:
        project = Path(args.project).resolve()
        if args.command == "prepare":
            artifact = prepare(project, args.scope)
            destination = _output_path(project, args.out, "reviews")
            bidkit.atomic(destination, artifact)
            result = {"created": str(destination), "valid": True, "artifact": artifact}
        elif args.command == "check":
            result = check(project, _read_json(args.scoring))
        else:
            result = render(project, _read_json(args.scoring), args.out)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("valid", True) else 1
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
