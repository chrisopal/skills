"""Shared pytest fixtures for the ppt-maker-direct-pptx skill tests."""

from pathlib import Path

import pytest


@pytest.fixture
def fixtures_dir() -> Path:
    """Absolute path to the ``tests/fixtures/`` directory."""
    return Path(__file__).parent / "fixtures"
