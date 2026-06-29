#!/usr/bin/env python3
"""Save WeChat Official Account image-post or article drafts.

Default target is `article_type=newspic` for image-post drafts.
This helper is intentionally conservative:
- save draft only
- never publish
- use stdlib only
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
DRAFT_GET_URL = "https://api.weixin.qq.com/cgi-bin/draft/get"
DRAFT_UPDATE_URL = "https://api.weixin.qq.com/cgi-bin/draft/update"
ADD_MATERIAL_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"


def load_env_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def merge_env(env_file: Path | None) -> dict[str, str]:
    merged = dict(os.environ)
    if env_file:
        merged.update(load_env_file(env_file))
    return merged


def http_json(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = None
    headers = {"User-Agent": "Codex-WeChat-Draft-Helper/1.0"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method=method)
    with urlopen(req, timeout=60) as resp:
        text = resp.read().decode("utf-8")
    return json.loads(text)


def encode_multipart(fields: dict[str, str], files: list[tuple[str, Path, str]]) -> tuple[bytes, str]:
    boundary = f"----CodexBoundary{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode("utf-8"),
                b"\r\n",
            ]
        )
    for field_name, path, content_type in files:
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{path.name}"\r\n'
                ).encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                path.read_bytes(),
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), boundary


def http_multipart(url: str, fields: dict[str, str], files: list[tuple[str, Path, str]]) -> dict[str, Any]:
    body, boundary = encode_multipart(fields, files)
    req = Request(
        url,
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Content-Length": str(len(body)),
            "User-Agent": "Codex-WeChat-Draft-Helper/1.0",
        },
        method="POST",
    )
    with urlopen(req, timeout=120) as resp:
        text = resp.read().decode("utf-8")
    return json.loads(text)


def get_access_token(env: dict[str, str]) -> str:
    cached = (env.get("WECHAT_ACCESS_TOKEN") or env.get("WECHAT_OA_ACCESS_TOKEN") or "").strip()
    if cached:
        return cached
    appid = (env.get("WECHAT_APP_ID") or env.get("WECHAT_OA_APPID") or "").strip()
    secret = (env.get("WECHAT_APP_SECRET") or env.get("WECHAT_OA_APPSECRET") or "").strip()
    if not appid or not secret:
        raise SystemExit(
            "Missing WeChat credentials. Set WECHAT_APP_ID + WECHAT_APP_SECRET, "
            "or WECHAT_ACCESS_TOKEN, or the legacy WECHAT_OA_* names."
        )
    url = f"{TOKEN_URL}?{urlencode({'grant_type': 'client_credential', 'appid': appid, 'secret': secret})}"
    data = http_json(url)
    token = data.get("access_token")
    if not token:
        raise SystemExit(f"Failed to get access token: {json.dumps(data, ensure_ascii=False)}")
    return token


def upload_permanent_image(access_token: str, image_path: Path) -> str:
    if not image_path.exists():
        raise FileNotFoundError(f"image not found: {image_path}")
    mime = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    url = f"{ADD_MATERIAL_URL}?{urlencode({'access_token': access_token, 'type': 'image'})}"
    data = http_multipart(url, {}, [("media", image_path, mime)])
    media_id = data.get("media_id")
    if not media_id:
        raise SystemExit(f"Failed to upload image material: {json.dumps(data, ensure_ascii=False)}")
    return media_id


def get_draft(access_token: str, media_id: str) -> dict[str, Any]:
    url = f"{DRAFT_GET_URL}?{urlencode({'access_token': access_token})}"
    return http_json(url, method="POST", payload={"media_id": media_id})


def normalize_plain_text_content(value: Any) -> Any:
    """Prevent JSON-built drafts from showing literal ``\n`` in WeChat."""
    if not isinstance(value, str):
        return value
    return value.replace("\\r\\n", "\n").replace("\\n", "\n")


def resolve_articles(
    bundle: dict[str, Any],
    access_token: str | None,
    *,
    dry_run: bool,
    existing_articles: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    for index, article in enumerate(bundle.get("articles", [])):
        item = dict(article)
        article_type = item.get("article_type") or bundle.get("draft_type") or "newspic"
        item["article_type"] = article_type
        if "content" in item:
            item["content"] = normalize_plain_text_content(item["content"])

        if article_type == "newspic":
            image_paths = [Path(p) for p in item.pop("image_paths", [])]
            existing_image_info = (
                (existing_articles or [{}])[index].get("image_info")
                if existing_articles and index < len(existing_articles)
                else None
            )
            if not image_paths and existing_image_info:
                item["image_info"] = existing_image_info
            elif not image_paths:
                raise SystemExit(f"newspic article missing image_paths: {item.get('title', '<untitled>')}")
            else:
                image_list = []
                for path in image_paths:
                    if dry_run:
                        media_id = f"DRYRUN_MEDIA_ID_{path.stem}"
                    else:
                        media_id = upload_permanent_image(access_token or "", path)
                    image_list.append({"image_media_id": media_id})
                item["image_info"] = {"image_list": image_list}
            cover_crop = item.pop("cover_crop", None)
            if cover_crop:
                item["cover_info"] = {"crop_percent_list": cover_crop}

        elif article_type == "news":
            thumb_path = item.pop("thumb_image_path", None)
            if thumb_path and not item.get("thumb_media_id"):
                if dry_run:
                    item["thumb_media_id"] = f"DRYRUN_THUMB_MEDIA_ID_{Path(thumb_path).stem}"
                else:
                    item["thumb_media_id"] = upload_permanent_image(access_token or "", Path(thumb_path))

        resolved.append(item)
    return resolved


def update_draft(access_token: str, media_id: str, index: int, article: dict[str, Any]) -> dict[str, Any]:
    url = f"{DRAFT_UPDATE_URL}?{urlencode({'access_token': access_token})}"
    payload = {"media_id": media_id, "index": index, "articles": article}
    return http_json(url, method="POST", payload=payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="Save WeChat image-post/article drafts.")
    parser.add_argument("--bundle", required=True, help="Path to draft bundle JSON")
    parser.add_argument("--env-file", help="Optional env file with WeChat credentials")
    parser.add_argument("--dry-run", action="store_true", help="Resolve payload but do not call draft/add")
    parser.add_argument("--update-media-id", help="Existing draft media_id to update instead of creating a new draft")
    parser.add_argument("--update-index", type=int, default=0, help="Article index to update when --update-media-id is set")
    args = parser.parse_args()

    bundle_path = Path(args.bundle).resolve()
    env_file = Path(args.env_file).resolve() if args.env_file else None
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    env = merge_env(env_file)
    access_token = None if args.dry_run else get_access_token(env)
    existing_articles = None
    if args.update_media_id and not args.dry_run:
        existing_articles = get_draft(access_token or "", args.update_media_id).get("news_item", [])
    articles = resolve_articles(bundle, access_token, dry_run=args.dry_run, existing_articles=existing_articles)
    payload = {"articles": articles}

    if args.dry_run:
        print(json.dumps({"ok": True, "dry_run": True, "payload": payload}, ensure_ascii=False, indent=2))
        return 0

    if args.update_media_id:
        if len(articles) != 1:
            raise SystemExit("Updating currently supports exactly one article in the bundle.")
        result = update_draft(access_token or "", args.update_media_id, args.update_index, articles[0])
        print(
            json.dumps(
                {
                    "ok": "errcode" not in result or result.get("errcode") == 0,
                    "result": result,
                    "media_id": args.update_media_id,
                    "updated_index": args.update_index,
                    "draft_type": bundle.get("draft_type", "newspic"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    url = f"{DRAFT_ADD_URL}?{urlencode({'access_token': access_token})}"
    result = http_json(url, method="POST", payload=payload)
    ok = "media_id" in result and "errcode" not in result
    print(
        json.dumps(
            {
                "ok": ok,
                "result": result,
                "article_count": len(articles),
                "draft_type": bundle.get("draft_type", "newspic"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
