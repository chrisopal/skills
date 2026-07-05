from __future__ import annotations
import json
from pathlib import Path
from typing import Any
from .extractor import analyze
from .storage import OpportunitySQLiteAdapter
from .renderer import SkillDisplayRenderer


def run_analyze(input_data: dict[str, Any], db_path: str | Path, output_dir: str | Path | None = None, template_id: str = "opportunity_card") -> dict[str, Any]:
    result = analyze(input_data)
    adapter = OpportunitySQLiteAdapter(db_path)
    storage_result = adapter.save_structured_data(result)
    detail = adapter.get_opportunity_detail(storage_result["opportunity_id"])
    renderer = SkillDisplayRenderer()
    display = renderer.render(template_id, detail)

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


def run_query(db_path: str | Path, query_json: dict[str, Any], output_dir: str | Path | None = None, render_html: bool = False) -> dict[str, Any]:
    adapter = OpportunitySQLiteAdapter(db_path)
    opportunities = adapter.query_opportunities(query_json)
    result = {"query": query_json, "opportunities": opportunities, "count": len(opportunities)}
    if render_html:
        renderer = SkillDisplayRenderer()
        display = renderer.render("opportunity_kanban", result)
        result["display_result"] = display
        if output_dir:
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            (out / "query_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            (out / "opportunity_kanban.html").write_text(display["html"], encoding="utf-8")
            (out / "opportunity_kanban.md").write_text(display["markdown"], encoding="utf-8")
    adapter.close()
    return result


def run_detail(db_path: str | Path, opportunity_id: str, output_dir: str | Path | None = None, template_id: str = "opportunity_detail") -> dict[str, Any]:
    adapter = OpportunitySQLiteAdapter(db_path)
    detail = adapter.get_opportunity_detail(opportunity_id)
    renderer = SkillDisplayRenderer()
    display = renderer.render(template_id, detail)
    result = {"detail": detail, "display_result": display}
    if output_dir:
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / "detail.json").write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
        (out / f"{template_id}.html").write_text(display["html"], encoding="utf-8")
        (out / f"{template_id}.md").write_text(display["markdown"], encoding="utf-8")
    adapter.close()
    return result
