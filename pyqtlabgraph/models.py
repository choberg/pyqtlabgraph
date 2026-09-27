from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import pyqtgraph as pg
from PySide6.QtGui import QColor

from .styles import CurveStyle


class InteractionTool(Enum):
    NONE = "none"
    RECT_ZOOM = "rect_zoom"
    X_ZOOM = "x_zoom"
    Y_ZOOM = "y_zoom"


@dataclass(frozen=True)
class InteractionState:
    autoscale_x: bool = True
    autoscale_y: bool = True
    rolling_x: bool = False
    active_tool: InteractionTool = InteractionTool.NONE

    def __post_init__(self) -> None:
        if not isinstance(self.active_tool, InteractionTool):
            raise TypeError("Interaction active_tool must be an InteractionTool.")
        if self.autoscale_x and self.rolling_x:
            raise ValueError("Autoscale X and rolling X cannot both be enabled.")
        if self.active_tool is not InteractionTool.NONE and (
            self.autoscale_x or self.autoscale_y or self.rolling_x
        ):
            raise ValueError(
                "An active zoom tool requires both autoscales and rolling X "
                "to be disabled."
            )


@dataclass
class CurveState:
    key: str
    label: str
    item: pg.PlotDataItem
    style: CurveStyle = field(default_factory=CurveStyle)
    visible: bool = True


class CursorType(Enum):
    X = "x"
    Y = "y"


class CursorLineStyle(Enum):
    SOLID = "solid"
    DASH = "dash"
    DOT = "dot"
    DASH_DOT = "dash-dot"


@dataclass(frozen=True)
class CursorStyle:
    line_color: str = "#0072B2"
    line_width: float = 1.0
    line_style: CursorLineStyle = CursorLineStyle.SOLID

    def __post_init__(self) -> None:
        if not QColor(self.line_color).isValid():
            raise ValueError(f"Invalid line_color color: {self.line_color}")
        if self.line_width <= 0.0:
            raise ValueError("Cursor line_width must be greater than zero.")
        if not isinstance(self.line_style, CursorLineStyle):
            raise TypeError("Cursor line_style must be a CursorLineStyle.")


@dataclass(frozen=True)
class CursorState:
    key: str
    name: str
    cursor_type: CursorType
    value: float
    visible: bool = True
    style: CursorStyle = field(default_factory=CursorStyle)
    snap_target_curve_key: str | None = None
    follow_target_visibility: bool = False
    label_visible: bool = False

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("Cursor key must not be empty.")
        if not self.name:
            raise ValueError("Cursor name must not be empty.")
        if not isinstance(self.cursor_type, CursorType):
            raise TypeError("Cursor cursor_type must be a CursorType.")
        if not math.isfinite(self.value):
            raise ValueError("Cursor value must be finite.")
        if self.snap_target_curve_key is None:
            if self.follow_target_visibility:
                raise ValueError("Target visibility coupling requires a snap target.")
            return
        if self.cursor_type is not CursorType.X:
            raise ValueError("Only X cursors support snapping.")
        if not self.snap_target_curve_key:
            raise ValueError("Snapping requires a target curve key.")


@dataclass(frozen=True)
class CursorPairState:
    key: str
    first_cursor_key: str
    second_cursor_key: str
    measurement_visible: bool = True
    annotation_position: float = 0.08

    def __post_init__(self) -> None:
        if not self.key:
            raise ValueError("Cursor pair key must not be empty.")
        if self.first_cursor_key == self.second_cursor_key:
            raise ValueError("Cursor pair requires two distinct cursors.")
        if not 0.0 <= self.annotation_position <= 1.0:
            raise ValueError("Cursor pair annotation_position must be between 0 and 1.")
