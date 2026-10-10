#!/usr/bin/env python3
"""Check the host-authored quality plan against a real review and bid inputs.

This is a mechanical binding check.  It verifies current hashes, exact source and
response quotes, condition coverage, and registered fact consistency.  It never
calculates a score or turns a reviewer conclusion into semantic approval.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import bidkit


UPSTREAM = {
    "scoring": ("artifacts/04-scoring.json", "items"),
    "compliance": ("artifacts/05-compliance.json", "rules"),
    "materials": ("artifacts/09-evidence-selection.json", "selections"),
}
QUALITY_PLAN = "profiles/quality-plan.json"
QUALITY_REVIEW = "reviews/quality-review.json"
CONCLUSIONS = {"satisfied", "partial", "missing", "unknown", "deferred"}
FACT_CONCLUSIONS = {"consistent", "conflict", "unknown", "not_applicable"}
_NUMBER = re.compile(r"[-+]?\d+(?:[,.]\d+)?")


def _project_path(project, value):
    path = Path(value)
    if not path.is_absolute():
        return bidkit.safe(project, str(value))
    path = path.resolve()
    if not path.is_relative_to(Path(project).resolve()):
        raise ValueError("路径必须在项目内：" + str(value))
    return path


def _relative_ref(project, reference, label):
    if not isinstance(reference, dict):
        raise ValueError(label + "必须是对象")
    relative = reference.get("relative_path")
    digest = reference.get("sha256")
    if not isinstance(relative, str) or not relative.strip():
        raise ValueError(label + "缺少relative_path")
    if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
        raise ValueError(label + "缺少有效sha256")
    path = bidkit.safe(project, relative)
    if not path.is_file() or bidkit.digest(path) != digest:
        raise ValueError(label + "不存在或哈希过期：" + relative)
    return relative, digest, path


def _plan_conditions(plan):
    """Return a flat condition list while accepting the natural grouped authoring form."""
    rows = plan.get("conditions")
    if rows is None:
        rows = plan.get("scoring_conditions", [])
    if not isinstance(rows, list):
        raise ValueError("质量计划conditions必须是数组")
    result = []
    for group in rows:
        if not isinstance(group, dict):
            raise ValueError("质量计划条件行必须是对象")
        nested = group.get("conditions")
        if isinstance(nested, list):
            score_id = group.get("scoring_id") or group.get("target_id") or group.get("score_id")
            for row in nested:
                if not isinstance(row, dict):
                    raise ValueError("质量计划条件行必须是对象")
                item = dict(row)
                item.setdefault("scoring_id", score_id)
                result.append(item)
        else:
            result.append(group)
    return result


def _plan_facts(plan):
    facts = plan.get("facts", plan.get("common_facts", []))
    if not isinstance(facts, list):
        raise ValueError("质量计划facts必须是数组")
    return facts


def _refs(row, *names):
    for name in names:
        if name in row:
            return row[name]
    return []


def _review_conditions(review):
    rows = review.get("conditions", review.get("condition_reviews", review.get("condition_rows", [])))
    if not isinstance(rows, list):
        raise ValueError("质量评审conditions必须是数组")
    return rows


def _review_facts(review):
    rows = review.get("facts", review.get("fact_reviews", review.get("fact_rows", [])))
    if not isinstance(rows, list):
        raise ValueError("质量评审facts必须是数组")
    return rows


def _upstream(project):
    pid = bidkit.project_id(project)
    values = {}
    hashes = {}
    for area, (relative, key) in UPSTREAM.items():
        path = bidkit.safe(project, relative)
        payload = bidkit.read(path)
        if payload.get("project_id") != pid:
            raise ValueError(relative + "：项目身份不一致")
        rows = payload.get("data", {}).get(key)
        if not isinstance(rows, list):
            raise ValueError(relative + "：缺少" + key)
        if len({x.get("id") for x in rows}) != len(rows):
            raise ValueError(relative + "：上游ID重复")
        values[area] = {x["id"]: x for x in rows}
        hashes[relative] = bidkit.digest(path)
    values["scored"] = {
        ident: row for ident, row in values["scoring"].items()
        if row.get("node_type") == "scored"
    }
    return values, hashes


def _source_checker(project):
    # Import lazily so review_checks can call this module without a module cycle.
    from review_checks import source_text
    return source_text


def _body_checker(project):
    # review_checks.reference_text is the anti-self-proof boundary: only actual
    # 11/12/14 artifacts and concrete locations are accepted.
    from review_checks import reference_text
    return reference_text


def _check_sources(project, refs, errors, row_id, cache):
    if not isinstance(refs, list) or not refs:
        errors.append(row_id + ": 缺少原文source_refs")
        return
    check = _source_checker(project)
    for source in refs:
        try:
            check(project, source, cache)
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            errors.append(row_id + ": " + str(exc))


def _check_bodies(project, refs, errors, row_id, bound=None):
    if not isinstance(refs, list):
        errors.append(row_id + ": body_refs必须是数组")
        return []
    values = []
    check = _body_checker(project)
    for reference in refs:
        try:
            relative = reference.get("relative_path") if isinstance(reference, dict) else None
            if not isinstance(relative, str) or not relative.startswith("artifacts/"):
                raise ValueError("正文引用不能引用评审自证响应")
            if not Path(relative).name.startswith(("11-", "12-", "14-")):
                raise ValueError("正文引用不能用需求、评分或评审文件自证响应")
            check(project, reference)
            values.append(reference['quote'])
            if bound is not None and bound.get(reference.get("relative_path")) != reference.get("sha256"):
                errors.append(row_id + ": 正文引用未绑定质量评审输入：" + str(reference.get("relative_path")))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            errors.append(row_id + ": " + str(exc))
    return values


def _expected(fact):
    for key in ("expected", "expected_value", "value", "expected_phrase"):
        if key in fact:
            return fact[key]
    return None


def _normalized(value):
    return re.sub(r"\s+", "", str(value))


def _numbers(values):
    return [token.replace(",", "") for value in values for token in _NUMBER.findall(value)]


def _fact_consistency(fact, values, errors, row_id):
    kind = fact.get("kind", fact.get("type", "phrase"))
    expected = _expected(fact)
    if expected is None:
        errors.append(row_id + ": 缺少expected事实值")
        return
    if not values:
        errors.append(row_id + ": 缺少可回读的正文事实")
        return
    joined = "\n".join(values)
    if kind in {"numeric", "number", "amount", "duration"}:
        try:
            expected_token = str(float(expected)).rstrip("0").rstrip(".")
        except (TypeError, ValueError):
            errors.append(row_id + ": numeric事实expected不是数字")
            return
        actual = _numbers(values)
        if expected_token not in actual:
            errors.append(row_id + ": 正文数字与登记事实冲突（期望" + str(expected) + "）")
        unexpected = [token for token in actual if token != expected_token]
        if unexpected:
            errors.append(row_id + ": 正文存在未登记参数值：" + ",".join(sorted(set(unexpected))))
    else:
        expected_text = _normalized(expected)
        if expected_text not in _normalized(joined):
            errors.append(row_id + ": 正文未出现登记事实短语：" + str(expected))
    unit = fact.get("unit")
    if unit and _normalized(unit) not in _normalized(joined):
        errors.append(row_id + ": 正文未出现登记事实单位：" + str(unit))


def _sections(row):
    value = row.get("section_ids", row.get("affected_section_ids", []))
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return [x for x in value if isinstance(x, str) and x]


def _result(project_id, quality_gate, errors=None, blockers=None, warnings=None,
            semantic_acceptance="NOT_RUN", actions=None, plan_identity=None, counts=None):
    errors = list(dict.fromkeys(errors or []))
    blockers = list(dict.fromkeys(blockers or []))
    warnings = list(dict.fromkeys(warnings or []))
    actions = actions or []
    sections = sorted({section for action in actions for section in action.get("section_ids", [])})
    return {
        "project_id": project_id,
        "quality_gate": quality_gate,
        "current": not errors,
        "errors": errors,
        "blockers": blockers,
        "release_blockers": blockers,
        "warnings": warnings,
        "semantic_acceptance": semantic_acceptance,
        "semantic_acceptance_certified": False,
        "plan_identity": plan_identity,
        "actions": actions,
        "remediation_rows": actions,
        "affected_section_ids": sections,
        "counts": counts or {},
        "binding_ready": quality_gate != "NOT_RUN" and not errors and not blockers,
        "notice": "机械绑定检查不认证语义、企业真实性或评委主观评分。",
    }


def _looks_like_plan(value):
    return isinstance(value, dict) and ("plan_id" in value or "inputs" in value) and "conditions" in value


def _looks_like_review(value):
    return isinstance(value, dict) and ("plan_ref" in value or "quality_plan_ref" in value) and "conditions" in value


def check(project, quality_review=None, plan=None, review=None):
    """Check a quality-review object, loading the project plan when omitted.

    ``quality_review`` and ``plan`` may also be paths.  With no current plan this
    returns ``quality_gate=NOT_RUN`` so historical reviews are never silently
    upgraded.
    """
    # The documented order is (project, quality_review, plan), but accepting
    # (project, plan, quality_review) keeps host workflow adapters small.
    if review is not None:
        quality_review = review
    if plan is None and (_looks_like_plan(quality_review)
                         or (isinstance(quality_review, (str, Path))
                             and Path(quality_review).name == "quality-plan.json")):
        plan, quality_review = quality_review, None
    elif _looks_like_plan(quality_review) and (_looks_like_review(plan) or isinstance(plan, (str, Path))):
        quality_review, plan = plan, quality_review
    elif isinstance(quality_review, (str, Path)) and isinstance(plan, (str, Path)):
        q_name, p_name = Path(quality_review).name, Path(plan).name
        if q_name == "quality-plan.json" and p_name != q_name:
            quality_review, plan = plan, quality_review
    project = Path(project).resolve()
    pid = bidkit.project_id(project)
    plan_path = bidkit.safe(project, QUALITY_PLAN)
    if plan is None:
        if not plan_path.is_file():
            return _result(pid, "NOT_RUN", semantic_acceptance="NOT_RUN",
                           plan_identity=None, counts={"reason": "quality-plan.json missing"})
        plan = bidkit.read(plan_path)
    elif isinstance(plan, (str, Path)):
        plan_path = _project_path(project, plan)
        plan = bidkit.read(plan_path)
    if quality_review is None:
        review_path = bidkit.safe(project, QUALITY_REVIEW)
        if not review_path.is_file():
            return _result(pid, "BLOCKED", errors=["质量评审不存在：" + QUALITY_REVIEW],
                           plan_identity={"relative_path": QUALITY_PLAN,
                                          "sha256": bidkit.digest(plan_path)},
                           counts={"reason": "quality-review.json missing"})
        quality_review = bidkit.read(review_path)
    elif isinstance(quality_review, (str, Path)):
        quality_review = bidkit.read(_project_path(project, quality_review))

    errors, blockers, warnings, actions = [], [], [], []
    try:
        _, current_hashes = _upstream(project)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return _result(pid, "BLOCKED", errors=[str(exc)], semantic_acceptance=quality_review.get("semantic_acceptance", "NOT_RUN")
                       if isinstance(quality_review, dict) else "NOT_RUN")
    if not isinstance(plan, dict):
        return _result(pid, "BLOCKED", errors=["质量计划必须是对象"])
    if plan.get("project_id") != pid:
        errors.append("质量计划项目身份不一致")
    if plan_path.is_file() and plan.get("plan_id") in {None, ""}:
        errors.append("质量计划缺少plan_id")
    plan_identity = {"relative_path": QUALITY_PLAN, "sha256": bidkit.digest(plan_path)}
    inputs = plan.get("inputs", plan.get("upstream_inputs", plan.get("upstream_refs", [])))
    if not isinstance(inputs, list):
        errors.append("质量计划inputs必须是数组")
        inputs = []
    input_map = {}
    for ref in inputs:
        try:
            relative, digest, _ = _relative_ref(project, ref, "质量计划输入")
            if relative in input_map:
                errors.append("质量计划输入重复：" + relative)
            input_map[relative] = digest
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(str(exc))
    for relative, digest in current_hashes.items():
        if input_map.get(relative) != digest:
            errors.append("质量计划未绑定当前上游：" + relative)
    if isinstance(quality_review, dict):
        if quality_review.get("project_id") != pid:
            errors.append("质量评审项目身份不一致")
        plan_ref = quality_review.get("plan_ref", quality_review.get("quality_plan_ref"))
        if not isinstance(plan_ref, dict):
            errors.append("质量评审缺少plan_ref")
        else:
            try:
                relative, digest, _ = _relative_ref(project, plan_ref, "质量评审plan_ref")
                if relative != QUALITY_PLAN or digest != plan_identity["sha256"]:
                    errors.append("质量评审未绑定当前质量计划")
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(str(exc))
    else:
        errors.append("质量评审必须是对象")
        quality_review = {}

    try:
        conditions = _plan_conditions(plan)
        facts = _plan_facts(plan)
    except ValueError as exc:
        return _result(pid, "BLOCKED", errors=errors + [str(exc)],
                       semantic_acceptance=quality_review.get("semantic_acceptance", "NOT_RUN"),
                       plan_identity=plan_identity)
    values, _ = _upstream(project)
    cache = {}
    condition_ids = [row.get("condition_id") for row in conditions]
    if any(not isinstance(x, str) or not x for x in condition_ids):
        errors.append("质量计划存在缺少condition_id的条件")
    if len(condition_ids) != len(set(condition_ids)):
        errors.append("质量计划condition_id重复")
    by_score = {}
    for row in conditions:
        if not isinstance(row.get("description"), str) or not row["description"].strip():
            errors.append(str(row.get("condition_id")) + ": 原子条件缺少具体description")
        score_id = row.get("scoring_id", row.get("target_id", row.get("score_id")))
        by_score.setdefault(score_id, []).append(row)
        if score_id not in values["scored"]:
            errors.append(str(row.get("condition_id")) + ": 未知评分叶子")
        _check_sources(project, _refs(row, "source_refs", "sources"), errors,
                       str(row.get("condition_id")), cache)
        # Tie condition sources to this scoring leaf, not merely any readable source.
        upstream_refs = values['scored'].get(score_id, {}).get('sources', [])
        for reference in _refs(row, 'source_refs', 'sources'):
            def page_range(location):
                match = re.fullmatch(r'P(\d+)(?:[-–]P?(\d+))?', str(location))
                return (int(match[1]), int(match[2] or match[1])) if match else None
            def belongs(upstream):
                if any(reference.get(k) != upstream.get(k) for k in ('source_id', 'revision', 'sha256', 'kind')):
                    return False
                a, b = page_range(reference.get('location')), page_range(upstream.get('location'))
                location_matches = (b[0] <= a[0] <= a[1] <= b[1]) if a and b else reference.get('location') == upstream.get('location')
                normalize = lambda text: re.sub(r'\s+', '', str(text))
                return location_matches and bool(reference.get('quote')) and normalize(reference['quote']) in normalize(upstream.get('quote', ''))
            if not any(belongs(upstream) for upstream in upstream_refs):
                errors.append(str(row.get('condition_id')) + ': 条件原文不属于对应评分叶子的来源范围')
        body_refs = _refs(row, "body_refs", "response_refs", "bid_refs")
        if body_refs:
            _check_bodies(project, body_refs, errors, str(row.get("condition_id")))
    missing_scores = set(values["scored"]) - set(by_score)
    if missing_scores:
        errors.append("质量计划漏评分叶子：" + ",".join(sorted(missing_scores)))
    try:
        review_rows = _review_conditions(quality_review)
    except ValueError as exc:
        return _result(pid, "BLOCKED", errors=errors + [str(exc)],
                       semantic_acceptance=quality_review.get("semantic_acceptance", "NOT_RUN"),
                       plan_identity=plan_identity)
    review_ids = [row.get("condition_id") for row in review_rows]
    if len(review_ids) != len(set(review_ids)):
        errors.append("质量评审condition_id重复")
    plan_ids = set(condition_ids)
    review_id_set = set(review_ids)
    plan_by_id = {row.get("condition_id"): row for row in conditions}
    if plan_ids - review_id_set:
        missing = sorted(plan_ids - review_id_set)
        blockers.append("质量评审漏条件：" + ",".join(missing))
        for condition_id in missing:
            row = plan_by_id.get(condition_id, {})
            actions.append({"row_id": condition_id, "target_id": row.get("scoring_id"),
                            "state": "blocker", "reason": "missing_review_row",
                            "blocking": True, "section_ids": _sections(row)})
    if review_id_set - plan_ids:
        errors.append("质量评审存在未知条件：" + ",".join(sorted(review_id_set - plan_ids)))
    for row in review_rows:
        condition_id = row.get("condition_id")
        plan_row = plan_by_id.get(condition_id)
        if plan_row is None:
            continue
        section_ids = _sections(plan_row)
        conclusion = row.get("conclusion")
        if conclusion not in CONCLUSIONS:
            errors.append(str(condition_id) + ": 结论无效")
            continue
        if not str(row.get("rationale") or "").strip():
            errors.append(str(condition_id) + ": 缺少结论理由")
        error_count = len(errors)
        _check_sources(project, _refs(row, "source_refs", "sources")
                       or _refs(plan_row, "source_refs", "sources"),
                       errors, str(condition_id), cache)
        body_refs = _refs(row, "body_refs", "response_refs", "bid_refs")
        if conclusion in {"satisfied", "partial", "deferred"} and not body_refs:
            errors.append(str(condition_id) + ": 已响应结论缺少正文body_refs")
        _check_bodies(project, body_refs, errors, str(condition_id))
        if len(errors) > error_count:
            actions.append({"row_id": condition_id, "target_id": plan_row.get("scoring_id"),
                            "state": "error", "reason": "evidence_binding", "blocking": True,
                            "section_ids": section_ids})
        if plan_row.get('phase') == 'evaluation' and conclusion not in {'deferred', 'unknown'}:
            errors.append(str(condition_id) + ': 评标阶段外部条件尚未产生，不能声称已满足或已失分')
        if conclusion == "deferred":
            if plan_row.get('phase') != 'evaluation':
                errors.append(str(condition_id) + ': 延后条件必须明确属于评标阶段')
            else:
                warnings.append(str(condition_id) + ': 等待评标阶段外部条件，不是投标正文漏项')
        if conclusion == "unknown":
            blockers.append(str(condition_id) + ": 条件尚未完成逐项复核")
            actions.append({"row_id": condition_id, "target_id": plan_row.get("scoring_id"),
                            "state": "blocker", "reason": "unknown", "blocking": True,
                            "section_ids": section_ids})
        elif conclusion in {"partial", "missing"}:
            warnings.append(str(condition_id) + ": 评分条件存在响应缺口：" + conclusion)
            actions.append({"row_id": condition_id, "target_id": plan_row.get("scoring_id"),
                            "state": "warning", "reason": conclusion, "blocking": False,
                            "section_ids": section_ids})
    try:
        fact_rows = _review_facts(quality_review)
    except ValueError as exc:
        return _result(pid, "BLOCKED", errors=errors + [str(exc)],
                       semantic_acceptance=quality_review.get("semantic_acceptance", "NOT_RUN"),
                       plan_identity=plan_identity)
    fact_ids = [row.get("fact_id") for row in fact_rows]
    if len(fact_ids) != len(set(fact_ids)):
        errors.append("质量评审fact_id重复")
    plan_facts = {row.get("fact_id"): row for row in facts}
    review_fact_ids = set(fact_ids)
    missing_facts = set(plan_facts) - review_fact_ids
    if missing_facts:
        missing = sorted(missing_facts)
        blockers.append("质量评审漏共同事实：" + ",".join(missing))
        for fact_id in missing:
            fact = plan_facts.get(fact_id, {})
            actions.append({"row_id": fact_id, "target_id": fact_id,
                            "state": "blocker", "reason": "missing_review_row",
                            "blocking": True, "section_ids": _sections(fact)})
    if review_fact_ids - set(plan_facts):
        errors.append("质量评审存在未知共同事实：" + ",".join(sorted(review_fact_ids - set(plan_facts))))
    for fact_id, fact in plan_facts.items():
        error_count = len(errors)
        _check_sources(project, _refs(fact, "source_refs", "sources"), errors,
                       str(fact_id), cache)
        values_text = _check_bodies(project, _refs(fact, "body_refs", "response_refs", "bid_refs"),
                                    errors, str(fact_id))
        _fact_consistency(fact, values_text, errors, str(fact_id))
        review_fact = next((row for row in fact_rows if row.get("fact_id") == fact_id), None)
        if review_fact is not None:
            review_body_refs = _refs(review_fact, "body_refs", "response_refs", "bid_refs")
            if review_body_refs:
                _check_bodies(project, review_body_refs, errors, str(fact_id))
            conclusion = review_fact.get("conclusion")
            if conclusion not in FACT_CONCLUSIONS:
                errors.append(str(fact_id) + ": 事实结论无效")
            elif conclusion == "unknown":
                blockers.append(str(fact_id) + ": 共同事实尚未完成复核")
            elif conclusion == "conflict":
                blockers.append(str(fact_id) + ": 共同事实存在冲突")
            elif conclusion == "not_applicable":
                warnings.append(str(fact_id) + ": 共同事实标记不适用，需人工确认")
            if conclusion in {"conflict", "unknown"}:
                actions.append({"row_id": fact_id, "target_id": fact_id, "state": "blocker",
                                "reason": conclusion, "blocking": True,
                                "section_ids": _sections(fact)})
        if len(errors) > error_count and not any(a.get("row_id") == fact_id for a in actions):
            actions.append({"row_id": fact_id, "target_id": fact_id, "state": "error",
                            "reason": "fact_binding", "blocking": True,
                            "section_ids": _sections(fact)})
    semantic = quality_review.get("semantic_acceptance", "NOT_RUN")
    gate = "BLOCKED" if errors or blockers else ("PASSED_WITH_WARNINGS" if warnings else "PASSED")
    return _result(pid, gate, errors, blockers, warnings, semantic, actions,
                   plan_identity, {"conditions": len(conditions), "condition_reviews": len(review_rows),
                                   "facts": len(facts), "fact_reviews": len(fact_rows),
                                   "scored_leaves": len(values["scored"])})


def prepare(project, plan=None):
    """Create an unknown quality-review scaffold for a host-authored plan."""
    project = Path(project).resolve()
    pid = bidkit.project_id(project)
    plan_path = bidkit.safe(project, QUALITY_PLAN)
    if plan is None:
        if not plan_path.is_file():
            return {"project_id": pid, "quality_gate": "NOT_RUN",
                    "plan_ref": None, "conditions": [], "facts": [],
                    "semantic_acceptance": "NOT_RUN",
                    "notice": "先由宿主创建profiles/quality-plan.json并拆解评分条件。"}
        plan = bidkit.read(plan_path)
    elif isinstance(plan, (str, Path)):
        plan_path = _project_path(project, plan)
        plan = bidkit.read(plan_path)
    conditions = []
    for row in _plan_conditions(plan):
        conditions.append({"condition_id": row.get("condition_id"),
                           "scoring_id": row.get("scoring_id", row.get("target_id")),
                           "conclusion": "unknown", "rationale": "尚未逐条回读评分条件、正文及证据。",
                           "source_refs": _refs(row, "source_refs", "sources"),
                           "body_refs": [], "section_ids": _sections(row),
                           "score_estimate": None})
    facts = []
    for row in _plan_facts(plan):
        facts.append({"fact_id": row.get("fact_id"), "conclusion": "unknown",
                      "rationale": "尚未逐条回读共同事实及正文。",
                      "body_refs": _refs(row, "body_refs", "response_refs", "bid_refs"),
                      "section_ids": _sections(row)})
    return {"schema_version": "1.0", "project_id": pid,
            "plan_ref": {"relative_path": QUALITY_PLAN, "sha256": bidkit.digest(plan_path)},
            "status": "needs_review", "conditions": conditions, "facts": facts,
            "semantic_acceptance": "NOT_RUN",
            "notice": "此文件是逐项评审输入；脚本不会预测评分或认证语义。"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prepare_parser = sub.add_parser("prepare")
    prepare_parser.add_argument("--project", type=Path, required=True)
    prepare_parser.add_argument("--out", default=QUALITY_REVIEW)
    check_parser = sub.add_parser("check")
    check_parser.add_argument("--project", type=Path, required=True)
    check_parser.add_argument("--quality-review", default=QUALITY_REVIEW)
    check_parser.add_argument("--plan", default=QUALITY_PLAN)
    check_parser.add_argument("--out")
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.project)
            destination = bidkit.safe(args.project, args.out)
            if destination.exists():
                raise ValueError("拒绝覆盖既有质量评审，请使用新版本")
            if not destination.is_relative_to(args.project.resolve() / "reviews"):
                raise ValueError("质量评审须放reviews")
            bidkit.atomic(destination, result)
            code = 0
        else:
            result = check(args.project, args.quality_review, args.plan)
            if args.out:
                destination = bidkit.safe(args.project, args.out)
                if not destination.is_relative_to(args.project.resolve() / "reviews"):
                    raise ValueError("质量回执须放reviews")
                bidkit.atomic(destination, result)
            code = 0 if result["binding_ready"] else 1
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return code
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
