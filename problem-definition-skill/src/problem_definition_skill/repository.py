from __future__ import annotations
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Repository:
    def __init__(self, db_path: str, schema_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(Path(schema_path).read_text(encoding="utf-8"))

    def save(self, result: dict[str, Any]) -> str:
        structured = result["structured_data"]
        pid = f"pd_{uuid.uuid4().hex[:12]}"
        t = now()
        pd = structured["problem_definition"]
        self.conn.execute(
            """INSERT INTO problem_definitions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid,
                structured.get("account_id"),
                structured.get("opportunity_id"),
                structured["case_name"],
                pd["surface_problem"]["value"],
                pd["surface_problem"]["status"],
                pd["deep_problem"]["value"],
                pd["deep_problem"]["status"],
                pd["decision_problem"]["value"],
                pd["decision_problem"]["status"],
                json.dumps(pd["business_impacts"], ensure_ascii=False),
                json.dumps(pd["constraints"], ensure_ascii=False),
                json.dumps(pd["assumptions"], ensure_ascii=False),
                json.dumps(pd["missing_information"], ensure_ascii=False),
                json.dumps(pd["solution_entry_points"], ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                t,
                t,
            ),
        )
        for item in pd["success_criteria"]:
            self.conn.execute(
                "INSERT INTO success_criteria VALUES (?,?,?,?,?,?,?,?)",
                (
                    f"sc_{uuid.uuid4().hex[:12]}", pid, item.get("dimension"), item["criterion"],
                    item.get("metric"), item.get("target_value"), item.get("status"), t,
                ),
            )
        for item in pd["assumptions"]:
            self.conn.execute(
                "INSERT INTO problem_hypotheses VALUES (?,?,?,?,?,?)",
                (f"ph_{uuid.uuid4().hex[:12]}", pid, item["hypothesis"], item.get("status"), item.get("validation_method"), t),
            )
        for question in structured["clarification_questions"]:
            self.conn.execute(
                "INSERT INTO clarification_questions VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    f"cq_{uuid.uuid4().hex[:12]}", pid, question["question"], question.get("purpose"),
                    question.get("target_role"), question.get("priority"), question.get("related_issue"), "open", t,
                ),
            )
        for item in structured["evidence_map"]:
            for source_id in item.get("source_ids", []):
                self.conn.execute(
                    "INSERT INTO problem_evidence_map VALUES (?,?,?,?,?,?,?,?)",
                    (f"em_{uuid.uuid4().hex[:12]}", pid, item["field_name"], source_id, None, None, item.get("confidence"), t),
                )
        self.conn.commit()
        return pid

    def query(self, keyword: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        sql = "SELECT id, case_name, surface_problem, deep_problem, decision_problem, created_at FROM problem_definitions"
        params: list[Any] = []
        if keyword:
            sql += " WHERE case_name LIKE ? OR surface_problem LIKE ? OR deep_problem LIKE ? OR decision_problem LIKE ?"
            value = f"%{keyword}%"
            params = [value, value, value, value]
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        return [dict(row) for row in self.conn.execute(sql, params).fetchall()]

    def get_detail(self, problem_definition_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            "SELECT raw_output_json FROM problem_definitions WHERE id = ?", (problem_definition_id,)
        ).fetchone()
        if not row:
            return None
        return json.loads(row["raw_output_json"])
