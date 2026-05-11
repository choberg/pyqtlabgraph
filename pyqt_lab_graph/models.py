from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pyqtgraph as pg

from .styles import CurveStyle


class InteractionTool(Enum):
    NONE = "none"
    RECT_ZOOM = "rect_zoom"
    X_ZOOM = "x_zoom"
    Y_ZOOM = "y_zoom"


@dataclass
class InteractionState:
    autoscale_x: bool = True
    autoscale_y: bool = True
    rolling_x: bool = False
    active_tool: InteractionTool = InteractionTool.NONE


@dataclass
class CurveState:
    key: str
    label: str
    item: pg.PlotDataItem
    style: CurveStyle = field(default_factory=CurveStyle)
    visible: bool = True
