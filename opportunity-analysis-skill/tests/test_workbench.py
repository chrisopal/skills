import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from opportunity_skill.pipeline import run_analyze
from opportunity_skill.workbench import make_server, _redact_paths


class WorkbenchHTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root / "opportunity.db"
        saved = run_analyze({"request_id": "seed", "materials": [{"evidence_id": "ev-seed", "content": "星河制造需要 MES 集成，联系人：王敏，业务负责人。"}]}, self.db)
        self.oid = saved["storage_result"]["opportunity_id"]
        self.server = make_server(self.db, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.temp.cleanup()

    def get(self, path):
        with urlopen(self.base + path) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def post(self, path, payload, *, token=None, origin=None):
        headers = {"Content-Type": "application/json", "Origin": origin or self.base}
        if token is not False:
            headers["X-Workbench-Token"] = self.server.session_token if token is None else token
        request = Request(self.base + path, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
        with urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def post_error(self, path, payload, **kwargs):
        try:
            self.post(path, payload, **kwargs)
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))
        self.fail("expected HTTP error")

    def test_list_detail_and_report_are_readable(self):
        status, listing = self.get("/api/opportunities")
        self.assertEqual(status, 200)
        self.assertEqual(listing["count"], 1)
        status, detail = self.get("/api/opportunity/" + self.oid)
        self.assertEqual(status, 200)
        self.assertEqual(detail["detail"]["opportunity"]["id"], self.oid)
        with urlopen(self.base + "/report/" + self.oid + "?theme=dark") as response:
            self.assertEqual(response.status, 200)
            self.assertIn("data-theme='dark'", response.read().decode("utf-8"))

    def test_radar_reuses_dimension_renderer_and_limits_parameters(self):
        with urlopen(self.base + "/radar/" + self.oid + "?category=delivery_confidence&theme=dark") as response:
            page = response.read().decode("utf-8")
            self.assertIn("data-theme='dark'", page)
            self.assertIn("<svg", page)
            self.assertIn("交付信心", page)
            self.assertNotIn("onclick", page)
        with self.assertRaises(HTTPError) as error:
            urlopen(self.base + "/radar/" + self.oid + "?category=untrusted")
        self.assertEqual(error.exception.code, 400)

    def test_manage_write_reads_back_and_rejects_stale_revision(self):
        payload = {"request_id": "wb-action", "opportunity_id": self.oid, "expected_revision": 1,
                   "actor": "工作台操作人", "operations": [{"type": "add_action", "title": "确认接口范围", "owner": "王敏", "due_date": "2026-10-20"}]}
        status, result = self.post("/api/manage", payload)
        self.assertEqual(status, 200)
        self.assertEqual(result["revision"], 2)
        _, detail = self.get("/api/opportunity/" + self.oid)
        self.assertEqual(detail["detail"]["lifecycle"]["next_action"]["title"], "确认接口范围")
        status, error = self.post_error("/api/manage", {**payload, "request_id": "stale", "title": "must not overwrite"})
        self.assertEqual(status, 409)
        self.assertEqual(error["error"]["code"], "revision_conflict")

    def test_analyze_feedback_persists_across_server_restart(self):
        payload = {"request_id": "wb-feedback", "opportunity_id": self.oid, "expected_revision": 1,
                   "actor": "工作台操作人", "account_hint": "星河制造",
                   "materials": [{"evidence_id": "ev-feedback", "type": "visit_note", "name": "客户反馈", "content": "客户确认下周安排方案评审。"}]}
        status, result = self.post("/api/analyze", payload)
        self.assertEqual(status, 200)
        self.assertEqual(result["revision"], 2)
        self.server.shutdown(); self.server.server_close(); self.thread.join(timeout=2)
        self.server = make_server(self.db, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"
        _, detail = self.get("/api/opportunity/" + self.oid)
        self.assertEqual(detail["detail"]["lifecycle"]["revision"], 2)
        self.assertIn("ev-feedback", [item["id"] for item in detail["detail"]["evidence"]])

    def test_competitor_ledger_and_score_confirmation_use_same_revision(self):
        competitor = {"request_id": "wb-competitor", "opportunity_id": self.oid, "expected_revision": 1,
                      "actor": "工作台操作人", "operations": [{"type": "record_competitor", "competitor_id": "cmp-1",
                      "name": "竞品甲", "position": "客户已有供应商", "strengths": ["价格低"],
                      "weaknesses": ["接口覆盖不足"], "response": "用接口验证回应", "status": "reported", "evidence": ["ev-seed"]}]}
        status, result = self.post("/api/manage", competitor)
        self.assertEqual(status, 200)
        self.assertEqual(result["revision"], 2)
        score = {"request_id": "wb-score", "opportunity_id": self.oid, "expected_revision": 2,
                 "actor": "工作台操作人", "sales_confirmation_answers":
                 [{"dimension_id": "customer_relationship", "rating": "strong", "answer_text": "客户内部赞助人已确认", "answered_by": "工作台操作人", "evidence_refs": ["ev-seed"]}]}
        status, result = self.post("/api/analyze", score)
        self.assertEqual(status, 200)
        self.assertEqual(result["revision"], 3)
        self.assertEqual(result["detail"]["lifecycle"]["competitors"][0]["competitor_id"], "cmp-1")
        answer = next(item for item in result["detail"]["sales_confirmation_answers"] if item["dimension_id"] == "customer_relationship")
        self.assertEqual(answer["answer_text"], "客户内部赞助人已确认")
        self.assertEqual(answer["evidence_refs"], ["ev-seed"])
        invalid = {**score, "request_id": "wb-score-invalid", "expected_revision": 3,
                   "sales_confirmation_answers": [{**score["sales_confirmation_answers"][0], "evidence_refs": ["does-not-exist"]}]}
        status, error = self.post_error("/api/analyze", invalid)
        self.assertEqual(status, 400)
        self.assertIn("evidence_refs", error["error"]["message"])

    def test_write_security_and_foreign_evidence(self):
        payload = {"request_id": "wb-security", "opportunity_id": self.oid, "expected_revision": 1,
                   "actor": "工作台操作人", "operations": [{"type": "confirm_fact", "fact_id": "need_confirmed", "value": True, "evidence": ["ev-missing"]}]}
        status, error = self.post_error("/api/manage", payload)
        self.assertEqual(status, 400)
        self.assertIn("evidence", error["error"]["message"])
        status, error = self.post_error("/api/manage", payload, origin="http://evil.example")
        self.assertEqual(status, 403)
        status, error = self.post_error("/api/manage", payload, token="wrong")
        self.assertEqual(status, 403)
        status, error = self.post_error("/api/manage", payload, token=False)
        self.assertEqual(status, 403)
        status, error = self.post_error("/api/analyze", {"request_id": "path", "materials": [{"content": "x", "file_path": "/etc/passwd"}]})
        self.assertEqual(status, 400)

    def test_host_body_limit_and_file_registration_are_rejected(self):
        request = Request(self.base + "/healthz", headers={"Host": "evil.example"})
        with self.assertRaises(HTTPError) as wrong_host:
            urlopen(request)
        self.assertEqual(wrong_host.exception.code, 400)
        request = Request(self.base + "/api/manage", data=b"{}", headers={"Origin": self.base, "X-Workbench-Token": self.server.session_token, "Content-Length": "1000001"}, method="POST")
        with self.assertRaises(HTTPError) as oversized:
            urlopen(request)
        self.assertEqual(oversized.exception.code, 413)
        payload = {"request_id": "forbidden-register", "opportunity_id": self.oid, "expected_revision": 1, "actor": "验证员", "operations": [{"type": "register_artifact", "artifact_id": "SOL"}]}
        status, error = self.post_error("/api/manage", payload)
        self.assertEqual(status, 400)
        self.assertIn("CLI", error["error"]["message"])
        _, detail = self.get("/api/opportunity/" + self.oid)
        self.assertEqual(detail["detail"]["lifecycle"]["revision"], 1)

    def test_nested_server_paths_are_not_exposed(self):
        value = {"id": "SOL-3", "metadata": {"presales_binding": {"project_path": "/private/project", "files": [{"file_path": "/private/deck.pptx", "sha256": "abc"}]}, "presales_call": {"runtime_path": "/private/runtime.py"}}}
        clean = _redact_paths(value)
        self.assertNotIn("/private", json.dumps(clean))
        self.assertEqual(clean["metadata"]["presales_binding"]["files"], [{"sha256": "abc"}])

    def test_loopback_only(self):
        with self.assertRaises(ValueError):
            make_server(self.db, host="0.0.0.0", port=0)


if __name__ == "__main__":
    unittest.main()
