"""Shared pytest fixtures for the pulse-setup test suite."""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES_ROOT = Path(__file__).parent / "fixtures"


@pytest.fixture
def tmp_consumer_project(tmp_path: Path) -> Path:
    """Empty tmp directory simulating a fresh consumer project root."""
    return tmp_path


@pytest.fixture
def bmad_64_consumer(tmp_path: Path) -> Path:
    """Consumer project with BMAD 6.4.0 layout (customize.toml present)."""
    src = FIXTURES_ROOT / "bmad-6.4.0"
    dst = tmp_path / "consumer"
    shutil.copytree(src, dst)
    return dst


@pytest.fixture
def bmad_63_consumer(tmp_path: Path) -> Path:
    """Consumer project with BMAD 6.3.x layout (workflow.md present, no customize.toml)."""
    src = FIXTURES_ROOT / "bmad-6.3.x"
    dst = tmp_path / "consumer"
    shutil.copytree(src, dst)
    return dst
