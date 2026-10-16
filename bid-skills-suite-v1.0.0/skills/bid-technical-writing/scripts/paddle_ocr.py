#!/usr/bin/env python3
"""Small, bounded client for a deployed PaddleOCR ``POST /ocr`` service.

The package deliberately does not import PaddleOCR or install a model.  A
caller opts into this client explicitly and submits one rendered PNG at a
time using the protocol documented by PaddleOCR's serving pipeline.
"""
from __future__ import annotations

import base64
import http.client
import ipaddress
import json
import math
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


DEFAULT_TIMEOUT = 30.0
MAX_RESPONSE_BYTES = 16 * 1024 * 1024


class PaddleOCRError(RuntimeError):
    """A safe-to-display OCR transport or response-contract error."""


def is_loopback_host(host: str | None) -> bool:
    """Return whether *host* is an explicitly local loopback name/address."""

    if not host:
        return False
    normalized = host.rstrip(".").lower()
    if normalized in {"localhost", "localhost.localdomain"}:
        return True
    try:
        return ipaddress.ip_address(normalized).is_loopback
    except ValueError:
        return False


def validate_service_url(url: str, *, allow_remote: bool = False) -> str:
    """Validate a configured endpoint without exposing credentials or query data."""

    if not isinstance(url, str) or not url.strip():
        raise PaddleOCRError("未配置 OCR 服务地址（BID_OCR_API_URL）")
    value = url.strip()
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise PaddleOCRError("OCR 服务地址必须是 http(s) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise PaddleOCRError("OCR 服务地址不得包含凭据、查询参数或片段")
    if not is_loopback_host(parsed.hostname):
        if not allow_remote:
            raise PaddleOCRError("远程 OCR 需要显式 --allow-remote-ocr")
        if parsed.scheme != "https":
            raise PaddleOCRError("远程 OCR 服务必须使用 HTTPS")
    return value


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        fp.close()
        raise PaddleOCRError("OCR 服务禁止重定向")


@dataclass(frozen=True)
class OCRPageResult:
    text: str
    confidence: float
    line_count: int
    polygons: list


class PaddleOCRService:
    """Submit one image per request and validate the PaddleOCR response shape."""

    def __init__(
        self,
        url: str | None = None,
        api_key: str | None = None,
        auth_scheme: str | None = None,
        *,
        allow_remote: bool = False,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        configured_url = url or os.environ.get("BID_OCR_API_URL")
        self.url = validate_service_url(configured_url or "", allow_remote=allow_remote)
        self.api_key = api_key if api_key is not None else os.environ.get("BID_OCR_API_KEY")
        if self.api_key is not None and (
            not isinstance(self.api_key, str)
            or not self.api_key.isascii()
            or any(ord(char) < 32 or ord(char) == 127 for char in self.api_key)
        ):
            raise PaddleOCRError("OCR 密钥格式无效；请通过宿主密钥管理重新配置")
        scheme = (
            auth_scheme
            or os.environ.get("BID_OCR_API_AUTH_SCHEME")
            or "bearer"
        )
        self.auth_scheme = scheme.strip().lower()
        if self.auth_scheme not in {"token", "bearer"}:
            raise PaddleOCRError("BID_OCR_API_AUTH_SCHEME 只能是 token 或 bearer")
        if timeout <= 0 or not math.isfinite(timeout):
            raise PaddleOCRError("OCR 请求超时必须是正数")
        self.timeout = float(timeout)
        self._opener = build_opener(_NoRedirectHandler())

    def recognize(self, image_bytes: bytes) -> OCRPageResult:
        """Recognize one PNG/JPEG payload, failing closed on malformed output."""

        if not image_bytes:
            raise PaddleOCRError("OCR 输入图像为空")
        payload = json.dumps(
            {"file": base64.b64encode(image_bytes).decode("ascii"), "fileType": 1},
            separators=(",", ":"),
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"{self.auth_scheme.title()} {self.api_key}"
        request = Request(self.url, data=payload, headers=headers, method="POST")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
        except PaddleOCRError:
            raise
        except HTTPError as exc:
            exc.close()
            if exc.code in {301, 302, 303, 307, 308}:
                raise PaddleOCRError("OCR 服务禁止重定向") from None
            raise PaddleOCRError(f"OCR 服务返回 HTTP {exc.code}") from None
        except TimeoutError:
            raise PaddleOCRError("OCR 服务请求超时") from None
        except URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, TimeoutError) or "timed out" in str(reason).lower():
                raise PaddleOCRError("OCR 服务请求超时") from None
            raise PaddleOCRError("OCR 服务连接失败") from None
        except (OSError, http.client.HTTPException, ValueError):
            raise PaddleOCRError("OCR 服务连接失败") from None
        if len(raw) > MAX_RESPONSE_BYTES:
            raise PaddleOCRError("OCR 服务响应过大")
        try:
            response_json = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise PaddleOCRError("OCR 服务返回非 JSON 响应") from None
        return self._parse_response(response_json)

    @staticmethod
    def _parse_response(response_json: object) -> OCRPageResult:
        if not isinstance(response_json, dict):
            raise PaddleOCRError("OCR 服务响应结构无效")
        if 'errorCode' in response_json and (
            type(response_json['errorCode']) is not int or response_json['errorCode'] != 0
        ):
            raise PaddleOCRError("OCR 服务报告处理失败")
        result = response_json.get("result")
        if not isinstance(result, dict):
            raise PaddleOCRError("OCR 服务响应缺少 result")
        ocr_results = result.get("ocrResults")
        if not isinstance(ocr_results, list) or len(ocr_results) != 1:
            raise PaddleOCRError("OCR 服务结果数量与提交图像不一致")
        item = ocr_results[0]
        if not isinstance(item, dict) or not isinstance(item.get("prunedResult"), dict):
            raise PaddleOCRError("OCR 服务结果缺少 prunedResult")
        pruned = item["prunedResult"]
        texts = pruned.get("rec_texts")
        scores = pruned.get("rec_scores")
        polygons = pruned.get("rec_polys")
        if not isinstance(texts, list) or not isinstance(scores, list) or not isinstance(polygons, list):
            raise PaddleOCRError("OCR 服务结果缺少 rec_texts、rec_scores 或 rec_polys")
        if not texts or len(texts) != len(scores) or len(texts) != len(polygons):
            raise PaddleOCRError("OCR 服务结果字段数量不一致或为空")
        clean_texts: list[str] = []
        clean_scores: list[float] = []
        for text, score in zip(texts, scores):
            if not isinstance(text, str) or type(score) not in (int, float):
                raise PaddleOCRError("OCR 服务结果字段类型无效")
            value = float(score)
            if not math.isfinite(value) or value < 0 or value > 1:
                raise PaddleOCRError("OCR 服务置信度无效")
            clean_texts.append(text)
            clean_scores.append(value)
        for polygon in polygons:
            if not isinstance(polygon, list) or len(polygon) < 3:
                raise PaddleOCRError("OCR 服务文本框坐标无效")
            for point in polygon:
                if (not isinstance(point, list) or len(point) != 2
                        or any(type(n) not in (int, float) or not math.isfinite(n) for n in point)):
                    raise PaddleOCRError("OCR 服务文本框坐标无效")
        nonempty = [text for text in clean_texts if text.strip()]
        if not nonempty:
            raise PaddleOCRError("OCR 服务返回空文本")
        return OCRPageResult(
            text="\n".join(clean_texts),
            confidence=min(clean_scores),
            line_count=len(clean_texts),
            polygons=polygons,
        )


def make_client(
    *,
    url: str | None = None,
    api_key: str | None = None,
    auth_scheme: str | None = None,
    allow_remote: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
) -> PaddleOCRService:
    """Factory kept small so extraction and tests share URL/auth policy."""

    return PaddleOCRService(
        url=url,
        api_key=api_key,
        auth_scheme=auth_scheme,
        allow_remote=allow_remote,
        timeout=timeout,
    )
