from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .axis import AxisMode
from .cursor_widget import PyQtLabGraphCursorWidget
from .layouts import LayoutFileError
from .legend import PyQtLabGraphLegend
from .models import CursorLineStyle, CursorPairState, CursorState, CursorStyle, CursorType
from .runtime_state import PlotSnapshot
from .style_registry import PyQtLabGraphStyleRegistry
from .styles import (
    BUILTIN_PLOT_STYLES,
    CurveStyle,
    PyQtLabGraphPlotStyle,
)
from .themes import (
    BUILTIN_THEMES,
    PyQtLabGraphTheme,
)
from .toolbar import PyQtLabGraphToolbar
from .widget import PyQtLabGraphWidget

try:
    __version__ = version("pyqtlabgraph")
except PackageNotFoundError:
    __version__ = "0.0.0+unknown"

__all__ = [
    "AxisMode",
    "BUILTIN_PLOT_STYLES",
    "BUILTIN_THEMES",
    "CursorState",
    "CursorLineStyle",
    "CursorPairState",
    "CursorStyle",
    "CursorType",
    "CurveStyle",
    "LayoutFileError",
    "PlotSnapshot",
    "PyQtLabGraphPlotStyle",
    "PyQtLabGraphStyleRegistry",
    "PyQtLabGraphTheme",
    "PyQtLabGraphCursorWidget",
    "PyQtLabGraphLegend",
    "PyQtLabGraphToolbar",
    "PyQtLabGraphWidget",
    "__version__",
]
