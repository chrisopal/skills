from __future__ import annotations
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
import os


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def normalize_name(name: str | None) -> str | None:
    if not name:
        return None
    return re.sub(r"[\s（）()有限公司股份集团公司]+", "", name).lower()


def to_json(value) -> str:
    return json.dumps(value if value is not None else [], ensure_ascii=False)


def from_json(text: str | None, default=None):
    if default is None:
        default = []
    if not text:
        return default
    try:
        return json.loads(text)
    except Exception:
        return default


def ensure_parent(path: str | Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def default_db_path() -> Path:
    """Return the portable default database path for this capability package."""
    data_dir = os.environ.get("SKILL_DATA_DIR")
    root = Path(data_dir) if data_dir else Path.cwd() / ".skill_data"
    return root / "opportunity-analysis" / "opportunity.db"
