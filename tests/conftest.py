"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def original_source(fixtures_dir: Path) -> str:
    return (fixtures_dir / "original.py").read_text()


@pytest.fixture
def refactored_dir(fixtures_dir: Path) -> Path:
    return fixtures_dir / "refactored"
