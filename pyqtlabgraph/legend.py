from __future__ import annotations

from typing import TYPE_CHECKING

from pyqtgraph.graphicsItems.ScatterPlotItem import renderSymbol
from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .qt_styles import paint_host_frame

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget

_LEGEND_LAYOUT_MARGINS = (4, 4, 4, 4)
_LEGEND_LAYOUT_SPACING = 4
_LEGEND_VERTICAL_STRETCH = 1

_LEGEND_ITEM_CLICK_DELAY_MS = 220
_LEGEND_ITEM_MARGINS = (6, 3, 6, 3)
_LEGEND_ITEM_SPACING = 6
_LEGEND_ITEM_VISIBLE_OPACITY = 1.0
_LEGEND_ITEM_HIDDEN_OPACITY = 0.55

_SAMPLE_WIDTH = 42
_SAMPLE_HEIGHT = 22
_SAMPLE_MIN_MARKER_SIZE = 11
_SAMPLE_LINE_INSET = 3.0
_SAMPLE_CENTER_DIVISOR = 2.0
_SAMPLE_FILLED_MARKER_OUTLINE_WIDTH = 0.0


class PyQtLabGraphLegend(QWidget):
    """Qt legend panel for PyQtLabGraphWidget curves."""

    def __init__(
        self,
        plot: "PyQtLabGraphWidget",
        *,
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        parent: QWidget | None = None,
        show_frame: bool = True,
    ) -> None:
        super().__init__(parent)
        self.plot = plot
        self._show_frame = show_frame
        self.orientation = orientation
        self.items_by_key: dict[str, PyQtLabGraphLegendItem] = {}
        self.setObjectName("pyqtLabGraphLegend")
        if orientation == Qt.Orientation.Vertical:
            self._layout = QVBoxLayout(self)
        else:
            self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(*_LEGEND_LAYOUT_MARGINS)
        self._layout.setSpacing(_LEGEND_LAYOUT_SPACING)
        if orientation == Qt.Orientation.Vertical:
            self._layout.addStretch(_LEGEND_VERTICAL_STRETCH)
        plot.curve_added.connect(lambda _key: self.refresh())
        plot.curve_removed.connect(lambda _key: self.refresh())
        plot.curve_changed.connect(self.update_curve)
        plot.presentation_changed.connect(self.refresh_palette)
        plot.state_reset.connect(self.refresh)
        self.refresh()

    def refresh(self) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.items_by_key.clear()
        for key, _label in self.plot.curve_choices():
            legend_item = PyQtLabGraphLegendItem(self.plot, key, self)
            self.items_by_key[key] = legend_item
            self._layout.addWidget(legend_item)
        if self.orientation == Qt.Orientation.Vertical:
            self._layout.addStretch(_LEGEND_VERTICAL_STRETCH)

    def update_curve(self, key: str) -> None:
        item = self.items_by_key.get(key)
        if item is not None:
            item.refresh()

    def refresh_palette(self) -> None:
        for item in self.items_by_key.values():
            item.refresh()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._show_frame:
            paint_host_frame(self)


class PyQtLabGraphLegendItem(QWidget):
    """Clickable legend row for a single curve."""

    def __init__(self, plot: "PyQtLabGraphWidget", curve_key: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.plot = plot
        self.curve_key = curve_key
        self.sample = CurveSampleWidget(plot, curve_key, self)
        self.label = QLabel(self)
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(_LEGEND_ITEM_CLICK_DELAY_MS)
        self._click_timer.timeout.connect(self._toggle_curve_visibility)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(*_LEGEND_ITEM_MARGINS)
        layout.setSpacing(_LEGEND_ITEM_SPACING)
        layout.addWidget(self.sample)
        layout.addWidget(self.label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh()

    def refresh(self) -> None:
        curve_labels = dict(self.plot.curve_choices())
        if self.curve_key not in curve_labels:
            return
        visible = self.plot.curve_visible(self.curve_key)
        self.label.setText(curve_labels[self.curve_key])
        if visible:
            opacity = _LEGEND_ITEM_VISIBLE_OPACITY
        else:
            opacity = _LEGEND_ITEM_HIDDEN_OPACITY
        self.label.setEnabled(visible)
        self.setToolTip("Click to show/hide. Double-click to edit style.")
        self.sample.opacity = opacity
        self.sample.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.start()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.plot.show_customize_dialog(self.curve_key)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _toggle_curve_visibility(self) -> None:
        if self.curve_key not in dict(self.plot.curve_choices()):
            return
        self.plot.set_curve_visible(
            self.curve_key,
            not self.plot.curve_visible(self.curve_key),
        )


class CurveSampleWidget(QWidget):
    """Draws a centered line and PyQtGraph marker sample for a legend item."""

    def __init__(self, plot: "PyQtLabGraphWidget", curve_key: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.plot = plot
        self.curve_key = curve_key
        self.opacity = _LEGEND_ITEM_VISIBLE_OPACITY
        self.setFixedSize(_SAMPLE_WIDTH, _SAMPLE_HEIGHT)

    def paintEvent(self, _event: QPaintEvent) -> None:
        if self.curve_key not in dict(self.plot.curve_choices()):
            return
        style = self.plot.curve_style(self.curve_key)
        color = QColor(style.line_color)
        color.setAlphaF(color.alphaF() * self.opacity)
        line_enabled = style.line_enabled
        marker_enabled = style.marker_enabled
        marker_filled = style.marker_filled
        marker_symbol = style.marker_symbol
        marker_size = max(style.marker_size, _SAMPLE_MIN_MARKER_SIZE)
        marker_outline_width = style.marker_outline_width
        line_width = style.line_width

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_y = self.height() / _SAMPLE_CENTER_DIVISOR
        if line_enabled:
            painter.setPen(QPen(color, line_width))
            painter.drawLine(
                QPointF(_SAMPLE_LINE_INSET, center_y),
                QPointF(self.width() - _SAMPLE_LINE_INSET, center_y),
            )
        if marker_enabled:
            pen = QPen(
                color,
                _SAMPLE_FILLED_MARKER_OUTLINE_WIDTH if marker_filled else marker_outline_width,
            )
            pen.setCosmetic(True)
            brush = QBrush(color) if marker_filled else QBrush(Qt.BrushStyle.NoBrush)
            symbol_image = renderSymbol(marker_symbol, marker_size, pen, brush)
            x = int((self.width() - symbol_image.width()) / _SAMPLE_CENTER_DIVISOR)
            y = int((self.height() - symbol_image.height()) / _SAMPLE_CENTER_DIVISOR)
            painter.drawImage(x, y, symbol_image)
        painter.end()
