from __future__ import annotations

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QStyle, QStyleOptionFrame, QWidget


def paint_host_frame(widget: QWidget) -> None:
    """Draw a native panel frame without caching palette roles in a stylesheet."""
    option = QStyleOptionFrame()
    option.initFrom(widget)
    option.frameShape = QFrame.Shape.StyledPanel
    option.lineWidth = widget.style().pixelMetric(
        QStyle.PixelMetric.PM_DefaultFrameWidth,
        option,
        widget,
    )
    painter = QPainter(widget)
    widget.style().drawControl(
        QStyle.ControlElement.CE_ShapedFrame,
        option,
        painter,
        widget,
    )
    painter.end()
