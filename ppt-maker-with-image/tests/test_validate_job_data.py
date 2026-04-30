from __future__ import annotations

from validate_job import validate_job_data


def test_validate_job_data_allows_missing_style_when_master_style_exists() -> None:
    job = {
        "topic": "测试主题",
        "target_audience": "PM",
        "purpose": "汇报",
        "page_count": 3,
        "master_style": {"prompt_block": "统一风格"},
    }
    assert validate_job_data(job) == []


def test_validate_job_data_still_requires_style_without_template_or_master_style() -> None:
    job = {
        "topic": "测试主题",
        "target_audience": "PM",
        "purpose": "汇报",
        "page_count": 3,
    }
    missing = validate_job_data(job)
    assert "style" in missing
