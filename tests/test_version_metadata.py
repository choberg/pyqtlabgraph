from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

import pyqtlabgraph  # noqa: E402


def test_version_metadata() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', pyproject)
    assert match is not None
    expected_version = match.group(1)
    assert pyqtlabgraph.__version__ == expected_version
