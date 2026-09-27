from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")

EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
sys.path.insert(0, str(EXAMPLES_DIR))

import pytest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture(autouse=True)
def _restore_application_style() -> object:
    """Keep palette and style changes made by one test out of the next."""
    app = QApplication.instance() or QApplication([])
    style_name = app.style().name()
    palette = app.palette()
    yield
    if app.style().name() != style_name:
        app.setStyle(style_name)
    app.setPalette(palette)
