"""Protocol-level tests for the explicit, bounded PaddleOCR service path."""
from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

import fitz

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import bidkit  # noqa: E402
import extract_sources  # noqa: E402
from paddle_ocr import PaddleOCRError, PaddleOCRService, validate_service_url  # noqa: E402
from validate_output import validate  # noqa: E402


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


def response_payload(score: float = 0.96, text: str = "扫描页文字") -> dict:
    return {
        "result": {
            "ocrResults": [
                {
                    "prunedResult": {
                        "rec_texts": [text],
                        "rec_scores": [score],
                        "rec_polys": [[[0, 0], [20, 0], [20, 10], [0, 10]]],
                    }
                }
            ]
        }
    }


class OCRHandler(BaseHTTPRequestHandler):
    calls: list[dict] = []
    payload: object = response_payload()
    status = 200
    redirect_to: str | None = None
    delay = 0.0

    def log_message(self, *_args):  # type: ignore[no-untyped-def]
        return

    def do_POST(self):  # type: ignore[no-untyped-def]
        if OCRHandler.delay:
            time.sleep(OCRHandler.delay)
        if self.redirect_to:
            self.send_response(302)
            self.send_header("Location", self.redirect_to)
            self.end_headers()
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        OCRHandler.calls.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "body": json.loads(raw),
            }
        )
        body = json.dumps(OCRHandler.payload, ensure_ascii=False).encode("utf-8")
        self.send_response(OCRHandler.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class LocalOCRServer:
    def __enter__(self):
        OCRHandler.calls = []
        OCRHandler.payload = response_payload()
        OCRHandler.status = 200
        OCRHandler.redirect_to = None
        OCRHandler.delay = 0.0
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), OCRHandler)
        self.server.daemon_threads = False
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/ocr"


class ClientTests(unittest.TestCase):
    def test_invalid_key_is_rejected_without_exposing_its_value(self):
        for key in ('TEST-SECRET\nInjected: value', 'TEST-SECRET-中文'):
            with self.subTest(key_type='invalid'), self.assertRaises(PaddleOCRError) as raised:
                PaddleOCRService('http://localhost:8080/ocr', api_key=key)
            self.assertNotIn('TEST-SECRET', str(raised.exception))

    def test_url_policy(self):
        self.assertEqual(validate_service_url("http://localhost:8080/ocr"), "http://localhost:8080/ocr")
        with self.assertRaisesRegex(PaddleOCRError, "allow-remote"):
            validate_service_url("https://ocr.example.test/ocr")
        with self.assertRaises(PaddleOCRError):
            validate_service_url("http://ocr.example.test/ocr", allow_remote=True)
        with self.assertRaises(PaddleOCRError):
            validate_service_url("https://user:secret@ocr.example.test/ocr", allow_remote=True)
        with self.assertRaises(PaddleOCRError):
            validate_service_url("https://ocr.example.test/ocr?key=secret", allow_remote=True)

    def test_protocol_auth_and_png_payload(self):
        with LocalOCRServer() as server:
            client = PaddleOCRService(server.url, "test-key", "token")
            result = client.recognize(PNG)
        self.assertEqual(result.text, "扫描页文字")
        self.assertAlmostEqual(result.confidence, 0.96)
        self.assertEqual(OCRHandler.calls[0]["authorization"], "Token test-key")
        submitted = base64.b64decode(OCRHandler.calls[0]["body"]["file"])
        self.assertEqual(submitted, PNG)
        self.assertEqual(OCRHandler.calls[0]["body"]["fileType"], 1)

    def test_malformed_empty_and_count_mismatch_fail_closed(self):
        bool_score = response_payload()
        bool_score["result"]["ocrResults"][0]["prunedResult"]["rec_scores"] = [True]
        short_polygon = response_payload()
        short_polygon["result"]["ocrResults"][0]["prunedResult"]["rec_polys"] = [[[0, 0]]]
        nonfinite_polygon = response_payload()
        nonfinite_polygon["result"]["ocrResults"][0]["prunedResult"]["rec_polys"] = [
            [[0, 0], [20, 0], [float("nan"), 10]]
        ]
        bad_payloads = [
            {},
            {"result": {"ocrResults": []}},
            {"result": {"ocrResults": [{"prunedResult": {"rec_texts": ["x"], "rec_scores": [], "rec_polys": []}}]}},
            {"result": {"ocrResults": [{"prunedResult": {"rec_texts": [""], "rec_scores": [0.9], "rec_polys": [[]]}}]}},
            bool_score,
            short_polygon,
            nonfinite_polygon,
            {"errorCode": 500, "result": response_payload()["result"]},
            {"errorCode": True, "result": response_payload()["result"]},
        ]
        for payload in bad_payloads:
            with self.subTest(payload=payload), LocalOCRServer() as server:
                OCRHandler.payload = payload
                with self.assertRaises(PaddleOCRError):
                    PaddleOCRService(server.url).recognize(PNG)

    def test_redirect_and_error_body_are_sanitized(self):
        with LocalOCRServer() as server:
            OCRHandler.redirect_to = "/other"
            with self.assertRaisesRegex(PaddleOCRError, "重定向"):
                PaddleOCRService(server.url).recognize(PNG)
            OCRHandler.redirect_to = None
            OCRHandler.status = 500
            with self.assertRaises(PaddleOCRError) as raised:
                PaddleOCRService(server.url).recognize(PNG)
        self.assertNotIn("test-key", str(raised.exception))

    def test_timeout_is_sanitized(self):
        with LocalOCRServer() as server:
            OCRHandler.delay = 0.2
            with self.assertRaisesRegex(PaddleOCRError, "超时"):
                PaddleOCRService(server.url, timeout=0.01).recognize(PNG)
            time.sleep(0.25)


def scanned_pdf(path: Path, pages: int = 1) -> None:
    document = fitz.open()
    for _ in range(pages):
        page = document.new_page(width=300, height=200)
        page.insert_image(fitz.Rect(0, 0, 300, 200), stream=PNG)
    document.save(path)
    document.close()


def digital_pdf_with_logo(path: Path) -> None:
    document = fitz.open()
    page = document.new_page(width=500, height=300)
    page.insert_textbox(
        fitz.Rect(30, 30, 470, 180),
        "This is substantial native text from a digital tender page. "
        "The small embedded logo is supplemental image content.",
        fontsize=14,
    )
    page.insert_image(fitz.Rect(430, 240, 470, 280), stream=PNG)
    document.save(path)
    document.close()


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.project = self.root / "project"
        bidkit.init_project(self.project, "OCR-TEST")

    def tearDown(self):
        self.tmp.cleanup()

    def test_native_path_never_calls_configured_service(self):
        source = self.root / "plain.md"
        source.write_text("native text\n", encoding="utf-8")
        bidkit.register_source(self.project, source, "main")
        with patch.dict(
            os.environ,
            {
                "BID_OCR_API_URL": "https://invalid.example.test/ocr",
                "BID_OCR_MIN_CONFIDENCE": "not-a-number",
            },
        ):
            result = extract_sources.extract(self.project, "OCR-TEST")
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["inputs"][0]["sha256"], bidkit.digest(self.project / "inputs/SRC-001-plain.md"))

    def test_empty_filtered_sources_do_not_submit_ocr(self):
        with LocalOCRServer() as server:
            result = extract_sources.extract(
                self.project,
                "OCR-TEST",
                source_ids=[],
                ocr="paddle-service",
                ocr_api_url=server.url,
            )
            self.assertEqual(OCRHandler.calls, [])
        self.assertEqual(result["status"], "blocked")
        self.assertIn("没有来源", result["blockers"][0])

    def test_rendered_scan_uses_local_protocol_and_preserves_identity(self):
        original = self.root / "scan.pdf"
        scanned_pdf(original)
        registered = bidkit.register_source(self.project, original, "main")
        with LocalOCRServer() as server:
            result = extract_sources.extract(
                self.project,
                "OCR-TEST",
                ocr="paddle-service",
                ocr_api_url=server.url,
                ocr_api_key="local-key",
                ocr_auth_scheme="bearer",
            )
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["data"]["coverage"], "complete")
        self.assertEqual(result["inputs"][0]["sha256"], registered["sha256"])
        self.assertEqual(result["data"]["page_audit"][0]["method"], "ocr")
        self.assertEqual(result["data"]["blocks"][0]["method"], "ocr")
        self.assertEqual(OCRHandler.calls[0]["authorization"], "Bearer local-key")
        self.assertEqual(base64.b64decode(OCRHandler.calls[0]["body"]["file"])[0:8], b"\x89PNG\r\n\x1a\n")
        schema = json.loads((ROOT / "skills/bid-source-intake/assets/output.schema.json").read_text())
        self.assertEqual(validate(result, schema), [])

    def test_low_confidence_is_retained_and_flagged(self):
        source = self.root / "scan.png"
        source.write_bytes(PNG)
        bidkit.register_source(self.project, source, "supplier")
        with LocalOCRServer() as server:
            OCRHandler.payload = response_payload(score=0.42)
            result = extract_sources.extract(self.project, "OCR-TEST", ocr="paddle-service", ocr_api_url=server.url)
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["data"]["documents"][0]["status"], "needs_review")
        self.assertEqual(result["data"]["page_audit"][0]["status"], "needs_review")
        self.assertIn("扫描页文字", result["data"]["blocks"][0]["text"])

    def test_ocr_failure_saves_partial_evidence_and_blocks(self):
        original = self.root / "scan.pdf"
        scanned_pdf(original, pages=2)
        bidkit.register_source(self.project, original, "main")
        with LocalOCRServer() as server:
            OCRHandler.payload = response_payload()

            original_do_post = OCRHandler.do_POST

            def second_call_then_fail(handler):  # type: ignore[no-untyped-def]
                if len(OCRHandler.calls) == 1:
                    OCRHandler.payload = {}
                original_do_post(handler)

            OCRHandler.do_POST = second_call_then_fail  # type: ignore[method-assign]
            try:
                result = extract_sources.extract(self.project, "OCR-TEST", ocr="paddle-service", ocr_api_url=server.url)
            finally:
                OCRHandler.do_POST = original_do_post  # type: ignore[method-assign]
        self.assertEqual(result["status"], "blocked")
        self.assertTrue(result["blockers"])
        self.assertEqual(result["data"]["documents"][0]["status"], "failed")
        self.assertEqual(len(result["data"]["blocks"]), 1)
        self.assertEqual(result["data"]["page_audit"][1]["status"], "failed")

    def test_digital_pdf_supplemental_ocr_failure_is_review_only(self):
        original = self.root / "digital-with-logo.pdf"
        digital_pdf_with_logo(original)
        bidkit.register_source(self.project, original, "main")
        with LocalOCRServer() as server:
            OCRHandler.payload = {}
            result = extract_sources.extract(
                self.project,
                "OCR-TEST",
                ocr="paddle-service",
                ocr_api_url=server.url,
            )
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["blockers"], [])
        self.assertEqual(result["data"]["coverage"], "partial")
        self.assertEqual(result["data"]["documents"][0]["status"], "needs_review")
        self.assertEqual(result["data"]["page_audit"][0]["status"], "needs_review")
        self.assertIn("补充OCR失败", result["data"]["page_audit"][0]["note"])
        self.assertTrue(any("补充OCR失败" in warning for warning in result["warnings"]))
        self.assertTrue(any("substantial native text" in block["text"] for block in result["data"]["blocks"]))

    def test_revision_rejects_outside_or_cross_project_previous(self):
        outside = self.root / "outside.json"
        outside.write_text(json.dumps({"project_id": "OCR-TEST", "artifact_id": "ART-01-NATIVE", "revision": 1}))
        with self.assertRaisesRegex(ValueError, "当前项目"):
            extract_sources.extract(self.project, "OCR-TEST", previous=outside)

        cross_project = self.project / "reviews/cross-project.json"
        cross_project.write_text(
            json.dumps({"project_id": "OTHER", "artifact_id": "ART-01-NATIVE", "revision": 1})
        )
        with self.assertRaisesRegex(ValueError, "其他项目"):
            extract_sources.extract(self.project, "OCR-TEST", previous=cross_project)

        malformed = self.project / "reviews/malformed.json"
        malformed.write_text("not-json")
        with self.assertRaisesRegex(ValueError, "有效JSON"):
            extract_sources.extract(self.project, "OCR-TEST", previous=malformed)

    def test_revision_is_monotonic_and_duplicate_history_blocks_before_ocr(self):
        with self.assertRaisesRegex(ValueError, "大于等于1"):
            extract_sources.extract(self.project, "OCR-TEST", revision=True)

        first = self.project / "artifacts/01-r1.json"
        first.write_text(
            json.dumps({"project_id": "OCR-TEST", "artifact_id": "ART-01-NATIVE", "revision": 1})
        )
        with self.assertRaisesRegex(ValueError, "大于当前最高"):
            extract_sources.extract(
                self.project,
                "OCR-TEST",
                ocr="paddle-service",
                ocr_api_url="https://invalid.example.test/ocr",
                revision=1,
            )
        result = extract_sources.extract(self.project, "OCR-TEST", revision=2)
        self.assertEqual(result["revision"], 2)

        duplicate = self.project / "artifacts/01-duplicate.json"
        duplicate.write_text(
            json.dumps({"project_id": "OCR-TEST", "artifact_id": "ART-01-NATIVE", "revision": 1})
        )
        with self.assertRaisesRegex(ValueError, "重复revision"):
            extract_sources.extract(self.project, "OCR-TEST")

    def test_source_filter_and_revision_are_explicit(self):
        first = self.root / "first.md"
        second = self.root / "second.md"
        first.write_text("first\n", encoding="utf-8")
        second.write_text("second\n", encoding="utf-8")
        bidkit.register_source(self.project, first, "main")
        bidkit.register_source(self.project, second, "supplier")
        previous = self.project / "artifacts/01-old.json"
        old = extract_sources.extract(self.project, "OCR-TEST", source_ids=["SRC-001"])
        previous.write_text(json.dumps(old), encoding="utf-8")
        result = extract_sources.extract(self.project, "OCR-TEST", source_ids=["SRC-002"], previous=previous)
        self.assertEqual(result["revision"], 2)
        self.assertEqual([doc["source_id"] for doc in result["data"]["documents"]], ["SRC-002"])
        self.assertEqual([item["artifact_id"] for item in result["inputs"]], ["SRC-002"])


if __name__ == "__main__":
    unittest.main()
