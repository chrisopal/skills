"""Small, local-only editable workbench for the opportunity ledger.

The workbench deliberately stays a thin HTTP adapter around the existing
pipeline.  It does not introduce a second scoring or lifecycle model: reads
come from ``run_query``/``run_detail`` and writes use ``run_analyze`` or the
evidence-backed ``run_manage`` envelope.
"""

from __future__ import annotations

import json
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from .pipeline import run_analyze, run_detail, run_manage, run_query
from .renderer import SkillDisplayRenderer


ROOT = Path(__file__).resolve().parents[2]
WORKBENCH_ASSETS = ROOT / "display" / "workbench"
MAX_BODY_BYTES = 1_000_000
MAX_TEXT_BYTES = 100_000
FORBIDDEN_INPUT_KEYS = {
    "file_path",
    "path",
    "source_path",
    "archived_path",
    "original_path",
    "source_ref",
    "attachments",
}


def _json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _redact_paths(value: Any) -> Any:
    """Remove server filesystem paths before returning JSON to the browser."""
    if isinstance(value, dict):
        return {
            key: _redact_paths(item)
            for key, item in value.items()
            if key not in FORBIDDEN_INPUT_KEYS and not key.endswith("_path")
        }
    if isinstance(value, list):
        return [_redact_paths(item) for item in value]
    return value


def _validate_payload(value: Any, *, depth: int = 0) -> None:
    if depth > 8:
        raise ValueError("request payload is too deeply nested")
    if isinstance(value, dict):
        for key, item in value.items():
            if key in FORBIDDEN_INPUT_KEYS:
                raise ValueError(f"field is not accepted by the local workbench: {key}")
            if not isinstance(key, str) or len(key) > 80:
                raise ValueError("request field name is invalid")
            _validate_payload(item, depth=depth + 1)
    elif isinstance(value, list):
        if len(value) > 200:
            raise ValueError("request array is too large")
        for item in value:
            _validate_payload(item, depth=depth + 1)
    elif isinstance(value, str) and len(value.encode("utf-8")) > MAX_TEXT_BYTES:
        raise ValueError("request text is too large")


def _require_request_id(payload: dict[str, Any]) -> str:
    request_id = payload.get("request_id")
    if not isinstance(request_id, str) or not request_id.strip() or len(request_id) > 160:
        raise ValueError("request_id is required")
    return request_id.strip()


def _validate_analyze(payload: dict[str, Any]) -> dict[str, Any]:
    _require_request_id(payload)
    if payload.get("opportunity_id") is not None:
        if not isinstance(payload["opportunity_id"], str) or not payload["opportunity_id"].strip():
            raise ValueError("opportunity_id must be a non-empty string")
        if type(payload.get("expected_revision")) is not int:
            raise ValueError("expected_revision is required for an existing opportunity")
    elif payload.get("expected_revision", 0) != 0:
        raise ValueError("new opportunity expected_revision must be 0")
    materials = payload.get("materials", payload.get("evidence_list", []))
    answers = payload.get("sales_confirmation_answers", [])
    # An assessment answer may be recorded against an already-owned evidence
    # item.  Requiring a new material here would attempt to replace immutable
    # evidence on every retry of the score form.
    if not isinstance(materials, list) or (not materials and not (payload.get("opportunity_id") and isinstance(answers, list) and answers)):
        raise ValueError("at least one visit or feedback evidence item is required")
    return payload


def _validate_manage(payload: dict[str, Any]) -> dict[str, Any]:
    _require_request_id(payload)
    if not isinstance(payload.get("opportunity_id"), str) or not payload["opportunity_id"].strip():
        raise ValueError("opportunity_id is required")
    if type(payload.get("expected_revision")) is not int:
        raise ValueError("expected_revision is required")
    if not isinstance(payload.get("actor"), str) or not payload["actor"].strip():
        raise ValueError("actor is required")
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations must be a non-empty array")
    # Registering an artifact requires a server-side file binding.  The local
    # workbench intentionally leaves that controlled operation to the CLI.
    if any(isinstance(op, dict) and op.get("type") == "register_artifact" for op in operations):
        raise ValueError("register_artifact must be performed through the CLI with an approved file")
    return payload


class _WorkbenchHandler(BaseHTTPRequestHandler):
    server: "WorkbenchServer"
    protocol_version = "HTTP/1.1"

    def log_message(self, _format: str, *_args: Any) -> None:
        # Tokens and opportunity content must never be written to the process log.
        return

    @property
    def expected_host(self) -> str:
        return f"{self.server.host}:{self.server.server_port}"

    @property
    def expected_origin(self) -> str:
        return f"http://{self.expected_host}"

    def _send(self, status: int, body: Any, content_type: str = "application/json; charset=utf-8") -> None:
        data = body if isinstance(body, bytes) else (body.encode("utf-8") if isinstance(body, str) else _json_bytes(body))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(data)

    def _error(self, status: int, message: str, *, code: str = "error") -> None:
        self._send(status, {"ok": False, "error": {"code": code, "message": message}})

    def _check_host(self, *, require_origin: bool = False) -> bool:
        # Host and Origin are exact values.  This also rejects null/missing
        # Origin on mutating requests and prevents accidental CORS usage.
        if self.headers.get("Host") != self.expected_host:
            self._error(400, "Host header does not match this local session", code="invalid_host")
            return False
        if require_origin and self.headers.get("Origin") != self.expected_origin:
            self._error(403, "Origin is not allowed for this local session", code="invalid_origin")
            return False
        return True

    def _check_write_auth(self) -> bool:
        if not self._check_host(require_origin=True):
            return False
        if self.headers.get("X-Workbench-Token") != self.server.session_token:
            self._error(403, "workbench session token is invalid", code="invalid_token")
            return False
        return True

    def _read_json(self) -> dict[str, Any] | None:
        raw_length = self.headers.get("Content-Length")
        try:
            length = int(raw_length) if raw_length is not None else -1
        except ValueError:
            length = -1
        if length < 0 or length > MAX_BODY_BYTES:
            self._error(413, "request body is missing or too large", code="body_too_large")
            return None
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._error(400, "request body must be UTF-8 JSON", code="invalid_json")
            return None
        if not isinstance(payload, dict):
            self._error(400, "request body must be a JSON object", code="invalid_json")
            return None
        try:
            _validate_payload(payload)
        except ValueError as exc:
            self._error(400, str(exc), code="invalid_payload")
            return None
        return payload

    def do_GET(self) -> None:  # noqa: N802
        if not self._check_host():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/gtm":
                source = (WORKBENCH_ASSETS / "gtm.html").read_text(encoding="utf-8")
                self._send(200, source.replace("__WORKBENCH_TOKEN__", json.dumps(self.server.session_token)), "text/html; charset=utf-8")
                return
            if path.startswith("/api/gtm/"):
                from .gtm import GTMStore
                store = GTMStore(self.server.db_path)
                try:
                    if path == "/api/gtm/campaigns":
                        result = store.campaigns()
                    elif path.startswith("/api/gtm/campaign/"):
                        campaign_id = unquote(path.split("/", 4)[-1])
                        result = {"detail": store.detail(campaign_id, parse_qs(parsed.query).get("as_of", [None])[0])}
                    else:
                        self._error(404, "route not found", code="not_found")
                        return
                    self._send(200, {"ok": True, **_redact_paths(result)})
                finally:
                    store.close()
                return
            if path == "/":
                source = (WORKBENCH_ASSETS / "index.html").read_text(encoding="utf-8")
                config = json.dumps(self.server.session_token, ensure_ascii=False)
                self._send(200, source.replace("__WORKBENCH_TOKEN__", config), "text/html; charset=utf-8")
                return
            if path == "/css/default.css":
                self._send(200, (ROOT / "display" / "css" / "default.css").read_bytes(), "text/css; charset=utf-8")
                return
            if path in {"/assets/workbench.css", "/assets/workbench.js", "/assets/gtm.css", "/assets/gtm.js", "/assets/gtm-map.js", "/assets/china-map.json"}:
                filename = path.rsplit("/", 1)[-1]
                content_type = "text/css; charset=utf-8" if filename.endswith(".css") else "application/json; charset=utf-8" if filename.endswith(".json") else "text/javascript; charset=utf-8"
                self._send(200, (WORKBENCH_ASSETS / filename).read_bytes(), content_type)
                return
            if path == "/healthz":
                self._send(200, {"ok": True, "service": "opportunity-workbench"})
                return
            if path == "/api/opportunities":
                params = parse_qs(parsed.query)
                filters: dict[str, Any] = {}
                for key in ("status", "current_stage_id", "company_name"):
                    if params.get(key):
                        filters[key] = params[key][0]
                limit = min(max(int(params.get("limit", [50])[0]), 1), 100)
                result = run_query(self.server.db_path, {"query_type": "opportunity_search", "filters": filters, "sort": {"field": "updated_at", "order": "desc"}, "limit": limit})
                self._send(200, {"ok": True, "opportunities": _redact_paths(result["opportunities"]), "count": result["count"]})
                return
            if path.startswith("/api/opportunity/"):
                opportunity_id = unquote(path.split("/", 3)[-1])
                if not opportunity_id or "/" in opportunity_id:
                    self._error(400, "opportunity id is invalid", code="invalid_id")
                    return
                detail = run_detail(self.server.db_path, opportunity_id)["detail"]
                self._send(200, {"ok": True, "detail": _redact_paths(detail)})
                return
            if path.startswith("/radar/"):
                opportunity_id = unquote(path.split("/", 2)[-1])
                params = parse_qs(parsed.query)
                category = params.get("category", ["win_likelihood"])[0]
                theme = params.get("theme", ["light"])[0]
                if not opportunity_id or "/" in opportunity_id or category not in {"win_likelihood", "deal_attractiveness", "delivery_confidence"} or theme not in {"light", "dark"}:
                    raise ValueError("invalid radar selection")
                assessment = dict(run_detail(self.server.db_path, opportunity_id)["detail"]["commercial_assessment"])
                assessment["dimensions"] = [d for d in assessment.get("dimensions", []) if d.get("category") == category]
                radar = SkillDisplayRenderer()._assessment_radar_chart(assessment)
                page = (f"<!doctype html><html lang='zh-CN' data-ui='enterprise' data-theme='{theme}'>"
                        "<head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
                        "<link rel='stylesheet' href='/css/default.css'><title>判断维度雷达</title>"
                        "<style>body{margin:0;background:var(--ui-surface);color:var(--ui-text);font-family:var(--ui-font-sans)}"
                        ".ql-radar-panel{border:0!important;padding:0!important}.ql-radar-chart{max-width:380px!important}</style></head>"
                        f"<body>{radar}</body></html>")
                self._send(200, page, "text/html; charset=utf-8")
                return
            if path.startswith("/report/"):
                opportunity_id = unquote(path.split("/", 2)[-1])
                if not opportunity_id or "/" in opportunity_id:
                    self._error(400, "opportunity id is invalid", code="invalid_id")
                    return
                theme = parse_qs(parsed.query).get("theme", ["light"])[0]
                if theme not in {"light", "dark"}:
                    raise ValueError("invalid report theme")
                rendered = run_detail(self.server.db_path, opportunity_id, theme=theme)["display_result"]
                self._send(200, rendered["html"], "text/html; charset=utf-8")
                return
            self._error(404, "route not found", code="not_found")
        except KeyError as exc:
            self._error(404, str(exc), code="not_found")
        except (ValueError, TypeError) as exc:
            self._error(400, str(exc), code="invalid_request")
        except Exception:
            self._error(500, "workbench request failed", code="server_error")

    def do_POST(self) -> None:  # noqa: N802
        if not self._check_write_auth():
            return
        payload = self._read_json()
        if payload is None:
            return
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/gtm/manage":
                from .gtm import GTMStore
                _require_request_id(payload)
                store = GTMStore(self.server.db_path)
                try:
                    result = store.manage(payload)
                    self._send(200, {"ok": True, **_redact_paths(result)})
                finally:
                    store.close()
                return
            if parsed.path == "/api/analyze":
                _validate_analyze(payload)
                result = run_analyze(payload, self.server.db_path)
                opportunity_id = result["storage_result"]["opportunity_id"]
                detail = run_detail(self.server.db_path, opportunity_id)["detail"]
                self._send(200, {"ok": True, "opportunity_id": opportunity_id,
                                 "revision": detail["lifecycle"]["revision"],
                                 "detail": _redact_paths(detail)})
                return
            if parsed.path == "/api/manage":
                _validate_manage(payload)
                result = run_manage(self.server.db_path, payload)
                self._send(200, {"ok": True, "opportunity_id": result["opportunity_id"],
                                 "revision": result["current_revision"],
                                 "lifecycle": _redact_paths(result["lifecycle"])})
                return
            self._error(404, "route not found", code="not_found")
        except ValueError as exc:
            message = str(exc)
            status = 409 if "revision conflict" in message else 400
            code = "revision_conflict" if status == 409 else "invalid_request"
            self._error(status, message, code=code)
        except KeyError as exc:
            self._error(404, str(exc), code="not_found")
        except Exception:
            self._error(500, "workbench request failed", code="server_error")


class WorkbenchServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], db_path: str | Path):
        self.host = server_address[0]
        if self.host not in {"127.0.0.1", "localhost"}:
            raise ValueError("opportunity workbench only binds to loopback")
        self.db_path = Path(db_path)
        self.session_token = secrets.token_urlsafe(32)
        super().__init__(server_address, _WorkbenchHandler)


def make_server(db_path: str | Path, host: str = "127.0.0.1", port: int = 0) -> WorkbenchServer:
    """Create a testable local server.  ``port=0`` selects an ephemeral port."""
    return WorkbenchServer((host, port), db_path)


def serve(db_path: str | Path, host: str = "127.0.0.1", port: int = 8787) -> None:
    """Run the workbench until interrupted."""
    server = make_server(db_path, host, port)
    print(f"Opportunity workbench: http://{server.host}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Opportunity workbench stopped", flush=True)
    finally:
        server.server_close()


__all__ = ["WorkbenchServer", "make_server", "serve"]
