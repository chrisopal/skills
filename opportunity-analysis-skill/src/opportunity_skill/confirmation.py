from __future__ import annotations

from typing import Any, Callable

from .assessment import normalize_rating


def collect_sales_confirmation_answers(
    questions: list[dict[str, Any]],
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
    *,
    answered_by: str = "商务负责人",
    limit: int | None = None,
) -> list[dict[str, Any]]:
    selected = questions[:limit] if limit else questions
    answers: list[dict[str, Any]] = []
    if not selected:
        return answers

    output_func("检测到需要商务确认的问题。请逐项回答；如果暂时不确定，可输入“未知”或“待确认”，系统仍会按未知评分继续评估。")
    for idx, question in enumerate(selected, start=1):
        label = question.get("label") or question.get("dimension_id") or f"问题{idx}"
        output_func("")
        output_func(f"[{idx}/{len(selected)}] {label}")
        output_func(str(question.get("question") or "请补充该维度的商务判断。"))
        raw_rating = input_func("评级（强/中/弱/未知/待确认，直接回车=未知）：").strip()
        rating = normalize_rating(raw_rating or "未知") or "unknown"
        answer_text = input_func("补充说明（可为空）：").strip()
        answers.append({
            "question_id": question.get("id"),
            "dimension_id": question.get("dimension_id"),
            "rating": rating,
            "answer_text": answer_text or "商务暂未确认，按未知处理。",
            "answered_by": answered_by,
            "source": "interactive_confirmation",
        })
    return answers
