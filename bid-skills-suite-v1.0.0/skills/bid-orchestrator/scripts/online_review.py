"""Freeze and recheck the online body used by a semantic review."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def basis(project, scope="full"):
    from online_documents import OnlineDocumentService
    service = OnlineDocumentService(project)
    state = service.status()
    if not state.get("bound"):
        return None
    sections = sorted(state.get("current_mapping", {})) if scope == "limited" else None
    if scope == "limited" and not sections:
        raise ValueError("在线限定评审前至少同步一个章节")
    checked = service.assert_current(sections)["binding"]
    mapping = checked.get("current_mapping", {})
    selected = sections if sections is not None else sorted(mapping)
    fingerprints = {key: {"local_hash": mapping[key]["last_synced"]["local_hash"],
                          "remote_hash": mapping[key]["remote_hash"]} for key in selected}
    value = {"provider": checked["provider"], "document_id": checked["canonical_id"],
            "project_id": checked["project_id"], "section_ids": selected,
            "fingerprint": hashlib.sha256(json.dumps(fingerprints, sort_keys=True).encode()).hexdigest()}
    from bidkit import atomic, safe
    path = safe(project, "work/online-review-basis.json")
    serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if not path.is_file() or json.dumps(json.loads(path.read_text()), ensure_ascii=False, sort_keys=True) != serialized:
        atomic(path, value)
    return value


def verify(project, frozen, scope="full", rows=None):
    current = basis(project, scope)
    if frozen != current:
        raise ValueError("在线正文或文档绑定已变化，请重新读取并评审")
    if not current or rows is None or scope != "limited":
        return
    # A limited assessment cannot silently score unpublished local chapters.
    from bidkit import read, safe
    writing = read(safe(project, "artifacts/11-technical-content.json"))
    chapters = writing.get("data", {}).get("chapters", [])
    allowed = set(current["section_ids"])
    for row in rows:
        if row.get("status") != "scored":
            continue
        for ref in row.get("bid_refs", []):
            if ref.get("relative_path") != "artifacts/11-technical-content.json":
                raise ValueError("在线限定评分只能引用已同步章节正文；其他文件请完成整本同步后评审")
            location = str(ref.get("location", "")).split("/")
            try:
                if location[1:3] != ["data", "chapters"]:
                    raise ValueError()
                section_id = chapters[int(location[3])]["section_id"]
            except (ValueError, IndexError, KeyError) as exc:
                raise ValueError("在线限定评分缺少明确章节定位") from exc
            if section_id not in allowed:
                raise ValueError("在线限定评分引用了未同步的章节：" + section_id)
