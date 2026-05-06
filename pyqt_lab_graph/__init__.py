from __future__ import annotations

import pyqtgraph as pg

from .axis import AxisMode, SmartAxisItem
from .legend import PyQtLabGraphLegend
from .toolbar import PyQtLabGraphToolbar
from .widget import PyQtLabGraphWidget


pg.setConfigOptions(antialias=True)

__version__ = "0.1.0"

__all__ = [
    "AxisMode",
    "PyQtLabGraphLegend",
    "PyQtLabGraphToolbar",
    "PyQtLabGraphWidget",
    "SmartAxisItem",
    "__version__",
]
