#!/usr/bin/env python3
"""Audit real tender anchors and compare independent extraction evidence; no model calls."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

TRACKS = {"basic_info", "requirements", "scoring", "disqualification"}
CATEGORIES = {"construction", "hardware_supply", "software_integration", "service_outsourcing"}


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def normalized(text):
    return re.sub(r"\s+", "", text)


def safe(root, relative):
    base = Path(root).resolve()
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("语料路径必须相对且位于语料目录内")
    target = (base / path).resolve()
    if not target.is_relative_to(base):
        raise ValueError("语料路径越界")
    return target


def load_pages(root, sample):
    import fitz

    path = safe(root, sample["relative_path"])
    if digest(path) != sample["sha256"] or path.stat().st_size != sample["bytes"]:
        raise ValueError(sample["sample_id"] + ": 原件哈希或字节数变化")
    with fitz.open(path) as doc:
        if doc.needs_pass or len(doc) != sample["pages"]:
            raise ValueError(sample["sample_id"] + ": 页数变化或文件加密")
        return {i: page.get_text("text") for i, page in enumerate(doc, 1)}


def quote_valid(item, pages):
    page = item.get("page")
    quote = item.get("quote")
    return (type(page) is int and page in pages and isinstance(quote, str)
            and len(normalized(quote)) >= 4
            and normalized(quote) in normalized(pages[page]))


def category_groups(lots):
    groups = []
    for lot in lots:
        values = lot.get("categories", [])
        if not values or len(values) != len(set(values)) or set(values) - CATEGORIES:
            raise ValueError("标包类别为空、重复或未知")
        groups.append(tuple(sorted(values)))
    if not groups:
        raise ValueError("缺少标包")
    return sorted(groups)


def audit(manifest, annotations, root):
    samples = manifest["samples"]
    if not samples:
        raise ValueError("语料集合为空")
    ids = [s["sample_id"] for s in samples]
    if len(ids) != len(set(ids)):
        raise ValueError("重复样本ID")
    labels = annotations["samples"]
    label_ids = [a["sample_id"] for a in labels]
    if len(label_ids) != len(set(label_ids)) or set(ids) != set(label_ids):
        raise ValueError("样本与标注集合不一致")
    by_id = {a["sample_id"]: a for a in labels}
    reports = []
    for sample in samples:
        sid = sample["sample_id"]
        label = by_id[sid]
        pages = load_pages(root, sample)
        if label["sha256"] != sample["sha256"]:
            raise ValueError(sid + ": 标注对应的原件已变化")
        if label.get("annotation_status") != "ai_reviewed_not_human_gold":
            raise ValueError(sid + ": 本轮标注须显式保留未人工审定状态")
        category_groups(label["lots"])
        anchors = label["anchors"]
        anchor_ids = [a["id"] for a in anchors]
        if len(anchor_ids) != len(set(anchor_ids)):
            raise ValueError(sid + ": 重复锚点ID")
        for anchor in anchors:
            if anchor.get("track") not in TRACKS or not quote_valid(anchor, pages):
                raise ValueError(sid + ": 标注无法原页回查 " + anchor.get("id", "?"))
            if not isinstance(anchor.get("meaning"), str) or not anchor["meaning"].strip():
                raise ValueError(sid + ": 标注缺少语义说明")
        for lot in label["lots"]:
            if not lot.get("evidence") or any(not quote_valid(e, pages) for e in lot["evidence"]):
                raise ValueError(sid + ": 分类缺少可回看的原文证据")
        tracks = {a["track"] for a in anchors}
        absent = label.get("unavailable_tracks", {})
        if tracks | set(absent) != TRACKS or tracks & set(absent):
            raise ValueError(sid + ": 四类轨道未覆盖或缺失说明矛盾")
        if any(not isinstance(reason, str) or not reason.strip() for reason in absent.values()):
            raise ValueError(sid + ": 缺失轨道必须说明原因")
        reports.append({"sample_id": sid, "pages": len(pages), "anchors": len(anchors),
                        "tracks": sorted(tracks), "unavailable_tracks": absent,
                        "quotes_verified": True})
    return {"passed": True, "samples": reports,
            "total_anchors": sum(r["anchors"] for r in reports),
            "scope": "selected_anchors_only", "human_expert_acceptance": "NOT_RUN"}


def evidence_matches(anchor, fact):
    if anchor["track"] != fact.get("track") or anchor["page"] != fact.get("page"):
        return False
    a, b = normalized(anchor["quote"]), normalized(fact.get("quote", ""))
    # Require the annotated span, rather than scoring a whole-page quote as extraction.
    return a in b and len(b) <= max(3 * len(a), 200)


def evaluate(manifest, annotations, root, predictions):
    audit(manifest, annotations, root)
    metadata = {}
    for key in ("model", "run_id", "scope"):
        value = predictions.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("预测缺少运行元数据: " + key)
        metadata[key] = value
    input_scope = predictions.get("input_scope")
    if not isinstance(input_scope, (str, dict)) or not input_scope:
        raise ValueError("预测缺少运行元数据: input_scope")
    metadata["input_scope"] = input_scope
    samples = {s["sample_id"]: s for s in manifest["samples"]}
    labels = {a["sample_id"]: a for a in annotations["samples"]}
    predictions = predictions["samples"]
    ids = [p["sample_id"] for p in predictions]
    if len(ids) != len(set(ids)) or set(ids) - samples.keys():
        raise ValueError("预测样本ID重复或不存在")
    reports = []
    for pred in predictions:
        sid = pred["sample_id"]
        if pred["sha256"] != samples[sid]["sha256"]:
            raise ValueError(sid + ": 预测的原件身份错误")
        pages = load_pages(root, samples[sid])
        facts = pred["facts"]
        valid = [f for f in facts if f.get("track") in TRACKS and quote_valid(f, pages)]
        matched = [a["id"] for a in labels[sid]["anchors"]
                   if any(evidence_matches(a, f) for f in valid)]
        predicted_groups = category_groups(pred["lots"])
        expected_groups = category_groups(labels[sid]["lots"])
        component_only = labels[sid].get("classification_scope") == "procurement_components_only"
        labels_match = (
            {c for group in predicted_groups for c in group} ==
            {c for group in expected_groups for c in group}
            if component_only else predicted_groups == expected_groups
        )
        classification_evidence_valid = all(
            isinstance(lot.get("evidence"), list) and bool(lot["evidence"])
            and all(quote_valid(e, pages) for e in lot["evidence"])
            for lot in pred["lots"]
        )
        reports.append({"sample_id": sid,
                        "classification_labels_match": labels_match,
                        "classification_evidence_valid": classification_evidence_valid,
                        "classification_match": labels_match and classification_evidence_valid,
                        "lot_grouping_scored": not component_only,
                        "facts": len(facts), "valid_citations": len(valid),
                        "matched_anchor_ids": matched,
                        "missing_anchor_ids": [a["id"] for a in labels[sid]["anchors"]
                                               if a["id"] not in matched],
                        "annotated_anchors": len(labels[sid]["anchors"])})
    return {"run": metadata, "samples": reports,
            "not_run_samples": sorted(samples.keys() - set(ids)),
            "classification_matches": sum(r["classification_match"] for r in reports),
            "evaluated_samples": len(reports),
            "matched_anchors": sum(len(r["matched_anchor_ids"]) for r in reports),
            "annotated_anchors": sum(r["annotated_anchors"] for r in reports),
            "scope": "evidence_anchor_coverage_not_full_document_recall",
            "semantic_correctness": "REQUIRES_SEPARATE_REVIEW",
            "false_positive_rate": "NOT_MEASURED_UNANNOTATED_FACTS_NOT_FALSE_POSITIVES",
            "human_expert_acceptance": "NOT_RUN"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["audit", "evaluate"])
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--predictions", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "evaluate" and args.predictions is None:
            parser.error("evaluate 需要 --predictions")
        inputs = (read(args.manifest), read(args.annotations), args.corpus_root)
        result = (evaluate(*inputs, read(args.predictions)) if args.command == "evaluate"
                  else audit(*inputs))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"passed": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
