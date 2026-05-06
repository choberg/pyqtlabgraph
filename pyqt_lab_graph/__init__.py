from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pyqtgraph as pg
from PySide6.QtCore import QObject, QPoint, QPointF, QRect, QRectF, Qt, QTimer, QEvent
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QBrush
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QRubberBand,
    QSpinBox,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from pyqtgraph.graphicsItems.ScatterPlotItem import renderSymbol


pg.setConfigOptions(antialias=True)

__version__ = "0.1.0"


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


class AxisMode:
    AUTO = "auto"
    LINEAR = "linear"
    TIME = "time"


class SmartAxisItem(pg.AxisItem):
    """Axis item with support for relative time formatting and raw linear units."""

    def __init__(self, orientation: str, *args: object, **kwargs: object) -> None:
        self._mode = AxisMode.AUTO
        self._custom_units = ""
        super().__init__(orientation, *args, **kwargs)

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == AxisMode.LINEAR:
            self.enableAutoSIPrefix(False)
        elif mode == AxisMode.TIME:
            self.enableAutoSIPrefix(False)
        else:
            self.enableAutoSIPrefix(True)
        self.readjust_labels()

    def set_units(self, units: str | None) -> None:
        self._custom_units = units or ""
        # If in time mode, we don't use the standard unit display in the label
        # because the unit is attached to each tick.
        if self._mode == AxisMode.TIME:
            super().setLabel(units=None)
        else:
            super().setLabel(units=units)

    def setLabel(self, text: str | None = None, units: str | None = None, **args: object) -> None:
        self._custom_units = units or ""
        if self._mode == AxisMode.TIME:
            super().setLabel(text=text, units=None, **args)
        else:
            super().setLabel(text=text, units=units, **args)

    def readjust_labels(self) -> None:
        # Trigger a refresh of the labels by re-setting the unit
        self.setLabel(units=self._custom_units)

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        if self._mode != AxisMode.TIME:
            return super().tickStrings(values, scale, spacing)

        # Time formatting logic
        result = []
        for v in values:
            result.append(self._format_time(v, spacing))
        return result

    def _format_time(self, seconds: float, spacing: float) -> str:
        if seconds < 0:
            return f"-{self._format_time(-seconds, spacing)}"

        s = int(seconds)
        ms = seconds - s
        
        days = s // 86400
        hours = (s % 86400) // 3600
        minutes = (s % 3600) // 60
        secs = s % 60

        parts = []
        if days > 0:
            parts.append(f"{days} d")
        if hours > 0:
            parts.append(f"{hours} h")
        if minutes > 0:
            parts.append(f"{minutes} min")
        
        # Determine if we should show seconds or sub-seconds
        # If spacing is small enough, show decimals
        if spacing < 1.0:
            # How many decimals?
            if spacing < 0.001:
                fmt = f"{secs + ms:.3f}"
            elif spacing < 0.01:
                fmt = f"{secs + ms:.2f}"
            else:
                fmt = f"{secs + ms:.1f}"
            parts.append(f"{fmt} s")
        elif secs > 0 or not parts:
            parts.append(f"{secs} s")

        return " ".join(parts)


class PyQtLabGraphWidget(QObject):
    """Reusable PyQtGraph live plot with optional toolbar and rolling window support."""

    def __init__(
        self,
        plot_container: QWidget,
        toolbar_container: QWidget | None = None,
        legend_container: QWidget | None = None,
        *,
        show_toolbar: bool = True,
        show_legend: bool | None = None,
        legend_orientation: Qt.Orientation = Qt.Orientation.Vertical,
        rolling_window_seconds: float = 300.0,
    ) -> None:
        super().__init__(plot_container)
        self.plot_container = plot_container
        self.toolbar_container = toolbar_container
        self.legend_container = legend_container
        self.rolling_window_seconds = rolling_window_seconds

        # Use SmartAxisItem for bottom and left axes
        self.bottom_axis = SmartAxisItem(orientation="bottom")
        self.left_axis = SmartAxisItem(orientation="left")
        
        self.plot_widget = pg.PlotWidget(axisItems={"bottom": self.bottom_axis, "left": self.left_axis})
        self.plot_item = self.plot_widget.getPlotItem()
        self.view_box = self.plot_item.getViewBox()
        self.toolbar: PyQtLabGraphToolbar | None = None
        self.legend: PyQtLabGraphLegend | None = None

        self.curves: dict[str, CurveState] = {}
        self.curve_order: list[str] = []
        self.default_curve_color_by_theme = {
            False: "#1f77b4",
            True: "#4db6ff",
        }
        self.default_curve_colors = [
            "#1f77b4",
            "#ff7f0e",
            "#2ca02c",
            "#d62728",
            "#9467bd",
            "#8c564b",
        ]

        self.autoscale_x_enabled = True
        self.autoscale_y_enabled = True
        self.rolling_enabled = False
        self.applying_axis_scaling = False
        self.dark_mode_enabled = False
        self.x_label_text = "Messzeit"
        self.y_label_text = "Temperatur"
        self.x_label_units: str | None = "s"
        self.y_label_units: str | None = "deg C"
        self.x_axis_mode = AxisMode.AUTO
        self.y_axis_mode = AxisMode.AUTO
        self.axis_text_color = "#202124"

        self._setup_plot()

        self.plot_frame = self._create_plot_frame(self.plot_widget)
        self._embed_widget(self.plot_container, self.plot_frame)

        if show_toolbar and toolbar_container is not None:
            self.toolbar = PyQtLabGraphToolbar(
                self.plot_widget,
                toolbar_container,
                on_x_span_selected=self.apply_manual_x_limits,
                on_y_span_selected=self.apply_manual_y_limits,
                on_autoscale_x_changed=self.set_autoscale_x_enabled,
                on_autoscale_y_changed=self.set_autoscale_y_enabled,
                on_rolling_changed=self.set_rolling_enabled,
                on_rolling_window_selected=self.set_rolling_window_seconds,
                get_current_x_window_seconds=self.get_current_x_window_seconds,
                on_home_requested=self.show_all_data_with_autoscale,
                on_manual_navigation_started=self.disable_all_autoscaling,
                on_customize_requested=self.show_customize_dialog,
            )
            self.toolbar_frame = self._create_toolbar_frame(self.toolbar)
            self._embed_widget(toolbar_container, self.toolbar_frame)

        if (show_legend if show_legend is not None else legend_container is not None) and legend_container is not None:
            self.legend = PyQtLabGraphLegend(self, legend_orientation, legend_container)
            self.legend_frame = self._create_legend_frame(self.legend)
            self._embed_widget(legend_container, self.legend_frame)

        self.view_box.sigRangeChanged.connect(self._handle_view_range_changed)
        self.set_dark_mode_enabled(False)
        self._set_x_range(0.0, self.rolling_window_seconds)
        self._set_y_range(19.0, 25.0)

    def add_curve(
        self,
        key: str,
        *,
        label: str | None = None,
        color: str | None = None,
        style: dict[str, object] | None = None,
    ) -> None:
        if key in self.curves:
            raise ValueError(f'Curve "{key}" already exists.')
        color = color or self.default_curve_colors[len(self.curve_order) % len(self.default_curve_colors)]
        curve_style = self._default_curve_style(color)
        if style is not None:
            curve_style.update(style)
        item = self.plot_item.plot([], [], name=label or key, antialias=True)
        curve = CurveState(key=key, label=label or key, item=item, style=curve_style)
        self.curves[key] = curve
        self.curve_order.append(key)
        self._apply_curve_style(curve)
        self._refresh_legend()

    def add_point(self, key: str, x_value: float, y_value: float) -> None:
        curve = self._curve(key)
        curve.x_values.append(x_value)
        curve.y_values.append(y_value)
        curve.item.setData(curve.x_values, curve.y_values)
        self.apply_axis_scaling()

    def set_curve_data(self, key: str, x_values: list[float], y_values: list[float]) -> None:
        if len(x_values) != len(y_values):
            raise ValueError("x_values and y_values must have the same length.")
        curve = self._curve(key)
        curve.x_values = list(x_values)
        curve.y_values = list(y_values)
        curve.item.setData(curve.x_values, curve.y_values)
        self.apply_axis_scaling()

    def clear_curve(self, key: str) -> None:
        curve = self._curve(key)
        curve.x_values.clear()
        curve.y_values.clear()
        curve.item.setData([], [])
        self.apply_axis_scaling()

    def remove_curve(self, key: str) -> None:
        curve = self._curve(key)
        self.plot_item.removeItem(curve.item)
        del self.curves[key]
        self.curve_order.remove(key)
        self._refresh_legend()
        self.apply_axis_scaling()

    def set_curve_style(self, key: str, style: dict[str, object]) -> None:
        curve = self._curve(key)
        curve.style.update(style)
        curve.using_theme_color = bool(style.get("use_theme_color", False))
        if curve.using_theme_color:
            curve.style["line_color"] = self.default_curve_color_by_theme[self.dark_mode_enabled]
        self._apply_curve_style(curve)

    def curve_style(self, key: str) -> dict[str, object]:
        return dict(self._curve(key).style)

    def set_curve_visible(self, key: str, visible: bool) -> None:
        curve = self._curve(key)
        curve.visible = visible
        curve.item.setVisible(visible)
        self._update_legend_curve(key)
        self.apply_axis_scaling()

    def set_axis_labels(
        self,
        x_label: str,
        y_label: str,
        x_units: str | None = None,
        y_units: str | None = None,
        x_mode: str | None = None,
        y_mode: str | None = None,
    ) -> None:
        self._set_axis_labels(x_label, y_label, x_units, y_units, x_mode, y_mode)

    def set_grid_visible(self, visible: bool) -> None:
        self.grid_item.setVisible(visible)

    def set_autoscale_x_enabled(self, enabled: bool) -> None:
        self.autoscale_x_enabled = enabled
        if enabled:
            self.rolling_enabled = False
        self.apply_axis_scaling()

    def set_autoscale_y_enabled(self, enabled: bool) -> None:
        self.autoscale_y_enabled = enabled
        self.apply_axis_scaling()

    def set_rolling_enabled(self, enabled: bool) -> None:
        self.rolling_enabled = enabled
        if enabled:
            self.autoscale_x_enabled = False
        self.apply_axis_scaling()

    def set_rolling_window_seconds(self, seconds: float) -> None:
        if seconds <= 0.0:
            raise ValueError("Rolling window length must be greater than 0 seconds.")
        self.rolling_window_seconds = seconds
        if self.rolling_enabled:
            self.apply_axis_scaling()

    def get_current_x_window_seconds(self) -> float:
        xmin, xmax = self.get_x_range()
        return max(abs(xmax - xmin), 1.0)

    def get_x_range(self) -> tuple[float, float]:
        xmin, xmax = self.view_box.viewRange()[0]
        return float(xmin), float(xmax)

    def get_y_range(self) -> tuple[float, float]:
        ymin, ymax = self.view_box.viewRange()[1]
        return float(ymin), float(ymax)

    def apply_manual_x_limits(self, xmin: float, xmax: float) -> None:
        self.autoscale_x_enabled = False
        self.rolling_enabled = False
        self._set_x_range(min(xmin, xmax), max(xmin, xmax))

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        self.autoscale_y_enabled = False
        self._set_y_range(min(ymin, ymax), max(ymin, ymax))

    def disable_all_autoscaling(self) -> None:
        self.autoscale_x_enabled = False
        self.autoscale_y_enabled = False
        self.rolling_enabled = False

    def show_all_data_with_autoscale(self) -> None:
        self.rolling_enabled = False
        self.autoscale_x_enabled = True
        self.autoscale_y_enabled = True
        self.apply_axis_scaling()

    def set_dark_mode_enabled(self, enabled: bool) -> None:
        self.dark_mode_enabled = enabled
        if enabled:
            colors = {
                "outer": "#1f2329",
                "plot": "#181c20",
                "axis": "#d8dee9",
                "text": "#d8dee9",
                "grid": QColor(216, 222, 233, 38),
                "button": "#272c33",
                "button_hover": "#343b44",
                "button_disabled": "#1b1f24",
                "button_disabled_text": "#6b7280",
                "border": "#3a4048",
                "highlight": "#4b5563",
                "frame": "#1f2329",
            }
        else:
            colors = {
                "outer": "#f3f4f6",
                "plot": "#ffffff",
                "axis": "#000000",
                "text": "#202124",
                "grid": QColor(156, 163, 175, 70),
                "button": "#f8fafc",
                "button_hover": "#e5e7eb",
                "button_disabled": "#e5e7eb",
                "button_disabled_text": "#9ca3af",
                "border": "#c8ced6",
                "highlight": "#ffffff",
                "frame": "#f3f4f6",
            }

        self.axis_text_color = colors["text"]
        self.plot_widget.setBackground(colors["outer"])
        self.plot_widget.setStyleSheet(f"background-color: {colors['outer']};")
        self.view_box.setBackgroundColor(colors["plot"])
        self.grid_item.setPen(pg.mkPen(colors["grid"], width=1))
        for curve in self.curves.values():
            if curve.using_theme_color:
                curve.style["line_color"] = self.default_curve_color_by_theme[enabled]
            self._apply_curve_style(curve)
        self._style_legend()
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )

        axis_pen = pg.mkPen(colors["axis"], width=1)
        tick_pen = pg.mkPen(colors["axis"], width=1)
        text_pen = pg.mkPen(colors["text"])
        for axis_name in ("bottom", "left", "top", "right"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setTickPen(tick_pen)
        self._apply_container_theme(colors)
        if self.toolbar is not None:
            self.toolbar.set_dark_mode_enabled(enabled)

    def apply_axis_scaling(self) -> None:
        if self.autoscale_x_enabled:
            self._apply_x_autoscale()
        elif self.rolling_enabled:
            self._apply_x_rolling_window()
        if self.autoscale_y_enabled:
            self._apply_y_autoscale()

    def show_customize_dialog(self, curve_key: str | None = None) -> None:
        if not self.curve_order:
            return

        dialog = QDialog(self.plot_container)
        dialog.setWindowTitle("Customize")

        x_label = QLineEdit(self.x_label_text, dialog)
        y_label = QLineEdit(self.y_label_text, dialog)
        
        x_mode_combo = QComboBox(dialog)
        x_mode_combo.addItem("Auto (SI)", AxisMode.AUTO)
        x_mode_combo.addItem("Linear (Raw)", AxisMode.LINEAR)
        x_mode_combo.addItem("Time (h:min:s)", AxisMode.TIME)
        x_mode_combo.setCurrentIndex(x_mode_combo.findData(self.x_axis_mode))

        y_mode_combo = QComboBox(dialog)
        y_mode_combo.addItem("Auto (SI)", AxisMode.AUTO)
        y_mode_combo.addItem("Linear (Raw)", AxisMode.LINEAR)
        y_mode_combo.addItem("Time (h:min:s)", AxisMode.TIME)
        y_mode_combo.setCurrentIndex(y_mode_combo.findData(self.y_axis_mode))

        grid_checkbox = QCheckBox(dialog)
        grid_checkbox.setChecked(self.grid_item.isVisible())
        apply_x_range_checkbox = QCheckBox(dialog)
        apply_y_range_checkbox = QCheckBox(dialog)

        curve_combo = QComboBox(dialog)
        for key in self.curve_order:
            curve = self.curves[key]
            curve_combo.addItem(curve.label, key)
        if curve_key is not None:
            curve_index = curve_combo.findData(curve_key)
            curve_combo.setCurrentIndex(max(curve_index, 0))

        line_enabled_checkbox = QCheckBox(dialog)
        line_color_button = QPushButton(dialog)
        line_width_spin = QDoubleSpinBox(dialog)
        line_width_spin.setRange(0.1, 20.0)
        line_width_spin.setDecimals(1)
        line_width_spin.setSingleStep(0.1)
        marker_enabled_checkbox = QCheckBox(dialog)
        marker_filled_checkbox = QCheckBox(dialog)
        marker_symbol_combo = QComboBox(dialog)
        marker_options = [
            ("Circle", "o"),
            ("Square", "s"),
            ("Diamond", "d"),
            ("Triangle up", "t1"),
            ("Triangle down", "t"),
            ("Triangle right", "t2"),
            ("Triangle left", "t3"),
            ("Pentagon", "p"),
            ("Hexagon", "h"),
            ("Star", "star"),
            ("Plus", "+"),
            ("Cross", "x"),
            ("Crosshair", "crosshair"),
        ]
        for label, symbol in marker_options:
            marker_symbol_combo.addItem(label, symbol)
        marker_size_spin = QSpinBox(dialog)
        marker_size_spin.setRange(1, 40)

        selected_color = QColor()

        def load_curve_style(index: int) -> None:
            nonlocal selected_color
            curve = self.curves[str(curve_combo.itemData(index))]
            style = curve.style
            line_enabled_checkbox.setChecked(bool(style["line_enabled"]))
            selected_color = QColor(str(style["line_color"]))
            self._set_color_button_style(line_color_button, selected_color)
            line_width_spin.setValue(float(style["line_width"]))
            marker_enabled_checkbox.setChecked(bool(style["marker_enabled"]))
            marker_filled_checkbox.setChecked(bool(style["marker_filled"]))
            marker_index = marker_symbol_combo.findData(str(style["marker_symbol"]))
            marker_symbol_combo.setCurrentIndex(max(marker_index, 0))
            marker_size_spin.setValue(int(style["marker_size"]))

        def choose_line_color() -> None:
            nonlocal selected_color
            selected = QColorDialog.getColor(selected_color, dialog, "Line color")
            if selected.isValid():
                selected_color = selected
                self._set_color_button_style(line_color_button, selected_color)

        curve_combo.currentIndexChanged.connect(load_curve_style)
        line_color_button.clicked.connect(choose_line_color)
        load_curve_style(curve_combo.currentIndex())

        xmin, xmax = self.get_x_range()
        ymin, ymax = self.get_y_range()
        x_min_spin = self._range_spin_box(xmin, dialog)
        x_max_spin = self._range_spin_box(xmax, dialog)
        y_min_spin = self._range_spin_box(ymin, dialog)
        y_max_spin = self._range_spin_box(ymax, dialog)

        layout = QFormLayout(dialog)
        layout.addRow("X label:", x_label)
        layout.addRow("X mode:", x_mode_combo)
        layout.addRow("Y label:", y_label)
        layout.addRow("Y mode:", y_mode_combo)
        layout.addRow("Grid:", grid_checkbox)
        layout.addRow("Curve:", curve_combo)
        layout.addRow("Line:", line_enabled_checkbox)
        layout.addRow("Line color:", line_color_button)
        layout.addRow("Line width:", line_width_spin)
        layout.addRow("Markers:", marker_enabled_checkbox)
        layout.addRow("Filled markers:", marker_filled_checkbox)
        layout.addRow("Marker shape:", marker_symbol_combo)
        layout.addRow("Marker size:", marker_size_spin)
        layout.addRow("Apply X range:", apply_x_range_checkbox)
        layout.addRow("X range:", self._range_row(x_min_spin, x_max_spin))
        layout.addRow("Apply Y range:", apply_y_range_checkbox)
        layout.addRow("Y range:", self._range_row(y_min_spin, y_max_spin))

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.set_axis_labels(
            x_label.text(),
            y_label.text(),
            x_mode=x_mode_combo.currentData(),
            y_mode=y_mode_combo.currentData(),
        )
        self.set_grid_visible(grid_checkbox.isChecked())
        selected_curve_key = str(curve_combo.currentData())
        self.set_curve_style(
            selected_curve_key,
            {
                "line_enabled": line_enabled_checkbox.isChecked(),
                "line_color": selected_color.name(),
                "line_width": line_width_spin.value(),
                "marker_enabled": marker_enabled_checkbox.isChecked(),
                "marker_filled": marker_filled_checkbox.isChecked(),
                "marker_symbol": marker_symbol_combo.currentData(),
                "marker_size": marker_size_spin.value(),
            },
        )
        if apply_x_range_checkbox.isChecked():
            self.apply_manual_x_limits(
                min(x_min_spin.value(), x_max_spin.value()),
                max(x_min_spin.value(), x_max_spin.value()),
            )
            if self.toolbar is not None:
                self.toolbar.set_autoscale_x_checked(False)
                self.toolbar.set_rolling_checked(False)
        if apply_y_range_checkbox.isChecked():
            self.apply_manual_y_limits(
                min(y_min_spin.value(), y_max_spin.value()),
                max(y_min_spin.value(), y_max_spin.value()),
            )
            if self.toolbar is not None:
                self.toolbar.set_autoscale_y_checked(False)

    def _setup_plot(self) -> None:
        self.plot_item.layout.setContentsMargins(8, 8, 12, 8)
        self.plot_widget.setAntialiasing(True)
        self._set_axis_labels("Messzeit", "Temperatur", "s", "deg C")
        self.grid_item = pg.GridItem(
            pen=pg.mkPen(QColor(156, 163, 175, 70), width=1),
            textPen=None,
        )
        self.grid_item.setZValue(-10)
        self.plot_item.addItem(self.grid_item, ignoreBounds=True)
        self.plot_item.showGrid(x=False, y=False)
        self.plot_item.setMenuEnabled(False)
        self.plot_item.hideButtons()
        self.plot_item.showAxis("top", show=True)
        self.plot_item.showAxis("right", show=True)

        for axis_name in ("bottom", "left"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setStyle(tickLength=8, tickTextOffset=8, tickAlpha=1.0, maxTickLevel=1)
        self.plot_item.getAxis("bottom").setHeight(54)
        self.plot_item.getAxis("left").setWidth(62)
        for axis_name in ("top", "right"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setStyle(showValues=False, tickLength=0)

    def _refresh_legend(self) -> None:
        if self.legend is not None:
            self.legend.refresh()

    def _style_legend(self) -> None:
        if self.legend is not None:
            self.legend.apply_theme(self.dark_mode_enabled)

    def _update_legend_curve(self, key: str) -> None:
        if self.legend is not None:
            self.legend.update_curve(key)

    def _curve(self, key: str) -> CurveState:
        try:
            return self.curves[key]
        except KeyError as exc:
            raise KeyError(f'Curve "{key}" does not exist.') from exc

    def _default_curve_style(self, color: str) -> dict[str, object]:
        return {
            "line_enabled": True,
            "line_color": color,
            "line_width": 1.2,
            "marker_symbol": "o",
            "marker_size": 5,
            "marker_enabled": True,
            "marker_filled": True,
        }

    def _apply_curve_style(self, curve: CurveState) -> None:
        style = curve.style
        color = str(style["line_color"])
        line_width = float(style["line_width"])
        marker_size = int(style["marker_size"])
        marker_symbol = str(style["marker_symbol"])
        line_enabled = bool(style["line_enabled"])
        marker_enabled = bool(style["marker_enabled"])
        marker_filled = bool(style["marker_filled"])

        curve.item.setPen(pg.mkPen(color, width=line_width) if line_enabled else None)
        curve.item.setSymbol(marker_symbol if marker_enabled else None)
        curve.item.setSymbolSize(marker_size if marker_enabled else 0)
        curve.item.setSymbolBrush(
            pg.mkBrush(color) if marker_enabled and marker_filled else pg.mkBrush(None)
        )
        curve.item.setSymbolPen(
            pg.mkPen(color, width=0 if marker_filled else 1.4) if marker_enabled else None
        )
        curve.item.scatter.setPen(
            pg.mkPen(color, width=0 if marker_filled else 1.4) if marker_enabled else None
        )
        curve.item.scatter.setBrush(
            pg.mkBrush(color) if marker_enabled and marker_filled else pg.mkBrush(None)
        )
        self._update_legend_curve(curve.key)

    def _apply_x_autoscale(self) -> None:
        x_values = [x for curve in self.curves.values() if curve.visible for x in curve.x_values]
        if not x_values:
            return
        self._set_x_range(0.0, max(max(x_values), 10.0))

    def _apply_x_rolling_window(self) -> None:
        x_values = [x for curve in self.curves.values() if curve.visible for x in curve.x_values]
        if not x_values:
            return
        latest_x = max(x_values)
        right = max(latest_x, self.rolling_window_seconds)
        left = max(0.0, right - self.rolling_window_seconds)
        self._set_x_range(left, right)

    def _apply_y_autoscale(self) -> None:
        visible_values = self._visible_y_values()
        if not visible_values:
            visible_values = [
                y for curve in self.curves.values() if curve.visible for y in curve.y_values
            ]
        if not visible_values:
            return
        minimum = min(visible_values)
        maximum = max(visible_values)
        margin = 1.0 if minimum == maximum else (maximum - minimum) * 0.1
        self._set_y_range(minimum - margin, maximum + margin)

    def _visible_y_values(self) -> list[float]:
        xmin, xmax = self.get_x_range()
        values: list[float] = []
        for curve in self.curves.values():
            if not curve.visible:
                continue
            values.extend(
                y for x, y in zip(curve.x_values, curve.y_values) if xmin <= x <= xmax
            )
        return values

    def _set_x_range(self, xmin: float, xmax: float) -> None:
        self._set_range(lambda: self.plot_item.setXRange(xmin, xmax, padding=0.0))

    def _set_y_range(self, ymin: float, ymax: float) -> None:
        self._set_range(lambda: self.plot_item.setYRange(ymin, ymax, padding=0.0))

    def _set_range(self, setter: Callable[[], None]) -> None:
        self.applying_axis_scaling = True
        try:
            setter()
        finally:
            self.applying_axis_scaling = False

    def _set_axis_labels(
        self,
        x_label: str,
        y_label: str,
        x_units: str | None = None,
        y_units: str | None = None,
        x_mode: str | None = None,
        y_mode: str | None = None,
    ) -> None:
        self.x_label_text = x_label
        self.y_label_text = y_label
        self.x_label_units = x_units
        self.y_label_units = y_units
        if x_mode is not None:
            self.x_axis_mode = x_mode
        if y_mode is not None:
            self.y_axis_mode = y_mode

        self.bottom_axis.set_mode(self.x_axis_mode)
        self.bottom_axis.setLabel(
            x_label,
            units=x_units,
            **{"color": self.axis_text_color, "margin-top": "24px"},
        )
        self.left_axis.set_mode(self.y_axis_mode)
        self.left_axis.setLabel(
            y_label,
            units=y_units,
            **{"color": self.axis_text_color, "margin-right": "24px"},
        )

    def _handle_view_range_changed(self, *_args: object) -> None:
        if self.applying_axis_scaling:
            return
        self.disable_all_autoscaling()
        if self.toolbar is not None:
            self.toolbar.mark_manual_navigation_started()

    def _apply_container_theme(self, colors: dict[str, object]) -> None:
        style = f"""
            QFrame#plotFrame,
            QFrame#toolbarFrame,
            QFrame#legendFrame {{
                background-color: {colors['frame']};
                border: 1px solid {colors['border']};
                border-top-color: {colors['highlight']};
                border-left-color: {colors['highlight']};
                border-radius: 6px;
            }}
            QToolBar {{
                background-color: {colors['frame']};
                border: none;
                spacing: 2px;
            }}
            QToolButton,
            QPushButton {{
                background-color: {colors['button']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QToolButton:hover,
            QPushButton:hover {{
                background-color: {colors['button_hover']};
            }}
            QToolButton:checked {{
                background-color: {colors['button_hover']};
                border-color: {colors['highlight']};
            }}
            QPushButton:disabled {{
                background-color: {colors['button_disabled']};
                color: {colors['button_disabled_text']};
            }}
            QMenu {{
                background-color: {colors['frame']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
            }}
            QMenu::item:selected {{
                background-color: {colors['button_hover']};
            }}
        """
        self.plot_frame.setStyleSheet(style)
        if self.toolbar_container is not None:
            self.toolbar_container.setStyleSheet(style)
        if self.toolbar is not None and hasattr(self, "toolbar_frame"):
            self.toolbar_frame.setStyleSheet(style)
        if hasattr(self, "legend_frame"):
            self.legend_frame.setStyleSheet(style)

    @staticmethod
    def _create_plot_frame(plot_widget: pg.PlotWidget) -> QFrame:
        return PyQtLabGraphWidget._create_raised_frame("plotFrame", plot_widget, 8)

    @staticmethod
    def _create_toolbar_frame(toolbar: "PyQtLabGraphToolbar") -> QFrame:
        return PyQtLabGraphWidget._create_raised_frame("toolbarFrame", toolbar, 4)

    @staticmethod
    def _create_legend_frame(legend: "PyQtLabGraphLegend") -> QFrame:
        return PyQtLabGraphWidget._create_raised_frame("legendFrame", legend, 2)

    @staticmethod
    def _create_raised_frame(object_name: str, child: QWidget, margin: int) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(0)
        layout.addWidget(child)
        return frame

    @staticmethod
    def _embed_widget(container: QWidget, widget: QWidget) -> None:
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            container.setLayout(layout)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(widget)

    @staticmethod
    def _range_spin_box(value: float, parent: QWidget) -> QDoubleSpinBox:
        spin_box = QDoubleSpinBox(parent)
        spin_box.setRange(-1_000_000.0, 1_000_000.0)
        spin_box.setDecimals(3)
        spin_box.setValue(value)
        return spin_box

    @staticmethod
    def _range_row(min_spin: QDoubleSpinBox, max_spin: QDoubleSpinBox) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel("Min"))
        layout.addWidget(min_spin)
        layout.addWidget(QLabel("Max"))
        layout.addWidget(max_spin)
        return widget

    @staticmethod
    def _set_color_button_style(button: QPushButton, color: QColor) -> None:
        button.setText(color.name())
        text_color = "#ffffff" if color.lightness() < 128 else "#111827"
        button.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {color.name()};
                color: {text_color};
                border: 1px solid #6b7280;
                border-radius: 4px;
                padding: 4px 8px;
            }}
            """
        )


class AxisSpanZoomFilter(QObject):
    """Rubber-band span selection for one-shot X/Y zoom actions."""

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
        self.viewport_widget.installEventFilter(self)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.rubber_band.hide()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is not self.viewport_widget or not self.enabled:
            return False

        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            self.rubber_band.setGeometry(QRect(self.origin, self.origin))
            self.rubber_band.show()
            return True

        if event.type() == QEvent.Type.MouseMove and self.rubber_band.isVisible():
            current = event.position().toPoint()
            if self.direction == "x":
                top_left = QPoint(min(self.origin.x(), current.x()), 0)
                bottom_right = QPoint(max(self.origin.x(), current.x()), self.viewport_widget.height())
            else:
                top_left = QPoint(0, min(self.origin.y(), current.y()))
                bottom_right = QPoint(self.viewport_widget.width(), max(self.origin.y(), current.y()))
            self.rubber_band.setGeometry(QRect(top_left, bottom_right).normalized())
            return True

        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self.rubber_band.isVisible():
                self.rubber_band.hide()
                current = event.position().toPoint()
                start_value = self._map_view_value(self.origin)
                end_value = self._map_view_value(current)
                self.on_selected(start_value, end_value)
            return True

        return False

    def _map_view_value(self, point: QPoint) -> float:
        scene_point = self.plot_widget.mapToScene(point)
        view_point = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(scene_point)
        return float(view_point.x() if self.direction == "x" else view_point.y())


class PyQtLabGraphToolbar(QToolBar):
    """PyQtGraph toolbar for PyQtLabGraphWidget."""

    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        parent: QWidget | None = None,
        on_x_span_selected: Callable[[float, float], None] | None = None,
        on_y_span_selected: Callable[[float, float], None] | None = None,
        on_autoscale_x_changed: Callable[[bool], None] | None = None,
        on_autoscale_y_changed: Callable[[bool], None] | None = None,
        on_rolling_changed: Callable[[bool], None] | None = None,
        on_rolling_window_selected: Callable[[float], None] | None = None,
        get_current_x_window_seconds: Callable[[], float] | None = None,
        on_home_requested: Callable[[], None] | None = None,
        on_manual_navigation_started: Callable[[], None] | None = None,
        on_customize_requested: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.plot_widget = plot_widget
        self.on_x_span_selected = on_x_span_selected
        self.on_y_span_selected = on_y_span_selected
        self.on_autoscale_x_changed = on_autoscale_x_changed
        self.on_autoscale_y_changed = on_autoscale_y_changed
        self.on_rolling_changed = on_rolling_changed
        self.on_rolling_window_selected = on_rolling_window_selected
        self.get_current_x_window_seconds = get_current_x_window_seconds
        self.on_home_requested = on_home_requested
        self.on_manual_navigation_started = on_manual_navigation_started
        self.on_customize_requested = on_customize_requested
        self.dark_mode_enabled = False
        self._themed_icon_actions: list[tuple[QAction, str, QIcon | None]] = []

        self.setMovable(False)
        self.setIconSize(QPixmap(24, 24).size())

        self.home_action = self._add_action("reset_zoom.png", "Home", self.home)
        self.pan_action = self._add_action("pan.png", "Pan", self.pan, checkable=True)
        self.zoom_action = self._add_action("zoom_area.png", "Zoom", self.zoom, checkable=True)
        self.addSeparator()
        self.x_zoom_action = self._add_action("x-zoom.png", "X-Zoom", self.set_x_zoom_enabled, checkable=True, fallback_icon=self._create_axis_zoom_icon("x"))
        self.y_zoom_action = self._add_action("y-zoom.png", "Y-Zoom", self.set_y_zoom_enabled, checkable=True, fallback_icon=self._create_axis_zoom_icon("y"))
        self.addSeparator()
        self.autoscale_x_action = self._add_action("autox.png", "Autoscale X", self._autoscale_x_toggled, checkable=True)
        self.autoscale_x_action.blockSignals(True)
        self.autoscale_x_action.setChecked(True)
        self.autoscale_x_action.blockSignals(False)
        self.autoscale_y_action = self._add_action("autoy.png", "Autoscale Y", self._autoscale_y_toggled, checkable=True)
        self.autoscale_y_action.blockSignals(True)
        self.autoscale_y_action.setChecked(True)
        self.autoscale_y_action.blockSignals(False)
        self.rolling_button = self._create_rolling_button()
        self.addWidget(self.rolling_button)
        self.addSeparator()
        self.customize_action = self._add_action("edit_params.png", "Customize", self.customize)
        self.save_action = self._add_action("saveplot.png", "Save", self.save_figure)
        self.x_span_filter = AxisSpanZoomFilter(plot_widget, "x", self._apply_x_zoom, self)
        self.y_span_filter = AxisSpanZoomFilter(plot_widget, "y", self._apply_y_zoom, self)

    def home(self) -> None:
        self._disable_custom_zoom_actions()
        self.pan_action.setChecked(False)
        self.zoom_action.setChecked(False)
        self._set_mouse_mode(pg.ViewBox.PanMode)
        self.set_rolling_checked(False)
        self.set_autoscale_x_checked(True)
        self.set_autoscale_y_checked(True)
        if self.on_home_requested is not None:
            self.on_home_requested()

    def pan(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self._disable_custom_zoom_actions()
            self.zoom_action.setChecked(False)
            self._set_mouse_mode(pg.ViewBox.PanMode)

    def zoom(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self._disable_custom_zoom_actions()
            self.pan_action.setChecked(False)
            self._set_mouse_mode(pg.ViewBox.RectMode)
        else:
            self._set_mouse_mode(pg.ViewBox.PanMode)

    def customize(self) -> None:
        if self.on_customize_requested is not None:
            self.on_customize_requested()

    def save_figure(self) -> None:
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Save plot",
            str(Path.cwd() / "plot.png"),
            "PNG Images (*.png);;All Files (*)",
        )
        if not filename:
            return
        try:
            import pyqtgraph.exporters
            exporter = pyqtgraph.exporters.ImageExporter(self.plot_widget.getPlotItem())
            exporter.export(filename)
        except Exception as exc:
            raise RuntimeError(f"Could not save PyQtGraph plot to {filename}: {exc}") from exc

    def set_x_zoom_enabled(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self.y_zoom_action.setChecked(False)
            self.pan_action.setChecked(False)
            self.zoom_action.setChecked(False)
        self.x_span_filter.set_enabled(enabled)

    def set_y_zoom_enabled(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self.x_zoom_action.setChecked(False)
            self.pan_action.setChecked(False)
            self.zoom_action.setChecked(False)
        self.y_span_filter.set_enabled(enabled)

    def set_autoscale_x_checked(self, checked: bool) -> None:
        self.autoscale_x_action.blockSignals(True)
        self.autoscale_x_action.setChecked(checked)
        self.autoscale_x_action.blockSignals(False)

    def set_autoscale_y_checked(self, checked: bool) -> None:
        self.autoscale_y_action.blockSignals(True)
        self.autoscale_y_action.setChecked(checked)
        self.autoscale_y_action.blockSignals(False)

    def set_rolling_checked(self, checked: bool) -> None:
        self.rolling_button.blockSignals(True)
        self.rolling_button.setChecked(checked)
        self.rolling_button.blockSignals(False)

    def mark_manual_navigation_started(self) -> None:
        self.set_autoscale_x_checked(False)
        self.set_autoscale_y_checked(False)
        self.set_rolling_checked(False)

    def set_dark_mode_enabled(self, enabled: bool) -> None:
        self.dark_mode_enabled = enabled
        for action, icon_filename, fallback_icon in self._themed_icon_actions:
            action.setIcon(self._themed_icon(icon_filename, fallback_icon))
        if hasattr(self, "rolling_button"):
            self.rolling_button.setIcon(self._themed_icon("rolling.png"))

    def _apply_x_zoom(self, xmin: float, xmax: float) -> None:
        if xmin != xmax and self.on_x_span_selected is not None:
            self.on_x_span_selected(xmin, xmax)
        self.set_autoscale_x_checked(False)
        self.set_rolling_checked(False)
        self.x_zoom_action.setChecked(False)

    def _apply_y_zoom(self, ymin: float, ymax: float) -> None:
        if ymin != ymax and self.on_y_span_selected is not None:
            self.on_y_span_selected(ymin, ymax)
        self.set_autoscale_y_checked(False)
        self.y_zoom_action.setChecked(False)

    def _autoscale_x_toggled(self, enabled: bool) -> None:
        if enabled:
            self.set_rolling_checked(False)
            if self.on_rolling_changed is not None:
                self.on_rolling_changed(False)
        if self.on_autoscale_x_changed is not None:
            self.on_autoscale_x_changed(enabled)

    def _autoscale_y_toggled(self, enabled: bool) -> None:
        if self.on_autoscale_y_changed is not None:
            self.on_autoscale_y_changed(enabled)

    def _rolling_toggled(self, enabled: bool) -> None:
        if enabled:
            self.set_autoscale_x_checked(False)
            if self.on_autoscale_x_changed is not None:
                self.on_autoscale_x_changed(False)
        if self.on_rolling_changed is not None:
            self.on_rolling_changed(enabled)

    def _enable_rolling_window(self, seconds: float) -> None:
        if self.on_rolling_window_selected is not None:
            self.on_rolling_window_selected(seconds)
        self.set_rolling_checked(True)
        self._rolling_toggled(True)

    def _enable_current_x_rolling_window(self) -> None:
        if self.get_current_x_window_seconds is not None:
            self._enable_rolling_window(self.get_current_x_window_seconds())

    def _enable_custom_rolling_window(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Rolling Window")
        spin_box = QDoubleSpinBox(dialog)
        spin_box.setRange(1.0, 86400.0)
        spin_box.setDecimals(1)
        spin_box.setSuffix(" s")
        spin_box.setValue(300.0)
        layout = QFormLayout(dialog)
        layout.addRow("Seconds:", spin_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._enable_rolling_window(spin_box.value())

    def _create_rolling_button(self) -> QToolButton:
        button = QToolButton(self)
        button.setText("Rolling")
        button.setIcon(self._themed_icon("rolling.png"))
        button.setToolTip("Rolling window")
        button.setCheckable(True)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        button.toggled.connect(self._rolling_toggled)
        menu = QMenu(button)
        current_x_action = QAction("Current X", menu)
        current_x_action.triggered.connect(self._enable_current_x_rolling_window)
        menu.addAction(current_x_action)
        five_min_action = QAction("5 min", menu)
        five_min_action.triggered.connect(lambda: self._enable_rolling_window(300.0))
        menu.addAction(five_min_action)
        thirty_min_action = QAction("30 min", menu)
        thirty_min_action.triggered.connect(lambda: self._enable_rolling_window(1800.0))
        menu.addAction(thirty_min_action)
        custom_action = QAction("Custom", menu)
        custom_action.triggered.connect(self._enable_custom_rolling_window)
        menu.addAction(custom_action)
        button.setMenu(menu)
        return button

    def _notify_manual_navigation_started(self) -> None:
        self.mark_manual_navigation_started()
        if self.on_manual_navigation_started is not None:
            self.on_manual_navigation_started()

    def _disable_custom_zoom_actions(self) -> None:
        if self.x_zoom_action.isChecked():
            self.x_zoom_action.setChecked(False)
        if self.y_zoom_action.isChecked():
            self.y_zoom_action.setChecked(False)

    def _set_mouse_mode(self, mode: int) -> None:
        self.plot_widget.getPlotItem().getViewBox().setMouseMode(mode)

    def _add_action(self, icon_filename: str, text: str, slot: Callable, checkable: bool = False, fallback_icon: QIcon | None = None) -> QAction:
        icon = self._themed_icon(icon_filename, fallback_icon)
        action = QAction(icon, text, self)
        action.setToolTip(text)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(slot)
        else:
            action.triggered.connect(slot)
        self.addAction(action)
        if icon_filename:
            self._themed_icon_actions.append((action, icon_filename, fallback_icon))
        return action

    def _themed_icon(self, filename: str, fallback_icon: QIcon | None = None) -> QIcon:
        if not filename:
            return fallback_icon or QIcon()
        icon = self._recolored_png_icon(filename, QColor("#e5e7eb")) if self.dark_mode_enabled else self._png_icon(filename)
        if icon.isNull() and fallback_icon is not None:
            return fallback_icon
        return icon

    @staticmethod
    def _png_icon(filename: str) -> QIcon:
        icon_path = Path(__file__).resolve().parent / "assets" / filename
        return QIcon(str(icon_path))

    @staticmethod
    def _recolored_png_icon(filename: str, color: QColor) -> QIcon:
        icon_path = Path(__file__).resolve().parent / "assets" / filename
        source = QPixmap(str(icon_path))
        if source.isNull():
            return QIcon()
        recolored = QPixmap(source.size())
        recolored.setDevicePixelRatio(source.devicePixelRatio())
        recolored.fill(Qt.GlobalColor.transparent)
        painter = QPainter(recolored)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(recolored.rect(), color)
        painter.end()
        return QIcon(recolored)

    @staticmethod
    def _create_axis_zoom_icon(axis: str) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame_pen = QPen(QColor("#5f6368"), 1.4)
        accent_color = QColor("#1f77b4") if axis == "x" else QColor("#ff7f0e")
        accent_pen = QPen(accent_color, 2.0)
        marker_pen = QPen(accent_color, 1.2)
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(4.5, 4.5, 14.0, 14.0))
        painter.setPen(marker_pen)
        if axis == "x":
            painter.drawLine(QPointF(7.0, 6.0), QPointF(7.0, 17.0))
            painter.drawLine(QPointF(17.0, 6.0), QPointF(17.0, 17.0))
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(7.0, 12.0), QPointF(17.0, 12.0))
            painter.drawLine(QPointF(7.0, 12.0), QPointF(10.0, 9.0))
            painter.drawLine(QPointF(7.0, 12.0), QPointF(10.0, 15.0))
            painter.drawLine(QPointF(17.0, 12.0), QPointF(14.0, 9.0))
            painter.drawLine(QPointF(17.0, 12.0), QPointF(14.0, 15.0))
        else:
            painter.drawLine(QPointF(6.0, 7.0), QPointF(17.0, 7.0))
            painter.drawLine(QPointF(6.0, 17.0), QPointF(17.0, 17.0))
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(12.0, 7.0), QPointF(12.0, 17.0))
            painter.drawLine(QPointF(12.0, 7.0), QPointF(9.0, 10.0))
            painter.drawLine(QPointF(12.0, 7.0), QPointF(15.0, 10.0))
            painter.drawLine(QPointF(12.0, 17.0), QPointF(9.0, 14.0))
            painter.drawLine(QPointF(12.0, 17.0), QPointF(15.0, 14.0))
        painter.setFont(QFont("Sans Serif", 7, QFont.Weight.Bold))
        painter.setPen(QPen(accent_color, 1.0))
        painter.drawText(QRectF(14.0, 13.0, 9.0, 9.0), Qt.AlignmentFlag.AlignCenter, axis.upper())
        painter.end()
        return QIcon(pixmap)
