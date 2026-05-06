from __future__ import annotations

from typing import Callable

import pyqtgraph as pg
from PySide6.QtCore import QObject, QRectF, Qt
from PySide6.QtGui import QPen
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode, SmartAxisItem
from .dialogs import show_customize_dialog
from .legend import PyQtLabGraphLegend
from .models import CurveState
from .styles import (
    DEFAULT_CURVE_COLOR_BY_THEME,
    DEFAULT_CURVE_COLORS,
    default_curve_style,
)
from .theme import PyQtLabGraphTheme, frame_style, theme_for_dark_mode
from .toolbar import PyQtLabGraphToolbar


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
        self.axis_text_color = theme_for_dark_mode(False).text

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
        color = color or DEFAULT_CURVE_COLORS[len(self.curve_order) % len(DEFAULT_CURVE_COLORS)]
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
            curve.style["line_color"] = DEFAULT_CURVE_COLOR_BY_THEME[self.dark_mode_enabled]
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
        theme = theme_for_dark_mode(enabled)

        self.axis_text_color = theme.text
        self.plot_widget.setBackground(theme.outer)
        self.plot_widget.setStyleSheet(f"background-color: {theme.outer};")
        self.view_box.setBackgroundColor(theme.plot)
        self.grid_item.setPen(pg.mkPen(theme.grid, width=1))
        for curve in self.curves.values():
            if curve.using_theme_color:
                curve.style["line_color"] = DEFAULT_CURVE_COLOR_BY_THEME[enabled]
            self._apply_curve_style(curve)
        self._style_legend()
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )

        axis_pen = pg.mkPen(theme.axis, width=1)
        tick_pen = pg.mkPen(theme.axis, width=1)
        text_pen = pg.mkPen(theme.text)
        for axis_name in ("bottom", "left", "top", "right"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setTickPen(tick_pen)
        self._apply_container_theme(theme)
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
        show_customize_dialog(self, curve_key)

    def _setup_plot(self) -> None:
        self.plot_item.layout.setContentsMargins(8, 8, 12, 8)
        self.plot_widget.setAntialiasing(True)
        self._set_axis_labels("Messzeit", "Temperatur", "s", "deg C")
        self.grid_item = pg.GridItem(
            pen=pg.mkPen(theme_for_dark_mode(False).grid, width=1),
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
        return default_curve_style(color)

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

    def _apply_container_theme(self, theme: PyQtLabGraphTheme) -> None:
        style = frame_style(theme)
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
