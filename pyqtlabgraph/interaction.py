from __future__ import annotations

from typing import Any, Callable, Literal

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QRubberBand

from .models import InteractionTool
from .themes import (
    ZOOM_SELECTION_BORDER_ALPHA,
    ZOOM_SELECTION_COLOR,
    ZOOM_SELECTION_FILL_ALPHA,
)

_ZOOM_SELECTION_BORDER_WIDTH = 1
_ZOOM_CURSOR_SIZE = 31
_ZOOM_CURSOR_CENTER = _ZOOM_CURSOR_SIZE // 2
_ZOOM_CURSOR_CROSS_HALF_SIZE = 5
_ZOOM_CURSOR_ARROW_HEAD_DEPTH = 2
_ZOOM_CURSOR_ARROW_HEAD_HALF_WIDTH = 2
_X_ZOOM_ARROW_START = QPoint(22, 7)
_X_ZOOM_ARROW_END = QPoint(28, 7)
_Y_ZOOM_ARROW_START = QPoint(24, 4)
_Y_ZOOM_ARROW_END = QPoint(24, 10)


def _plot_viewport_rect(plot_widget: pg.PlotWidget) -> QRect:
    scene_rect = plot_widget.getPlotItem().getViewBox().sceneBoundingRect()
    top_left = plot_widget.mapFromScene(scene_rect.topLeft())
    bottom_right = plot_widget.mapFromScene(scene_rect.bottomRight())
    return QRect(top_left, bottom_right).normalized()


def _zoom_cursor_color(plot_background: str) -> QColor:
    background = QColor(plot_background)
    cursor_color = (
        Qt.GlobalColor.black
        if background.lightnessF() >= 0.5
        else Qt.GlobalColor.white
    )
    return QColor(cursor_color)


def _render_zoom_cursor_pixmap(
    tool: InteractionTool,
    color: QColor,
    device_pixel_ratio: float,
) -> QPixmap:
    if tool not in {
        InteractionTool.RECT_ZOOM,
        InteractionTool.X_ZOOM,
        InteractionTool.Y_ZOOM,
    }:
        raise ValueError(f"Unsupported zoom cursor tool: {tool}")

    ratio = max(1.0, float(device_pixel_ratio))
    physical_size = max(1, round(_ZOOM_CURSOR_SIZE * ratio))
    pixmap = QPixmap(physical_size, physical_size)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
    pen = QPen(color)
    pen.setWidth(1)
    pen.setCosmetic(True)
    pen.setCapStyle(Qt.PenCapStyle.SquareCap)
    painter.setPen(pen)
    cross_start = _ZOOM_CURSOR_CENTER - _ZOOM_CURSOR_CROSS_HALF_SIZE
    cross_end = _ZOOM_CURSOR_CENTER + _ZOOM_CURSOR_CROSS_HALF_SIZE
    painter.drawLine(
        QPoint(cross_start, _ZOOM_CURSOR_CENTER),
        QPoint(cross_end, _ZOOM_CURSOR_CENTER),
    )
    painter.drawLine(
        QPoint(_ZOOM_CURSOR_CENTER, cross_start),
        QPoint(_ZOOM_CURSOR_CENTER, cross_end),
    )

    if tool == InteractionTool.X_ZOOM:
        _draw_zoom_direction_arrow(painter, _X_ZOOM_ARROW_START, _X_ZOOM_ARROW_END)
    elif tool == InteractionTool.Y_ZOOM:
        _draw_zoom_direction_arrow(painter, _Y_ZOOM_ARROW_START, _Y_ZOOM_ARROW_END)
    painter.end()
    return pixmap


def _draw_zoom_direction_arrow(
    painter: QPainter,
    start: QPoint,
    end: QPoint,
) -> None:
    painter.drawLine(start, end)
    horizontal = start.y() == end.y()
    for tip, inward_direction in ((start, 1), (end, -1)):
        if horizontal:
            inward = inward_direction * _ZOOM_CURSOR_ARROW_HEAD_DEPTH
            painter.drawLine(
                tip,
                tip + QPoint(inward, -_ZOOM_CURSOR_ARROW_HEAD_HALF_WIDTH),
            )
            painter.drawLine(
                tip,
                tip + QPoint(inward, _ZOOM_CURSOR_ARROW_HEAD_HALF_WIDTH),
            )
        else:
            inward = inward_direction * _ZOOM_CURSOR_ARROW_HEAD_DEPTH
            painter.drawLine(
                tip,
                tip + QPoint(-_ZOOM_CURSOR_ARROW_HEAD_HALF_WIDTH, inward),
            )
            painter.drawLine(
                tip,
                tip + QPoint(_ZOOM_CURSOR_ARROW_HEAD_HALF_WIDTH, inward),
            )


def _create_zoom_cursor(
    tool: InteractionTool,
    plot_background: str,
    device_pixel_ratio: float,
) -> QCursor:
    pixmap = _render_zoom_cursor_pixmap(
        tool,
        _zoom_cursor_color(plot_background),
        device_pixel_ratio,
    )
    return QCursor(pixmap, _ZOOM_CURSOR_CENTER, _ZOOM_CURSOR_CENTER)


class _PyQtLabGraphPlotWidget(pg.PlotWidget):
    """PlotWidget that gives an active zoom tool cursor hover priority."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._zoom_cursor_tool = InteractionTool.NONE
        self._zoom_cursor_background = "#ffffff"
        self._zoom_cursor: QCursor | None = None
        self._zoom_cursor_applied = False
        super().__init__(*args, **kwargs)

    def set_zoom_tool_cursor(self, tool: InteractionTool, plot_background: str) -> None:
        self._zoom_cursor_tool = tool
        self._zoom_cursor_background = plot_background
        if tool == InteractionTool.NONE:
            self._zoom_cursor = None
            self._clear_zoom_cursor()
            return
        self._zoom_cursor = _create_zoom_cursor(
            tool,
            plot_background,
            self.viewport().devicePixelRatioF(),
        )
        self._refresh_zoom_cursor_at_global_position()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        super().mouseMoveEvent(event)
        self._apply_zoom_cursor_at(event.position().toPoint())

    def leaveEvent(self, event: QEvent) -> None:
        super().leaveEvent(event)
        self._clear_zoom_cursor()

    def event(self, event: QEvent) -> bool:
        handled = super().event(event)
        if (
            event.type() == QEvent.Type.DevicePixelRatioChange
            and self._zoom_cursor_tool != InteractionTool.NONE
        ):
            self._zoom_cursor = _create_zoom_cursor(
                self._zoom_cursor_tool,
                self._zoom_cursor_background,
                self.viewport().devicePixelRatioF(),
            )
            self._refresh_zoom_cursor_at_global_position()
        return handled

    def _refresh_zoom_cursor_at_global_position(self) -> None:
        viewport_position = self.viewport().mapFromGlobal(QCursor.pos())
        self._apply_zoom_cursor_at(viewport_position)

    def _apply_zoom_cursor_at(self, viewport_position: QPoint) -> None:
        if self._zoom_cursor is None or not _plot_viewport_rect(self).contains(
            viewport_position
        ):
            self._clear_zoom_cursor()
            return
        self.viewport().setCursor(self._zoom_cursor)
        self._zoom_cursor_applied = True

    def _clear_zoom_cursor(self) -> None:
        if not self._zoom_cursor_applied:
            return
        self.viewport().unsetCursor()
        self._zoom_cursor_applied = False


class _PyQtLabGraphViewBox(pg.ViewBox):
    """ViewBox with PyQtLabGraph mouse-wheel interaction extensions."""

    def wheelEvent(self, ev: Any, axis: int | None = None) -> None:
        if axis is None:
            if ev.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().wheelEvent(ev, axis=0)
                return
            elif ev.modifiers() & Qt.KeyboardModifier.ControlModifier:
                super().wheelEvent(ev, axis=1)
                return
        super().wheelEvent(ev, axis=axis)


class _AxisSpanZoomFilter(QObject):
    """Widget-owned rubber-band span selection for X/Y zoom tools."""

    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        direction: Literal["x", "y"],
        on_selected: Callable[[float, float], None],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        if direction not in ("x", "y"):
            raise ValueError(f"direction must be 'x' or 'y', got '{direction}'")
        self.plot_widget = plot_widget
        self.viewport_widget = plot_widget.viewport()
        self.direction = direction
        self.on_selected = on_selected
        self.enabled = False
        self.origin = QPoint()
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport_widget)
        self._style_rubber_band()
        self.viewport_widget.installEventFilter(self)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.rubber_band.hide()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is not getattr(self, "viewport_widget", None) or not getattr(
            self, "enabled", False
        ):
            return False

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            # The filter is installed on the complete graphics-view viewport,
            # which also contains the axes. Leave presses outside the ViewBox
            # to pyqtgraph so AxisItem can handle axis-specific panning.
            press_position = event.position().toPoint()
            if not self._plot_rect().contains(press_position):
                return False
            self.origin = self._clamp_to_plot_rect(press_position)
            self.rubber_band.setGeometry(self._selection_rect(self.origin))
            self.rubber_band.show()
            return True

        if event.type() == QEvent.Type.MouseMove and self.rubber_band.isVisible():
            current = self._clamp_to_plot_rect(event.position().toPoint())
            self.rubber_band.setGeometry(self._selection_rect(current))
            return True

        if (
            event.type() == QEvent.Type.MouseButtonRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            if not self.rubber_band.isVisible():
                return False
            self.rubber_band.hide()
            current = self._clamp_to_plot_rect(event.position().toPoint())
            start_value = self._map_view_value(self.origin)
            end_value = self._map_view_value(current)
            self.on_selected(start_value, end_value)
            return True

        return False

    def _selection_rect(self, current: QPoint) -> QRect:
        plot_rect = self._plot_rect()
        if self.direction == "x":
            top_left = QPoint(min(self.origin.x(), current.x()), plot_rect.top())
            bottom_right = QPoint(max(self.origin.x(), current.x()), plot_rect.bottom())
        else:
            top_left = QPoint(plot_rect.left(), min(self.origin.y(), current.y()))
            bottom_right = QPoint(plot_rect.right(), max(self.origin.y(), current.y()))
        return QRect(top_left, bottom_right).normalized()

    def _clamp_to_plot_rect(self, point: QPoint) -> QPoint:
        plot_rect = self._plot_rect()
        return QPoint(
            max(plot_rect.left(), min(point.x(), plot_rect.right())),
            max(plot_rect.top(), min(point.y(), plot_rect.bottom())),
        )

    def _plot_rect(self) -> QRect:
        return _plot_viewport_rect(self.plot_widget)

    def _map_view_value(self, point: QPoint) -> float:
        scene_point = self.plot_widget.mapToScene(point)
        view_point = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(scene_point)
        return float(view_point.x() if self.direction == "x" else view_point.y())

    def _style_rubber_band(self) -> None:
        color = QColor(ZOOM_SELECTION_COLOR)
        fill = f"{color.red()}, {color.green()}, {color.blue()}, {ZOOM_SELECTION_FILL_ALPHA}"
        border = f"{color.red()}, {color.green()}, {color.blue()}, {ZOOM_SELECTION_BORDER_ALPHA}"
        self.rubber_band.setStyleSheet(
            "QRubberBand {"
            f"background-color: rgba({fill});"
            f"border: {_ZOOM_SELECTION_BORDER_WIDTH}px solid rgba({border});"
            "}"
        )
