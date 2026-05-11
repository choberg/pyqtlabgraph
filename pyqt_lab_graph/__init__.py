from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import re

from .axis import AxisMode
from .layouts import LayoutFileError
from .styles import (
    BUILTIN_PLOT_STYLES,
    CurveStyle,
    PyQtLabGraphPlotStyle,
)
from .themes import (
    BUILTIN_THEMES,
    PyQtLabGraphTheme,
)
from .widget import PyQtLabGraphWidget


def _source_tree_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    project_metadata = pyproject_path.read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', project_metadata)
    if match is None:
        raise RuntimeError("Could not read project version from pyproject.toml")
    return match.group(1)


try:
    __version__ = version("pyqt-lab-graph")
except PackageNotFoundError:
    __version__ = _source_tree_version()

__all__ = [
    "AxisMode",
    "BUILTIN_PLOT_STYLES",
    "BUILTIN_THEMES",
    "CurveStyle",
    "LayoutFileError",
    "PyQtLabGraphPlotStyle",
    "PyQtLabGraphTheme",
    "PyQtLabGraphWidget",
    "__version__",
]
