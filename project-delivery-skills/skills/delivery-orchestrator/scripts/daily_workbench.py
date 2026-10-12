#!/usr/bin/env python3
"""Local-only HTTP workbench for daily delivery operations."""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
import secrets
import sys
from urllib.parse import parse_qs, urlsplit

# Keep direct/spec-based loading dependency-free: the sibling operations module
# is the only local import and is not installed as a package.
if str(Path(__file__).parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).parent))

from daily_operations import (
    ConflictError,
    record_change,
    record_hours,
    record_progress,
    record_risk,
    runtime,
    state,
    weekly_report,
)


MAX_BODY_BYTES = 64 * 1024
ASSET = Path(__file__).resolve().parent.parent / "assets" / "daily-workbench.html"


class WorkbenchServer(ThreadingHTTPServer):
    """A loopback-only server with a per-process CSRF token."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, project, server_address=("127.0.0.1", 0), handler_class=None):
        if server_address[0] not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("The daily workbench only binds to loopback")
        self.project = runtime.root_path(project)
        self.csrf_token = secrets.token_urlsafe(32)
        self.max_body_bytes = MAX_BODY_BYTES
        super().__init__(server_address, handler_class or WorkbenchHandler)


class WorkbenchHandler(BaseHTTPRequestHandler):
    server: WorkbenchServer
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass

    def _host_candidates(self):
        port = self.server.server_address[1]
        return {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}

    def _check_origin_and_host(self, *, unsafe=False):
        host = self.headers.get("Host", "")
        if host not in self._host_candidates():
            self._send_json(400, {"error": "Invalid Host"})
            return False
        origin = self.headers.get("Origin")
        if origin:
            if origin not in {f"http://{item}" for item in self._host_candidates()}:
                self._send_json(403, {"error": "Origin rejected"})
                return False
        elif unsafe:
            self._send_json(403, {"error": "Origin required"})
            return False
        return True

    def _send_bytes(self, status: int, content: bytes, content_type: str, *, disposition: str | None = None):
        if status >= 400:
            self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, status: int, value: dict):
        self._send_bytes(status, json.dumps(value, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _read_json(self):
        raw_length = self.headers.get("Content-Length")
        if raw_length is None:
            raise ValueError("Content-Length is required")
        try:
            length = int(raw_length)
        except ValueError:
            raise ValueError("Invalid Content-Length") from None
        if length < 0 or length > self.server.max_body_bytes:
            self._send_json(413, {"error": "Payload too large"})
            return None
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValueError("Incomplete request body")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Request body must be UTF-8 JSON") from None
        if not isinstance(value, dict):
            raise ValueError("Request body must be a JSON object")
        return value

    def _csrf(self):
        if self.headers.get("X-CSRF-Token") != self.server.csrf_token:
            self._send_json(403, {"error": "CSRF token rejected"})
            return False
        return True

    def do_GET(self):
        if not self._check_origin_and_host():
            return
        parsed = urlsplit(self.path)
        if any(part in {"..", "."} for part in parsed.path.split("/")):
            self._send_json(404, {"error": "Not found"})
            return
        try:
            if parsed.path in {"/", "/assets/daily-workbench.html"}:
                self._send_bytes(200, ASSET.read_bytes(), "text/html; charset=utf-8")
            elif parsed.path == "/api/csrf":
                self._send_json(200, {"csrf_token": self.server.csrf_token})
            elif parsed.path == "/api/state":
                self._send_json(200, state(self.server.project))
            elif parsed.path == "/api/report":
                query = parse_qs(parsed.query)
                audience = query.get("audience", ["internal"])[0]
                period = query.get("period", [None])[0]
                report = weekly_report(self.server.project, period, audience)
                safe_audience = "customer-draft" if audience == "customer" else "internal"
                self._send_bytes(200, report.encode("utf-8"), "text/markdown; charset=utf-8",
                                 disposition=f'attachment; filename="weekly-{safe_audience}.md"')
            else:
                self._send_json(404, {"error": "Not found"})
        except (ValueError, OSError, KeyError) as exc:
            self._send_json(400, {"error": str(exc)})

    def do_POST(self):
        if not self._check_origin_and_host(unsafe=True) or not self._csrf():
            return
        parsed = urlsplit(self.path)
        try:
            payload = self._read_json()
            if payload is None:
                return
            expected = payload.pop("expected_revision", None)
            expected_fingerprint = payload.pop("expected_registry_fingerprint", None)
            if parsed.path == "/api/progress":
                result = record_progress(self.server.project, payload, expected, expected_fingerprint)
            elif parsed.path == "/api/hours":
                result = record_hours(self.server.project, payload, expected, expected_fingerprint)
            elif parsed.path == "/api/risks":
                result = record_risk(self.server.project, payload, expected, expected_fingerprint)
            elif parsed.path == "/api/changes":
                result = record_change(self.server.project, payload, expected, expected_fingerprint)
            else:
                self._send_json(404, {"error": "Not found"})
                return
            self._send_json(201, result)
        except ConflictError as exc:
            self._send_json(409, {"error": str(exc), "current_revision": exc.current_revision,
                                  "current_registry_fingerprint": exc.current_fingerprint})
        except (ValueError, OSError, KeyError, TypeError) as exc:
            self._send_json(400, {"error": str(exc)})


def serve(project, host: str = "127.0.0.1", port: int = 8787):
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("The daily workbench only binds to loopback")
    server = WorkbenchServer(project, (host, port))
    print(f"Daily workbench listening at http://{host}:{server.server_address[1]}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    args = parser.parse_args()
    serve(args.project, args.host, args.port)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
