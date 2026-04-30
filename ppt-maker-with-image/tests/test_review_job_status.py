from __future__ import annotations

import json
from pathlib import Path

from pipeline.manifest import STAGE_ARTIFACTS
from review_job_status import determine_stage


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_review_job_status_uses_artifact_completeness_to_complete(tmp_path: Path) -> None:
    job = {
        "topic": "季度复盘",
        "target_audience": "管理层",
        "purpose": "汇报",
        "style": "咨询风",
        "page_count": 2,
        "output": {"directory": str(tmp_path / "artifacts")},
        "outline_approved": False,
        "prompts_approved": False,
    }
    output_dir = tmp_path / "artifacts"
    output_dir.mkdir()
    _write_json(output_dir / STAGE_ARTIFACTS["master_style"], {"prompt_block": "白底"})
    _write_json(output_dir / STAGE_ARTIFACTS["outline"], {"slides": [{"page_no": 1}, {"page_no": 2}]})
    _write_json(output_dir / STAGE_ARTIFACTS["page_intent"], {"slides": [{"page_no": 1}, {"page_no": 2}]})
    _write_json(output_dir / STAGE_ARTIFACTS["slide_prompts"], {"slides": [{"page_no": 1}, {"page_no": 2}]})
    image_dir = output_dir / STAGE_ARTIFACTS["render"]
    image_dir.mkdir()
    (image_dir / "slide_01.png").write_bytes(b"")
    (image_dir / "slide_02.png").write_bytes(b"")
    (output_dir / "deck.pptx").write_bytes(b"")

    status = determine_stage(job, output_dir)

    assert status["completed"] is True
    assert status["stage"] == "completed"
    assert status["artifacts"]["page_intent"] is True
