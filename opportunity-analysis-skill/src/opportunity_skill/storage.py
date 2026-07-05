from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Any
from .utils import now_iso, to_json, from_json, ensure_parent, new_id

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "storage" / "sqlite" / "schema.sql"


class OpportunitySQLiteAdapter:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        ensure_parent(self.db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.migrate()

    def close(self):
        self.conn.close()

    def migrate(self):
        sql = SCHEMA_PATH.read_text(encoding="utf-8")
        self.conn.executescript(sql)
        self.conn.commit()

    def upsert_account(self, account: dict[str, Any]) -> str:
        now = now_iso()
        account_id = account.get("id") or new_id("acc")
        self.conn.execute(
            """
            INSERT INTO accounts (id, company_name, normalized_name, industry, region, company_size, business_summary, current_systems, key_pain_points, source_confidence, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              company_name=excluded.company_name,
              normalized_name=excluded.normalized_name,
              industry=excluded.industry,
              region=excluded.region,
              company_size=excluded.company_size,
              business_summary=excluded.business_summary,
              current_systems=excluded.current_systems,
              key_pain_points=excluded.key_pain_points,
              source_confidence=excluded.source_confidence,
              updated_at=excluded.updated_at
            """,
            (
                account_id, account.get("company_name"), account.get("normalized_name"), account.get("industry"), account.get("region"),
                account.get("company_size"), account.get("business_summary"), to_json(account.get("current_systems", [])),
                to_json(account.get("key_pain_points", [])), account.get("source_confidence"), now, now
            )
        )
        self.conn.commit()
        return account_id

    def upsert_contact(self, contact: dict[str, Any]) -> str:
        now = now_iso()
        contact_id = contact.get("id") or new_id("ct")
        self.conn.execute(
            """
            INSERT INTO contacts (id, account_id, name, title, department, role_in_opportunity, phone, email, attitude, source_refs, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              account_id=excluded.account_id, name=excluded.name, title=excluded.title, department=excluded.department,
              role_in_opportunity=excluded.role_in_opportunity, phone=excluded.phone, email=excluded.email,
              attitude=excluded.attitude, source_refs=excluded.source_refs, updated_at=excluded.updated_at
            """,
            (
                contact_id, contact.get("account_id"), contact.get("name"), contact.get("title"), contact.get("department"),
                contact.get("role_in_opportunity"), contact.get("phone"), contact.get("email"), contact.get("attitude"),
                to_json(contact.get("source_refs", [])), now, now
            )
        )
        self.conn.commit()
        return contact_id

    def upsert_opportunity(self, opportunity: dict[str, Any]) -> str:
        now = now_iso()
        opp_id = opportunity.get("id") or new_id("opp")
        self.conn.execute(
            """
            INSERT INTO opportunities (id, account_id, name, stage, stage_status, core_need, budget_signal, budget_amount, expected_timeline, win_probability, score, score_level, risk_level, competitors, pain_points, requirements, missing_information, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              account_id=excluded.account_id, name=excluded.name, stage=excluded.stage, stage_status=excluded.stage_status,
              core_need=excluded.core_need, budget_signal=excluded.budget_signal, budget_amount=excluded.budget_amount,
              expected_timeline=excluded.expected_timeline, win_probability=excluded.win_probability, score=excluded.score,
              score_level=excluded.score_level, risk_level=excluded.risk_level, competitors=excluded.competitors,
              pain_points=excluded.pain_points, requirements=excluded.requirements, missing_information=excluded.missing_information,
              status=excluded.status, updated_at=excluded.updated_at
            """,
            (
                opp_id, opportunity.get("account_id"), opportunity.get("name"), opportunity.get("stage"), opportunity.get("stage_status"),
                opportunity.get("core_need"), opportunity.get("budget_signal"), opportunity.get("budget_amount"), opportunity.get("expected_timeline"),
                opportunity.get("win_probability"), opportunity.get("score"), opportunity.get("score_level"), opportunity.get("risk_level"),
                to_json(opportunity.get("competitors", [])), to_json(opportunity.get("pain_points", [])), to_json(opportunity.get("requirements", [])),
                to_json(opportunity.get("missing_information", [])), opportunity.get("status", "active"), now, now
            )
        )
        self.conn.commit()
        return opp_id

    def append_interaction(self, interaction: dict[str, Any]) -> str:
        iid = interaction.get("id") or new_id("int")
        self.conn.execute(
            """
            INSERT INTO interactions (id, account_id, opportunity_id, interaction_type, channel, title, summary, content, occurred_at, owner, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (iid, interaction.get("account_id"), interaction.get("opportunity_id"), interaction.get("interaction_type"), interaction.get("channel"), interaction.get("title"), interaction.get("summary"), interaction.get("content"), interaction.get("occurred_at"), interaction.get("owner"), now_iso())
        )
        self.conn.commit()
        return iid

    def append_evidence(self, evidence: dict[str, Any]) -> str:
        eid = evidence.get("evidence_id") or evidence.get("id") or new_id("ev")
        self.conn.execute(
            """
            INSERT OR REPLACE INTO evidence (id, source_type, source_name, source_ref, content, extracted_fields, confidence, requires_human_confirmation, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (eid, evidence.get("source_type"), evidence.get("source_name"), evidence.get("source_ref"), evidence.get("content"), to_json(evidence.get("extracted_fields", {})), evidence.get("confidence"), int(bool(evidence.get("requires_human_confirmation", False))), now_iso())
        )
        for item in evidence.get("archived_files", []) or []:
            item["evidence_id"] = eid
            self.append_evidence_file(item)
        self.conn.commit()
        return eid

    def append_evidence_file(self, item: dict[str, Any]) -> str:
        fid = item.get("id") or new_id("file")
        self.conn.execute(
            """
            INSERT OR REPLACE INTO evidence_files
              (id, evidence_id, original_path, archived_path, relative_path, file_name, display_name, mime_type, size_bytes, sha256, is_image, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                fid,
                item.get("evidence_id"),
                item.get("original_path"),
                item.get("archived_path"),
                item.get("relative_path"),
                item.get("file_name"),
                item.get("display_name"),
                item.get("mime_type"),
                item.get("size_bytes"),
                item.get("sha256"),
                int(bool(item.get("is_image", False))),
                now_iso(),
            ),
        )
        return fid

    def link_evidence_to_field(self, item: dict[str, Any]) -> str:
        mid = item.get("id") or new_id("map")
        self.conn.execute(
            """
            INSERT INTO opportunity_evidence_map (id, opportunity_id, evidence_id, field_name, field_value, status, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (mid, item.get("opportunity_id"), item.get("evidence_id"), item.get("field_name"), item.get("field_value"), item.get("status"), item.get("confidence"), now_iso())
        )
        self.conn.commit()
        return mid

    def create_risk(self, risk: dict[str, Any]) -> str:
        rid = risk.get("id") or new_id("risk")
        now = now_iso()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO risks (id, opportunity_id, risk_type, risk_level, description, mitigation, evidence_refs, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rid, risk.get("opportunity_id"), risk.get("risk_type"), risk.get("risk_level"), risk.get("description"), risk.get("mitigation"), to_json(risk.get("evidence_refs", [])), now, now)
        )
        self.conn.commit()
        return rid

    def create_next_action(self, action: dict[str, Any]) -> str:
        aid = action.get("id") or new_id("act")
        now = now_iso()
        self.conn.execute(
            """
            INSERT OR REPLACE INTO next_actions (id, opportunity_id, action_title, action_detail, priority, owner, deadline_suggestion, status, reason, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (aid, action.get("opportunity_id"), action.get("action_title"), action.get("action_detail"), action.get("priority"), action.get("owner"), action.get("deadline_suggestion"), action.get("status", "open"), action.get("reason"), now, now)
        )
        self.conn.commit()
        return aid

    def save_skill_run(self, run: dict[str, Any]) -> str:
        rid = run.get("id") or new_id("run")
        self.conn.execute(
            """
            INSERT INTO skill_runs (id, skill_name, input_summary, output_summary, structured_output, display_output_path, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (rid, run.get("skill_name", "opportunity-analysis-skill"), run.get("input_summary"), run.get("output_summary"), run.get("structured_output"), run.get("display_output_path"), run.get("status", "success"), now_iso())
        )
        self.conn.commit()
        return rid

    def save_rendered_view(self, object_type: str, object_id: str, template_id: str, html_content: str, markdown_content: str) -> str:
        vid = new_id("view")
        now = now_iso()
        self.conn.execute(
            """
            INSERT INTO rendered_views (id, object_type, object_id, template_id, html_content, markdown_content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (vid, object_type, object_id, template_id, html_content, markdown_content, now, now)
        )
        self.conn.commit()
        return vid

    def save_structured_data(self, data: dict[str, Any]) -> dict[str, Any]:
        sd = data["structured_data"] if "structured_data" in data else data
        account_id = self.upsert_account(sd["account"])
        for ev in sd.get("evidence", []):
            self.append_evidence(ev)
        for c in sd.get("contacts", []):
            c["account_id"] = account_id
            self.upsert_contact(c)
        opp = sd["opportunity"]
        opp["account_id"] = account_id
        opportunity_id = self.upsert_opportunity(opp)
        mapped_evidence_ids = {item.get("evidence_id") for item in sd.get("evidence_map", [])}
        for item in sd.get("evidence_map", []):
            item["opportunity_id"] = opportunity_id
            self.link_evidence_to_field(item)
        for ev in sd.get("evidence", []):
            evidence_id = ev.get("evidence_id") or ev.get("id")
            if evidence_id and evidence_id not in mapped_evidence_ids:
                self.link_evidence_to_field({
                    "opportunity_id": opportunity_id,
                    "evidence_id": evidence_id,
                    "field_name": "source_material",
                    "field_value": ev.get("source_name"),
                    "status": "confirmed",
                    "confidence": ev.get("confidence"),
                })
        for risk in sd.get("risks", []):
            risk["opportunity_id"] = opportunity_id
            self.create_risk(risk)
        for action in sd.get("next_actions", []):
            action["opportunity_id"] = opportunity_id
            self.create_next_action(action)
        return {"adapter": "sqlite", "saved": True, "account_id": account_id, "opportunity_id": opportunity_id, "db_path": str(self.db_path)}

    def query_opportunities(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        filters = query.get("filters", {})
        sql = """
        SELECT o.*, a.company_name, a.industry, a.region
        FROM opportunities o
        JOIN accounts a ON a.id = o.account_id
        WHERE 1=1
        """
        params = []
        if filters.get("account_id"):
            sql += " AND o.account_id = ?"
            params.append(filters["account_id"])
        if filters.get("company_name"):
            sql += " AND a.company_name LIKE ?"
            params.append(f"%{filters['company_name']}%")
        if filters.get("stage"):
            sql += " AND o.stage = ?"
            params.append(filters["stage"])
        if filters.get("risk_level"):
            sql += " AND o.risk_level = ?"
            params.append(filters["risk_level"])
        if filters.get("min_score") is not None:
            sql += " AND o.score >= ?"
            params.append(int(filters["min_score"]))
        if filters.get("max_score") is not None:
            sql += " AND o.score <= ?"
            params.append(int(filters["max_score"]))
        if filters.get("status"):
            sql += " AND o.status = ?"
            params.append(filters["status"])
        if filters.get("updated_after"):
            sql += " AND o.updated_at >= ?"
            params.append(filters["updated_after"])
        sort = query.get("sort", {})
        allowed_sort = {"score": "o.score", "updated_at": "o.updated_at", "created_at": "o.created_at", "stage": "o.stage"}
        field = allowed_sort.get(sort.get("field"), "o.updated_at")
        order = "ASC" if sort.get("order") == "asc" else "DESC"
        sql += f" ORDER BY {field} {order} LIMIT ?"
        params.append(int(query.get("limit", 50)))
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_opportunity_summary(r) for r in rows]

    def get_opportunity_detail(self, opportunity_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            """
            SELECT o.*, a.company_name, a.normalized_name, a.industry, a.region, a.company_size, a.business_summary, a.current_systems, a.key_pain_points, a.source_confidence
            FROM opportunities o
            JOIN accounts a ON a.id = o.account_id
            WHERE o.id = ?
            """,
            (opportunity_id,)
        ).fetchone()
        if not row:
            raise KeyError(f"Opportunity not found: {opportunity_id}")
        account = {
            "id": row["account_id"], "company_name": row["company_name"], "normalized_name": row["normalized_name"],
            "industry": row["industry"], "region": row["region"], "company_size": row["company_size"],
            "business_summary": row["business_summary"], "current_systems": from_json(row["current_systems"]),
            "key_pain_points": from_json(row["key_pain_points"]), "source_confidence": row["source_confidence"]
        }
        opportunity = self._row_to_opportunity_summary(row)
        contacts = [dict(r) for r in self.conn.execute("SELECT * FROM contacts WHERE account_id = ?", (row["account_id"],)).fetchall()]
        for c in contacts:
            c["source_refs"] = from_json(c.get("source_refs"))
        risks = [dict(r) for r in self.conn.execute("SELECT * FROM risks WHERE opportunity_id = ?", (opportunity_id,)).fetchall()]
        for r in risks:
            r["evidence_refs"] = from_json(r.get("evidence_refs"))
        actions = [dict(r) for r in self.conn.execute("SELECT * FROM next_actions WHERE opportunity_id = ?", (opportunity_id,)).fetchall()]
        maps = [dict(r) for r in self.conn.execute("SELECT * FROM opportunity_evidence_map WHERE opportunity_id = ?", (opportunity_id,)).fetchall()]
        ev_ids = list(dict.fromkeys(m["evidence_id"] for m in maps))
        evidence = []
        if ev_ids:
            placeholders = ",".join("?" for _ in ev_ids)
            evidence = [dict(r) for r in self.conn.execute(f"SELECT * FROM evidence WHERE id IN ({placeholders})", ev_ids).fetchall()]
            files = [dict(r) for r in self.conn.execute(f"SELECT * FROM evidence_files WHERE evidence_id IN ({placeholders})", ev_ids).fetchall()]
        else:
            files = []
        files_by_evidence: dict[str, list[dict[str, Any]]] = {}
        for item in files:
            item["is_image"] = bool(item.get("is_image"))
            files_by_evidence.setdefault(item.get("evidence_id"), []).append(item)
        for ev in evidence:
            ev["extracted_fields"] = from_json(ev.get("extracted_fields"))
            ev["archived_files"] = files_by_evidence.get(ev.get("id"), [])
        return {"account": account, "opportunity": opportunity, "contacts": contacts, "risks": risks, "next_actions": actions, "evidence": evidence, "evidence_map": maps, "archived_files": files}

    def _row_to_opportunity_summary(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"], "account_id": row["account_id"], "name": row["name"], "stage": row["stage"],
            "stage_status": row["stage_status"], "core_need": row["core_need"], "budget_signal": row["budget_signal"],
            "budget_amount": row["budget_amount"], "expected_timeline": row["expected_timeline"],
            "win_probability": row["win_probability"], "win_probability_percent": int(round((row["win_probability"] or 0) * 100)),
            "score": row["score"], "score_level": row["score_level"], "risk_level": row["risk_level"],
            "competitors": from_json(row["competitors"]), "pain_points": from_json(row["pain_points"]),
            "requirements": from_json(row["requirements"]), "missing_information": from_json(row["missing_information"]),
            "status": row["status"], "created_at": row["created_at"], "updated_at": row["updated_at"],
            "company_name": row["company_name"] if "company_name" in row.keys() else None,
            "industry": row["industry"] if "industry" in row.keys() else None,
            "region": row["region"] if "region" in row.keys() else None,
        }
