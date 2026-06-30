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
    try:
        pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        if not pyproject_path.exists():
            return "0.0.0-unknown"
        project_metadata = pyproject_path.read_text(encoding="utf-8")
        match = re.search(r'(?m)^version\s*=\s*"([^"]+)"\s*$', project_metadata)
        if match is None:
            return "0.0.0-unknown"
        return match.group(1)
    except Exception:
        return "0.0.0-unknown"


_local_version = _source_tree_version()
if _local_version != "0.0.0-unknown":
    __version__ = _local_version
else:
    try:
        __version__ = version("pyqtlabgraph")
    except PackageNotFoundError:
        __version__ = "0.0.0-unknown"

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
