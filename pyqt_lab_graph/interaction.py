from __future__ import annotations

from typing import Any, Callable

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QRubberBand

from .themes import (
    ZOOM_SELECTION_BORDER_ALPHA,
    ZOOM_SELECTION_COLOR,
    ZOOM_SELECTION_FILL_ALPHA,
)

_ZOOM_SELECTION_BORDER_WIDTH = 1


class _PyQtLabGraphViewBox(pg.ViewBox):
    """ViewBox with PyQtLabGraph mouse-wheel interaction extensions."""

    def wheelEvent(self, ev: Any, axis: int | None = None) -> None:
        if axis is None and ev.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            super().wheelEvent(ev, axis=0)
            return
        super().wheelEvent(ev, axis=axis)


class _AxisSpanZoomFilter(QObject):
    """Widget-owned rubber-band span selection for X/Y zoom tools."""

    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        direction: str,
        on_selected: Callable[[float, float], None],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
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
        if watched is not self.viewport_widget or not self.enabled:
            return False

        if (
            event.type() == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            self.origin = self._clamp_to_plot_rect(event.position().toPoint())
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
            if self.rubber_band.isVisible():
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
        scene_rect = self.plot_widget.getPlotItem().getViewBox().sceneBoundingRect()
        top_left = self.plot_widget.mapFromScene(scene_rect.topLeft())
        bottom_right = self.plot_widget.mapFromScene(scene_rect.bottomRight())
        return QRect(top_left, bottom_right).normalized()

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
