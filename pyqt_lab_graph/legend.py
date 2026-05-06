from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from pyqtgraph.graphicsItems.ScatterPlotItem import renderSymbol


class PyQtLabGraphLegend(QWidget):
    """Qt legend panel for PyQtLabGraphWidget curves."""

    def __init__(
        self,
        plot: "PyQtLabGraphWidget",
        orientation: Qt.Orientation = Qt.Orientation.Vertical,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.plot = plot
        self.orientation = orientation
        self.items_by_key: dict[str, PyQtLabGraphLegendItem] = {}
        self.setObjectName("livePlotLegend")
        self.layout = QVBoxLayout(self) if orientation == Qt.Orientation.Vertical else QHBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.setSpacing(4)
        if orientation == Qt.Orientation.Vertical:
            self.layout.addStretch(1)
        self.apply_theme(False)

    def refresh(self) -> None:
        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.items_by_key.clear()
        for key in self.plot.curve_order:
            legend_item = PyQtLabGraphLegendItem(self.plot, key, self)
            self.items_by_key[key] = legend_item
            self.layout.addWidget(legend_item)
        if self.orientation == Qt.Orientation.Vertical:
            self.layout.addStretch(1)

    def update_curve(self, key: str) -> None:
        item = self.items_by_key.get(key)
        if item is not None:
            item.refresh()

    def apply_theme(self, dark_mode_enabled: bool) -> None:
        if dark_mode_enabled:
            self.setStyleSheet(
                """
                QWidget#livePlotLegend {
                    background-color: #1f2329;
                    color: #d8dee9;
                }
                """
            )
        else:
            self.setStyleSheet(
                """
                QWidget#livePlotLegend {
                    background-color: #f3f4f6;
                    color: #202124;
                }
                """
            )
        for item in self.items_by_key.values():
            item.refresh()


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
        self._click_timer.setInterval(220)
        self._click_timer.timeout.connect(self._toggle_curve_visibility)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 3, 6, 3)
        layout.setSpacing(6)
        layout.addWidget(self.sample)
        layout.addWidget(self.label)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.refresh()

    def refresh(self) -> None:
        curve = self.plot.curves[self.curve_key]
        self.label.setText(curve.label)
        if curve.visible:
            text_color = self.plot.axis_text_color
            opacity = "1.0"
        else:
            text_color = "#6b7280" if self.plot.dark_mode_enabled else "#9ca3af"
            opacity = "0.55"
        self.setStyleSheet(
            f"""
            PyQtLabGraphLegendItem {{
                border-radius: 4px;
            }}
            PyQtLabGraphLegendItem:hover {{
                background-color: rgba(148, 163, 184, 45);
            }}
            QLabel {{
                color: {text_color};
            }}
            """
        )
        self.setToolTip("Click to show/hide. Double-click to edit style.")
        self.sample.opacity = float(opacity)
        self.sample.update()

    def mousePressEvent(self, event: QEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.start()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._click_timer.stop()
            self.plot.show_customize_dialog(self.curve_key)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _toggle_curve_visibility(self) -> None:
        self.plot.set_curve_visible(
            self.curve_key,
            not self.plot.curves[self.curve_key].visible,
        )


class CurveSampleWidget(QWidget):
    """Draws a centered line and PyQtGraph marker sample for a legend item."""

    def __init__(self, plot: "PyQtLabGraphWidget", curve_key: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.plot = plot
        self.curve_key = curve_key
        self.opacity = 1.0
        self.setFixedSize(42, 22)

    def paintEvent(self, _event: QEvent) -> None:
        curve = self.plot.curves[self.curve_key]
        style = curve.style
        color = QColor(str(style["line_color"]))
        color.setAlphaF(color.alphaF() * self.opacity)
        line_enabled = bool(style["line_enabled"])
        marker_enabled = bool(style["marker_enabled"])
        marker_filled = bool(style["marker_filled"])
        marker_symbol = str(style["marker_symbol"])
        marker_size = max(int(style["marker_size"]), 11)
        line_width = float(style["line_width"])

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        center_y = self.height() / 2.0
        if line_enabled:
            painter.setPen(QPen(color, line_width))
            painter.drawLine(QPointF(3.0, center_y), QPointF(self.width() - 3.0, center_y))
        if marker_enabled:
            pen = QPen(color, 1.0 if marker_filled else 1.1)
            pen.setCosmetic(True)
            brush = QBrush(color) if marker_filled else QBrush(Qt.BrushStyle.NoBrush)
            symbol_image = renderSymbol(marker_symbol, marker_size, pen, brush)
            x = int((self.width() - symbol_image.width()) / 2)
            y = int((self.height() - symbol_image.height()) / 2)
            painter.drawImage(x, y, symbol_image)
        painter.end()


