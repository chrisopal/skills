"""HTTP security and persistence tests for the loopback daily workbench."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/delivery-orchestrator/scripts"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


runtime = load("daily_http_runtime", SCRIPTS / "runtime.py")
daily = load("daily_http_operations", SCRIPTS / "daily_operations.py")
workbench = load("daily_workbench_test_module", SCRIPTS / "daily_workbench.py")


class DailyWorkbenchHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "project"
        runtime.init_project(self.project, "HTTP-001")
        self.source = Path(self.temp.name) / "evidence.txt"
        self.source.write_text("registered evidence", encoding="utf-8")
        self.evidence_ref = runtime.source(self.project, self.source, "SRC")
        self.server = workbench.WorkbenchServer(self.project, ("127.0.0.1", 0))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.host = f"127.0.0.1:{self.server.server_address[1]}"
        self.origin = self.base

    def fingerprint(self):
        status, _, body = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        return json.loads(body)["registry_fingerprint"]

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, method, path, payload=None, *, csrf=None, origin=None, host=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {"Host": host or self.host}
        if origin is not None:
            headers["Origin"] = origin
        if csrf is not None:
            headers["X-CSRF-Token"] = csrf
        if data is not None:
            headers["Content-Type"] = "application/json"
        response = urlopen(Request(self.base + path, data=data, headers=headers, method=method), timeout=3)
        return response.status, response.headers, response.read()

    def error_request(self, method, path, payload=None, **kwargs):
        with self.assertRaises(HTTPError) as context:
            self.request(method, path, payload, **kwargs)
        return context.exception.code, json.loads(context.exception.read().decode("utf-8"))

    def test_workbench_home_is_served_from_installed_asset(self):
        status, headers, body = self.request('GET','/')
        self.assertEqual(status,200)
        self.assertIn('text/html',headers['Content-Type'])
        self.assertIn('进度',body.decode('utf-8'))
        self.assertIn('工时',body.decode('utf-8'))

    def test_http_persists_and_reloads_actual_ledgers(self):
        status, _, body = self.request("GET", "/api/csrf")
        self.assertEqual(status, 200)
        csrf = json.loads(body)["csrf_token"]
        payload = {"entry_id": "OP1", "date": "2026-10-12", "work_package_id": "WP1", "status": "completed", "summary": "实际完成", "evidence_refs": [self.evidence_ref], "customer_visible": True, "expected_revision": 0, "expected_registry_fingerprint": self.fingerprint()}
        status, _, _ = self.request("POST", "/api/progress", payload, csrf=csrf, origin=self.origin)
        self.assertEqual(status, 201)
        status, _, body = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        current = json.loads(body)
        self.assertEqual(current["active_ledgers"]["DAILY-PROGRESS"], 1)
        reopened = daily.state(self.project)
        self.assertEqual(reopened["active_ledgers"]["DAILY-PROGRESS"], 1)
        status, headers, report = self.request("GET", "/api/report?audience=customer")
        self.assertEqual(status, 200)
        self.assertIn("attachment", headers.get("Content-Disposition", ""))
        self.assertIn("实际完成", report.decode("utf-8"))

    def test_origin_host_csrf_and_public_binding_guards(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        with self.assertRaises(ValueError):
            workbench.WorkbenchServer(self.project, ("0.0.0.0", 0))
        base = {"work_package_id": "WP1", "summary": "x", "expected_revision": 0, "expected_registry_fingerprint": self.fingerprint()}
        code, body = self.error_request("POST", "/api/progress", base, origin=self.origin, csrf="wrong")
        self.assertEqual((code, body["error"]), (403, "CSRF token rejected"))
        code, body = self.error_request("POST", "/api/progress", base, csrf=self.server.csrf_token, origin="http://evil.test")
        self.assertEqual((code, body["error"]), (403, "Origin rejected"))
        code, body = self.error_request("GET", "/api/state", host="evil.test")
        self.assertEqual((code, body["error"]), (400, "Invalid Host"))
        code, body = self.error_request("POST", "/api/progress", base, csrf=self.server.csrf_token)
        self.assertEqual((code, body["error"]), (403, "Origin required"))

    def test_hours_and_change_endpoints_keep_authority_boundaries(self):
        csrf = json.loads(self.request("GET", "/api/csrf")[2])["csrf_token"]
        common = {"person": "A", "work_package_id": "WP1", "hours": 1, "status": "approved", "expected_revision": 0, "expected_registry_fingerprint": self.fingerprint()}
        code, body = self.error_request("POST", "/api/hours", common, csrf=csrf, origin=self.origin)
        self.assertEqual(code, 400)
        self.assertIn("submitted", body["error"])
        proposal = {"change_id": "CHG-1", "state": "approved", "reason": "no", "affected_ids": ["PLAN"], "impact": {}, "expected_registry_fingerprint": self.fingerprint()}
        code, body = self.error_request("POST", "/api/changes", proposal, csrf=csrf, origin=self.origin)
        self.assertEqual(code, 400)
        self.assertIn("proposed", body["error"])

    def test_payload_limits_invalid_input_and_stale_second_writer(self):
        csrf = json.loads(self.request("GET", "/api/csrf")[2])["csrf_token"]
        oversized = {"work_package_id": "WP1", "summary": "x" * (workbench.MAX_BODY_BYTES + 10), "expected_revision": 0, "expected_registry_fingerprint": self.fingerprint()}
        code, body = self.error_request("POST", "/api/progress", oversized, csrf=csrf, origin=self.origin)
        self.assertEqual((code, body["error"]), (413, "Payload too large"))
        first = {"entry_id": "OP1", "work_package_id": "WP1", "summary": "one", "expected_revision": 0, "expected_registry_fingerprint": self.fingerprint()}
        self.request("POST", "/api/progress", first, csrf=csrf, origin=self.origin)
        stale = {"entry_id": "OP2", "work_package_id": "WP1", "summary": "two", "expected_revision": 0, "expected_registry_fingerprint": first["expected_registry_fingerprint"]}
        code, body = self.error_request("POST", "/api/progress", stale, csrf=csrf, origin=self.origin)
        self.assertEqual(code, 409)
        self.assertEqual(body["current_revision"], 0)
        self.assertTrue(body["current_registry_fingerprint"])
        injection = {"entry_id": "OP2", "work_package_id": "WP1", "summary": "<script>alert(1)</script>", "expected_revision": 1, "expected_registry_fingerprint": self.fingerprint()}
        self.request("POST", "/api/progress", injection, csrf=csrf, origin=self.origin)
        html = (SCRIPTS.parent / "assets/daily-workbench.html").read_text(encoding="utf-8")
        self.assertIn("function escapeHtml", html)
        self.assertNotIn("innerHTML = item.summary", html)


if __name__ == "__main__":
    unittest.main()
