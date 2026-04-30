from __future__ import annotations

import json
import time
from typing import Any, Mapping, Sequence

from .errors import ProviderError, UnsupportedFeatureError


MessageList = Sequence[Mapping[str, Any]]
JSON_MODE_SYSTEM_MESSAGE = {
    "role": "system",
    "content": "Return only valid JSON. Do not include markdown fences or explanatory prose.",
}
JSON_PARSE_MAX_ATTEMPTS = 3


def complete_text(
    *,
    model: str,
    messages: MessageList,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.3,
    response_format: Mapping[str, Any] | None = None,
    extra_headers: Mapping[str, str] | None = None,
    **kwargs: Any,
) -> str:
    try:
        from litellm import completion
    except ImportError as exc:
        raise UnsupportedFeatureError("litellm is required for text completion") from exc

    payload: dict[str, Any] = {
        "model": model,
        "messages": list(messages),
        "temperature": temperature,
    }
    if api_key:
        payload["api_key"] = api_key
    if base_url:
        payload["base_url"] = base_url
    if response_format:
        payload["response_format"] = dict(response_format)
    if extra_headers:
        payload["extra_headers"] = dict(extra_headers)
    payload.update(kwargs)

    try:
        response = completion(**payload)
    except Exception as exc:
        raise ProviderError(f"Text completion failed for model `{model}`") from exc

    try:
        content = response.choices[0].message.content
    except Exception as exc:
        raise ProviderError("Text completion response is missing message content") from exc

    return _coerce_content_to_text(content)


def complete_json(
    *,
    model: str,
    messages: MessageList,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.3,
    extra_headers: Mapping[str, str] | None = None,
    **kwargs: Any,
) -> Any:
    request_messages = _with_json_instruction(messages)
    last_exc: ProviderError | None = None

    for attempt in range(JSON_PARSE_MAX_ATTEMPTS):
        content = complete_text(
            model=model,
            messages=request_messages,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            response_format={"type": "json_object"},
            extra_headers=extra_headers,
            **kwargs,
        )
        try:
            return _parse_json_content(content)
        except ProviderError as exc:
            last_exc = exc
            if attempt < JSON_PARSE_MAX_ATTEMPTS - 1:
                time.sleep(attempt + 1)
                continue
            break

    raise ProviderError("Text model did not return valid JSON content") from last_exc


def _with_json_instruction(messages: MessageList) -> list[Mapping[str, Any]]:
    return [JSON_MODE_SYSTEM_MESSAGE, *list(messages)]


def _coerce_content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
                continue
            if isinstance(item, Mapping):
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        joined = "".join(parts).strip()
        if joined:
            return joined
    raise ProviderError("Unsupported message content type returned from text model")


def _parse_json_content(content: str) -> Any:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        candidate = _extract_json_candidate(content)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ProviderError("Text model did not return valid JSON content") from exc


def _extract_json_candidate(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3 and lines[-1].strip() == "```":
            inner = "\n".join(lines[1:-1]).strip()
            if inner:
                stripped = inner

    start_positions = [pos for pos in (stripped.find("{"), stripped.find("[")) if pos != -1]
    end_positions = [pos for pos in (stripped.rfind("}"), stripped.rfind("]")) if pos != -1]
    if not start_positions or not end_positions:
        return stripped
    start = min(start_positions)
    end = max(end_positions)
    if end <= start:
        return stripped
    return stripped[start : end + 1]
