from __future__ import annotations

from dataclasses import dataclass, field

import pyqtgraph as pg


@dataclass
class CurveState:
    key: str
    label: str
    item: pg.PlotDataItem
    x_values: list[float] = field(default_factory=list)
    y_values: list[float] = field(default_factory=list)
    style: dict[str, object] = field(default_factory=dict)
    using_theme_color: bool = False
    visible: bool = True


