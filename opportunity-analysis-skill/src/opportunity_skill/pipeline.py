from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import mimetypes
import re
import shutil
from pathlib import Path
from typing import Any
from .extractor import analyze
from .storage import OpportunitySQLiteAdapter
from .renderer import SkillDisplayRenderer


def _safe_file_name(name: str, fallback: str) -> str:
    clean = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", name).strip("._")
    return clean[:96] or fallback


def _attachment_candidates(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for key in ["file_path", "path", "source_path"]:
        if evidence.get(key):
            candidates.append({"path": evidence[key], "display_name": evidence.get("source_name")})
    source_ref = evidence.get("source_ref")
    if isinstance(source_ref, str):
        candidates.append({"path": source_ref, "display_name": evidence.get("source_name")})
    for item in evidence.get("attachments", []) or []:
        if isinstance(item, str):
            candidates.append({"path": item})
        elif isinstance(item, dict):
            path = item.get("path") or item.get("file_path") or item.get("source_path")
            if path:
                candidates.append({**item, "path": path})
    return candidates


def archive_material_files(result: dict[str, Any], archive_root: str | Path | None) -> list[dict[str, Any]]:
    """Copy local source files into the run archive and attach metadata to Evidence."""
    if not archive_root:
        return []
    structured = result.get("structured_data", result)
    evidence_list = structured.get("evidence", [])
    archive_dir = Path(archive_root) / "attachments"
    archived_files: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for evidence in evidence_list:
        evidence_id = evidence.get("evidence_id") or evidence.get("id")
        if not evidence_id:
            continue
        evidence_files = list(evidence.get("archived_files", []) or [])
        for candidate in _attachment_candidates(evidence):
            source = Path(str(candidate["path"])).expanduser()
            if not source.exists() or not source.is_file():
                continue
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            key = (str(evidence_id), digest)
            if key in seen:
                continue
            seen.add(key)
            archive_dir.mkdir(parents=True, exist_ok=True)
            mime_type = mimetypes.guess_type(source.name)[0] or "application/octet-stream"
            safe_name = _safe_file_name(source.name, f"{digest[:12]}")
            archive_name = f"{digest[:12]}_{safe_name}"
            target = archive_dir / archive_name
            if source.resolve() != target.resolve():
                shutil.copy2(source, target)
            item = {
                "id": f"file_{str(evidence_id).replace('-', '_')}_{digest[:12]}",
                "evidence_id": evidence_id,
                "original_path": str(source),
                "archived_path": str(target),
                "relative_path": f"attachments/{archive_name}",
                "file_name": source.name,
                "display_name": candidate.get("display_name") or source.name,
                "mime_type": mime_type,
                "size_bytes": target.stat().st_size,
                "sha256": digest,
                "is_image": mime_type.startswith("image/"),
            }
            evidence_files.append(item)
            archived_files.append(item)
        evidence["archived_files"] = evidence_files
    structured["archived_files"] = archived_files
    return archived_files


def prepare_detail_attachments(detail: dict[str, Any], output_dir: str | Path | None) -> None:
    """Make archived files linkable from a newly rendered detail output folder."""
    if not output_dir:
        return
    out = Path(output_dir)
    target_dir = out / "attachments"
    for item in detail.get("archived_files", []) or []:
        archived_path = item.get("archived_path")
        if not archived_path:
            continue
        source = Path(archived_path)
        if not source.exists() or not source.is_file():
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = _safe_file_name(item.get("file_name") or source.name, source.name)
        target = target_dir / f"{item.get('sha256', '')[:12]}_{safe_name}"
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        item["relative_path"] = f"attachments/{target.name}"
    for ev in detail.get("evidence", []) or []:
        for item in ev.get("archived_files", []) or []:
            match = next((x for x in detail.get("archived_files", []) if x.get("id") == item.get("id")), None)
            if match:
                item["relative_path"] = match.get("relative_path")
    for artifact in detail.get('lifecycle', {}).get('artifacts', []):
        # Export only the registered bytes; a changed source must not masquerade
        # as the approved version in the report's download link.
        artifact.pop('relative_path', None)
        source = Path(artifact['file_path'])
        try:
            content = source.read_bytes()
        except OSError:
            continue
        digest = hashlib.sha256(content).hexdigest()
        if digest != artifact.get('sha256'):
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{digest[:12]}_{_safe_file_name(source.name, digest[:12])}"
        if source.resolve() != target.resolve():
            target.write_bytes(content)
        artifact['relative_path'] = f'attachments/{target.name}'


def run_analyze(input_data: dict[str, Any], db_path: str | Path, output_dir: str | Path | None = None, template_id: str = "opportunity_card", *, theme: str = "light") -> dict[str, Any]:
    adapter = OpportunitySQLiteAdapter(db_path)
    analysis_input = deepcopy(input_data)
    if input_data.get('opportunity_id'):
        previous = adapter.get_opportunity_detail(input_data['opportunity_id'])
        from .stages.evidence_normalization import normalize_input
        old = [{**ev, 'evidence_id': ev['id']} for ev in previous['evidence']]
        combined = {ev['evidence_id']: ev for ev in old}
        combined.update({ev['evidence_id']: ev for ev in normalize_input(input_data)})
        analysis_input['evidence_list'] = list(combined.values())
        analysis_input.setdefault('account_hint', previous['account']['company_name'])
        answers = {answer['dimension_id']: {k: v for k, v in answer.items()
                   if k not in {'id', 'assessment_id', 'opportunity_id', 'created_at'}}
                   for answer in previous['sales_confirmation_answers']}
        answers.update({answer['dimension_id']: answer for answer in input_data.get('sales_confirmation_answers', [])})
        analysis_input['sales_confirmation_answers'] = list(answers.values())
        if previous['lifecycle'].get('owner'):
            analysis_input.setdefault('owner', previous['lifecycle']['owner'])
    result = analyze(analysis_input)
    archive_material_files(result, output_dir or Path(db_path).parent)
    try:
        storage_result = adapter.save_structured_data(result, request=input_data)
    except Exception:
        adapter.close()
        raise
    detail = adapter.get_opportunity_detail(storage_result["opportunity_id"])
    for key in ('account', 'opportunity', 'contacts', 'decision_chain', 'commercial_assessment', 'sales_confirmation_questions', 'sales_confirmation_answers', 'risks', 'next_actions', 'evidence', 'evidence_map', 'archived_files', 'lifecycle'):
        result['structured_data'][key] = deepcopy(detail[key])
    prepare_detail_attachments(detail, output_dir)
    renderer = SkillDisplayRenderer()
    display = renderer.render(template_id, detail, theme=theme)

    html_path = None
    md_path = None
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        html_path = out / f"{template_id}.html"
        md_path = out / f"{template_id}.md"
        html_path.write_text(display["html"], encoding="utf-8")
        md_path.write_text(display["markdown"], encoding="utf-8")
    view_id = adapter.save_rendered_view("opportunity", storage_result["opportunity_id"], template_id, display["html"], display["markdown"])
    adapter.save_skill_run({
        "input_summary": input_data.get("analysis_goal") or "商机分析",
        "output_summary": result.get("human_summary"),
        "structured_output": json.dumps(result.get("structured_data", {}), ensure_ascii=False),
        "display_output_path": str(html_path) if html_path else None,
        "status": "success"
    })
    adapter.close()
    final = {
        **result,
        "storage_result": storage_result,
        "display_result": {
            "template_id": template_id,
            "html": display["html"],
            "markdown": display["markdown"],
            "html_path": str(html_path) if html_path else None,
            "markdown_path": str(md_path) if md_path else None,
            "rendered_view_id": view_id
        }
    }
    if output_dir:
        (Path(output_dir) / "result.json").write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
    return final


def run_query(db_path: str | Path, query_json: dict[str, Any], output_dir: str | Path | None = None, render_html: bool = False, *, template_id: str = "opportunity_list", theme: str = "light") -> dict[str, Any]:
    adapter = OpportunitySQLiteAdapter(db_path)
    opportunities = adapter.query_opportunities(query_json)
    result = {"query": query_json, "opportunities": opportunities, "count": len(opportunities)}
    if render_html:
        renderer = SkillDisplayRenderer()
        if output_dir:
            for record in opportunities:
                oid = record['id']
                slug = _safe_file_name(oid, 'opportunity') + '_' + hashlib.sha256(oid.encode()).hexdigest()[:8]
                directory = Path(output_dir) / 'details' / slug
                detail = adapter.get_opportunity_detail(oid)
                prepare_detail_attachments(detail, directory)
                rendered = renderer.render('opportunity_detail', detail, theme=theme)
                directory.mkdir(parents=True, exist_ok=True)
                (directory / 'opportunity_detail.html').write_text(rendered['html'], encoding='utf-8')
                (directory / 'opportunity_detail.md').write_text(rendered['markdown'], encoding='utf-8')
                record['detail_url'] = f'details/{slug}/opportunity_detail.html'
        display = renderer.render(template_id, result, theme=theme)
        result["display_result"] = display
        if output_dir:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / "query_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (out / f"{template_id}.html").write_text(display["html"], encoding="utf-8")
            (out / f"{template_id}.md").write_text(display["markdown"], encoding="utf-8")
    adapter.close()
    return result


def run_detail(db_path: str | Path, opportunity_id: str, output_dir: str | Path | None = None, template_id: str = "opportunity_detail", *, theme: str = "light") -> dict[str, Any]:
    adapter = OpportunitySQLiteAdapter(db_path)
    detail = adapter.get_opportunity_detail(opportunity_id)
    prepare_detail_attachments(detail, output_dir)
    renderer = SkillDisplayRenderer()
    display = renderer.render(template_id, detail, theme=theme)
    result = {"detail": detail, "display_result": display}
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "detail.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / f"{template_id}.html").write_text(display["html"], encoding="utf-8")
        (out / f"{template_id}.md").write_text(display["markdown"], encoding="utf-8")
    adapter.close()
    return result


def run_manage(db_path: str | Path, change: dict[str, Any]) -> dict[str, Any]:
    adapter = OpportunitySQLiteAdapter(db_path)
    try:
        return adapter.manage(change)
    finally:
        adapter.close()
