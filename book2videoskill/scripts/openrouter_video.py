#!/usr/bin/env python3
"""Generate per-scene video clips through OpenRouter's video API."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from book2video_common import read_json, relpath, write_json
from openrouter_tts import resolve_openrouter_key


OPENROUTER_VIDEO_URL = "https://openrouter.ai/api/v1/videos"
DEFAULT_MODEL = "bytedance/seedance-2.0-fast"
DEFAULT_RESOLUTION = "720p"
DEFAULT_ASPECT_RATIO = "9:16"


def request_json(url: str, api_key: str, *, payload: dict[str, Any] | None = None, timeout: int = 60) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chrisopal/skills",
            "X-Title": "book2videoskill",
        },
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
            return json.loads(body) if body.strip() else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1200]
        raise RuntimeError(f"OpenRouter video HTTP {exc.code}: {detail}") from exc


def duration_for_model(scene_duration: float) -> int:
    # The default OpenRouter video models support integer durations from 4-15s.
    return max(4, min(15, int(math.ceil(scene_duration))))


def scene_prompt(scene: dict[str, Any]) -> str:
    base = scene.get("imageSourceStrategy", {}).get("imagePrompt") or scene.get("visualDescription") or scene["title"]
    return "\n".join(
        [
            base,
            "",
            "Generate a short 9:16 cinematic vertical video clip for this book-analysis scene.",
            "The clip should have gentle camera motion, natural depth, no hard cuts, no subtitles, no long readable text, no logos, no watermarks.",
            "Final Chinese title and subtitles will be overlaid by the renderer.",
        ]
    )


def find_video_url(value: Any) -> str | None:
    if isinstance(value, str) and value.startswith("http"):
        lowered = value.lower()
        if "polling_url" not in lowered and ("content?index=" in lowered or any(ext in lowered for ext in [".mp4", ".webm", ".mov"])):
            return value
    if isinstance(value, dict):
        for key in ["unsigned_urls", "video_url", "download_url", "asset_url", "url"]:
            found = find_video_url(value.get(key))
            if found:
                return found
        for key, item in value.items():
            if key == "polling_url":
                continue
            found = find_video_url(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = find_video_url(item)
            if found:
                return found
    return None


def download(url: str, output_path: Path, *, api_key: str, timeout: int = 180) -> None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "book2videoskill/1.0",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        output_path.write_bytes(response.read())


def generate_scene_clip(
    scene: dict[str, Any],
    output_path: Path,
    *,
    api_key: str,
    model: str,
    resolution: str,
    aspect_ratio: str,
    duration: int,
    timeout_sec: int,
    poll_interval: int,
) -> dict[str, Any]:
    payload = {
        "model": model,
        "prompt": scene_prompt(scene),
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "resolution": resolution,
        "generate_audio": False,
    }
    submitted = request_json(OPENROUTER_VIDEO_URL, api_key, payload=payload, timeout=90)
    polling_url = submitted.get("polling_url") or f"{OPENROUTER_VIDEO_URL}/{submitted.get('id')}"
    deadline = time.monotonic() + timeout_sec
    last_status = submitted
    while time.monotonic() < deadline:
        status = request_json(polling_url, api_key, timeout=60)
        last_status = status
        state = str(status.get("status", "")).lower()
        if state in {"completed", "complete", "succeeded", "success", "finished"}:
            video_url = find_video_url(status)
            if not video_url:
                raise RuntimeError(f"OpenRouter video completed without downloadable video URL: {json.dumps(status)[:1000]}")
            download(video_url, output_path, api_key=api_key)
            return {
                "sceneId": scene["sceneId"],
                "status": "generated",
                "path": str(output_path),
                "durationSec": duration,
                "jobId": submitted.get("id"),
                "generationId": status.get("generation_id") or submitted.get("generation_id"),
                "pollingUrl": polling_url,
            }
        if state in {"failed", "error", "cancelled", "canceled"}:
            raise RuntimeError(f"OpenRouter video failed: {json.dumps(status, ensure_ascii=False)[:1200]}")
        time.sleep(poll_interval)
    raise TimeoutError(f"OpenRouter video timed out after {timeout_sec}s. Last status: {json.dumps(last_status, ensure_ascii=False)[:1200]}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--model", default=os.getenv("OPENROUTER_VIDEO_MODEL", DEFAULT_MODEL))
    parser.add_argument("--resolution", default=os.getenv("OPENROUTER_VIDEO_RESOLUTION", DEFAULT_RESOLUTION))
    parser.add_argument("--aspect-ratio", default=os.getenv("OPENROUTER_VIDEO_ASPECT_RATIO", DEFAULT_ASPECT_RATIO))
    parser.add_argument("--timeout-sec", type=int, default=int(os.getenv("OPENROUTER_VIDEO_TIMEOUT_SEC", "900")))
    parser.add_argument("--poll-interval", type=int, default=int(os.getenv("OPENROUTER_VIDEO_POLL_INTERVAL", "8")))
    parser.add_argument("--max-scenes", type=int, default=0, help="Generate only the first N scenes; 0 means all scenes.")
    parser.add_argument("--reuse-existing", action="store_true")
    args = parser.parse_args()

    api_key = resolve_openrouter_key()
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found", file=sys.stderr)
        return 1

    project_dir = Path(args.project_dir)
    storyboard = read_json(project_dir / "storyboard.json")
    timing = read_json(project_dir / "render_timing.json") if (project_dir / "render_timing.json").exists() else {}
    scene_durations = timing.get("sceneDurations", {})
    clips_dir = project_dir / "video_clips" / "openrouter"
    clips_dir.mkdir(parents=True, exist_ok=True)

    scenes = storyboard["scenes"][: args.max_scenes or None]
    assets: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for scene in scenes:
        scene_id = scene["sceneId"]
        clip_path = clips_dir / f"{scene_id}.mp4"
        duration = duration_for_model(float(scene_durations.get(scene_id, scene["durationSec"])))
        if args.reuse_existing and clip_path.exists():
            assets.append(
                {
                    "sceneId": scene_id,
                    "status": "reused",
                    "path": relpath(clip_path, project_dir),
                    "durationSec": duration,
                }
            )
            continue
        try:
            asset = generate_scene_clip(
                scene,
                clip_path,
                api_key=api_key,
                model=args.model,
                resolution=args.resolution,
                aspect_ratio=args.aspect_ratio,
                duration=duration,
                timeout_sec=args.timeout_sec,
                poll_interval=args.poll_interval,
            )
            asset["path"] = relpath(clip_path, project_dir)
            assets.append(asset)
            print(f"openrouter_video_scene: {scene_id} generated")
        except Exception as exc:
            errors.append({"sceneId": scene_id, "error": str(exc)})
            print(f"ERROR: scene {scene_id}: {exc}", file=sys.stderr)
            break

    manifest = {
        "provider": "openrouter-video",
        "model": args.model,
        "resolution": args.resolution,
        "aspectRatio": args.aspect_ratio,
        "generateAudio": False,
        "status": "generated" if len(assets) == len(scenes) and not errors else "partial",
        "assets": assets,
        "errors": errors,
    }
    write_json(project_dir / "openrouter_video_manifest.json", manifest)
    print(f"openrouter_video_project: {project_dir}")
    print(f"openrouter_video_assets: {len(assets)}")
    print(f"openrouter_video_status: {manifest['status']}")
    return 0 if manifest["status"] == "generated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
