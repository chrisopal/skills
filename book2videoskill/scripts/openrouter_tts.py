#!/usr/bin/env python3
"""Generate per-scene TTS audio using OpenRouter, with local fallback."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

from book2video_common import read_json, relpath, write_json


OPENROUTER_SPEECH_URL = "https://openrouter.ai/api/v1/audio/speech"
DEFAULT_MODEL = "openai/gpt-4o-mini-tts"
DEFAULT_VOICE = "nova"
KEY_ERROR = "OPENROUTER_API_KEY not found in env, Hermes env-path, or supported system config files."


def read_key_from_file(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        env_match = re.match(r"OPENROUTER_API_KEY\s*=\s*['\"]?([^'\"\s#]+)", stripped, re.I)
        if env_match:
            return env_match.group(1)
        yaml_match = re.match(r"(?:api_key|apikey|OPENROUTER_API_KEY|key)\s*:\s*['\"]?([^'\"\s#]+)", stripped, re.I)
        if yaml_match and yaml_match.group(1).startswith("sk-or-"):
            return yaml_match.group(1)
    return None


def hermes_env_path() -> Path | None:
    hermes = shutil_which("hermes")
    if not hermes:
        return None
    try:
        result = subprocess.run(
            [hermes, "config", "env-path"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except Exception:
        return None
    output = result.stdout.strip().splitlines()
    if not output:
        return None
    return Path(output[-1]).expanduser()


def shutil_which(binary: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(directory) / binary
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return None


def hermes_openrouter_status() -> str | None:
    hermes = shutil_which("hermes")
    if not hermes:
        return None
    try:
        result = subprocess.run(
            [hermes, "auth", "status", "openrouter"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
    except Exception:
        return None
    status = (result.stdout or result.stderr).strip()
    return status or None


def resolve_openrouter_key() -> str | None:
    if os.getenv("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    paths = [
        Path.home() / ".hermes" / ".env",
        Path.home() / ".hermes" / "config.yaml",
        Path.home() / ".config" / "hermes" / ".env",
        Path.home() / ".config" / "openrouter" / ".env",
    ]
    env_path = hermes_env_path()
    if env_path and env_path not in paths:
        paths.insert(0, env_path)
    for path in paths:
        key = read_key_from_file(path)
        if key:
            return key
    return None


def synthesize_openrouter(text: str, output_path: Path, *, model: str, voice: str, speed: float) -> None:
    api_key = resolve_openrouter_key()
    if not api_key:
        status = hermes_openrouter_status()
        detail = f" Hermes auth status: {status}" if status else ""
        raise RuntimeError(KEY_ERROR + detail)
    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": output_path.suffix.lstrip(".") or "mp3",
        "speed": speed,
    }
    req = urllib.request.Request(
        OPENROUTER_SPEECH_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/chrisopal/skills",
            "X-Title": "book2videoskill",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            output_path.write_bytes(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"OpenRouter TTS failed: HTTP {exc.code} {detail}") from exc


def synthesize_macos_say(text: str, output_path: Path, *, voice: str) -> None:
    aiff_path = output_path.with_suffix(".aiff")
    say_voice = voice if voice and voice != DEFAULT_VOICE else "Tingting"
    subprocess.run(["say", "-v", say_voice, "-o", str(aiff_path), text], check=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(aiff_path),
            "-codec:a",
            "libmp3lame",
            "-q:a",
            "4",
            str(output_path),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    aiff_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--provider", choices=["openrouter", "say", "none"], default="openrouter")
    parser.add_argument("--fallback-provider", choices=["say", "none"], default="say")
    parser.add_argument("--model", default=os.getenv("OPENROUTER_TTS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--voice", default=os.getenv("OPENROUTER_TTS_VOICE", DEFAULT_VOICE))
    parser.add_argument("--speed", type=float, default=float(os.getenv("OPENROUTER_TTS_SPEED", "1.0")))
    args = parser.parse_args()

    project_dir = Path(args.project_dir)
    storyboard = read_json(project_dir / "storyboard.json")
    tts_dir = project_dir / "tts_audio"
    tts_dir.mkdir(parents=True, exist_ok=True)

    generated = []
    actual_provider = args.provider
    provider_error = None
    for scene in storyboard["scenes"]:
        out_path = tts_dir / f"{scene['sceneId']}.mp3"
        text = scene["narration"]
        if args.provider == "none":
            provider_error = "TTS provider disabled"
            continue
        try:
            if args.provider == "openrouter":
                synthesize_openrouter(text, out_path, model=args.model, voice=args.voice, speed=args.speed)
            elif args.provider == "say":
                synthesize_macos_say(text, out_path, voice=args.voice)
        except Exception as exc:
            provider_error = str(exc)
            if args.fallback_provider == "say":
                synthesize_macos_say(text, out_path, voice="Tingting")
                actual_provider = "say"
            else:
                print(f"ERROR: {provider_error}", file=sys.stderr)
                return 1
        generated.append(
            {
                "sceneId": scene["sceneId"],
                "path": relpath(out_path, project_dir),
                "provider": actual_provider,
                "model": args.model if actual_provider == "openrouter" else None,
                "voice": args.voice if actual_provider == "openrouter" else "Tingting",
                "status": "generated",
                "durationSecTarget": scene["durationSec"],
            }
        )

    write_json(
        project_dir / "tts_manifest.json",
        {
            "provider": actual_provider,
            "requestedProvider": args.provider,
            "fallbackProvider": args.fallback_provider,
            "model": args.model,
            "voice": args.voice,
            "providerError": provider_error,
            "assets": generated,
        },
    )
    print(f"tts_project: {project_dir}")
    print(f"tts_provider: {actual_provider}")
    print(f"tts_assets: {len(generated)}")
    if provider_error:
        print(f"tts_provider_note: {provider_error}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
