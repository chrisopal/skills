from __future__ import annotations
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


def _template_filename(template_id: str) -> str:
    return template_id if template_id.endswith(".html") else f"{template_id}.html"


def render(result: dict, template_dir: str, template_id: str = "problem_definition_card") -> str:
    env = Environment(loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html", "xml"]))
    template = env.get_template(_template_filename(template_id))
    structured = result["structured_data"]
    return template.render(
        case_name=structured["case_name"],
        pd=structured["problem_definition"],
        questions=structured["clarification_questions"],
        evidence=structured.get("evidence", []),
    )


def markdown(result: dict) -> str:
    structured = result["structured_data"]
    pd = structured["problem_definition"]
    lines = [
        f"# {structured['case_name']}", "", "## 表层问题", pd["surface_problem"]["value"], "",
        "## 深层问题", pd["deep_problem"]["value"], "", "## 决策问题", pd["decision_problem"]["value"], "",
        "## 业务影响",
    ]
    lines += [f"- {item}" for item in pd["business_impacts"]]
    lines += ["", "## 澄清问题"]
    lines += [f"- {q['question']}（{q['target_role']}，{q['priority']}）" for q in structured["clarification_questions"]]
    return "\n".join(lines)
