from __future__ import annotations

import math
from pathlib import Path
import re
from typing import Any, Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRubberBand,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode, SmartAxisItem, resolve_axis_mode
from .dialogs import show_customize_dialog
from .legend import PyQtLabGraphLegend
from .layouts import PlotLayoutState, load_plot_layout, save_plot_layout
from .models import CurveState, InteractionState, InteractionTool
from .styles import (
    CurveStyle,
    PyQtLabGraphPlotStyle,
    resolve_plot_style,
)
from .qt_styles import host_frame_fallback_style, plot_widget_chrome_style
from .themes import (
    PyQtLabGraphTheme,
    ZOOM_SELECTION_BORDER_ALPHA,
    ZOOM_SELECTION_COLOR,
    ZOOM_SELECTION_FILL_ALPHA,
    resolve_theme,
)
from .toolbar import PyQtLabGraphToolbar


_DEFAULT_X_RANGE = (0.0, 1.0)
_DEFAULT_Y_RANGE = (0.0, 1.0)

_ADAPTIVE_PERFORMANCE_THRESHOLD = 5_000
_ADAPTIVE_PERFORMANCE_RESTORE_THRESHOLD = 3_000

_PLOT_LAYOUT_MARGINS = (8, 8, 12, 8)
_PRIMARY_AXIS_TICK_LENGTH = 8
_PRIMARY_AXIS_TICK_TEXT_OFFSET = 8
_PRIMARY_AXIS_TICK_ALPHA = 1.0
_PRIMARY_AXIS_MAX_TICK_LEVEL = 1
_SECONDARY_AXIS_TICK_LENGTH = 0
_BOTTOM_AXIS_HEIGHT = 54
_LEFT_AXIS_WIDTH = 62
_AXIS_LABEL_TOP_MARGIN = "24px"
_AXIS_LABEL_RIGHT_MARGIN = "24px"
_AXIS_PEN_WIDTH = 1

_GRID_LINE_WIDTH = 1
_GRID_Z_VALUE = -10
_RANGE_PADDING = 0.0
_ZOOM_SELECTION_BORDER_WIDTH = 1
_VIEW_BOX_BACKGROUND_OVERDRAW = 1.0

_PLOT_FRAME_MARGIN = 8
_TOOLBAR_FRAME_MARGIN = 4
_LEGEND_FRAME_MARGIN = 2
_EMBEDDED_CONTAINER_MARGIN = 0
_FRAME_LAYOUT_SPACING = 0

_X_AUTOSCALE_EQUAL_VALUE_MARGIN = 1.0
_Y_AUTOSCALE_EQUAL_VALUE_MARGIN = 1.0
_Y_AUTOSCALE_MARGIN_RATIO = 0.1

_RANGE_EDITOR_DECIMALS = 3
_RANGE_EDITOR_MARGIN = 6
_RANGE_EDITOR_SPACING = 6
_RANGE_EDITOR_OFFSET = QPoint(8, 8)
_RANGE_EDITOR_VALUE_PATTERN = re.compile(
    r"^\s*"
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?)"
    r"\s*([A-Za-zµμ]*)"
    r"\s*$"
)
_RANGE_EDITOR_SUFFIX_FACTORS = {
    "": 1.0,
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "µ": 1e-6,
    "μ": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}
_RANGE_EDITOR_ERROR_STYLE = "QLineEdit { border: 1px solid #c2410c; }"


class _PyQtLabGraphViewBox(pg.ViewBox):
    """ViewBox with PyQtLabGraph mouse-wheel interaction extensions."""

    def wheelEvent(self, ev: Any, axis: int | None = None) -> None:
        if axis is None and ev.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            super().wheelEvent(ev, axis=0)
            return
        super().wheelEvent(ev, axis=axis)


class _AxisRangePopup(QWidget):
    """Small popup editor for manually entering one axis range."""

    def __init__(
        self,
        axis_label: str,
        minimum: float,
        maximum: float,
        on_apply: Callable[[float, float], None],
        parent: QWidget,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.on_apply = on_apply
        self.setObjectName("pyqtLabGraphAxisRangePopup")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _RANGE_EDITOR_MARGIN,
            _RANGE_EDITOR_MARGIN,
            _RANGE_EDITOR_MARGIN,
            _RANGE_EDITOR_MARGIN,
        )
        layout.setSpacing(_RANGE_EDITOR_SPACING)
        layout.addWidget(QLabel(f"{axis_label} min:", self))
        self.minimum_edit = self._create_line_edit(minimum, "pyqtLabGraphAxisMinEdit")
        layout.addWidget(self.minimum_edit)
        layout.addWidget(QLabel(f"{axis_label} max:", self))
        self.maximum_edit = self._create_line_edit(maximum, "pyqtLabGraphAxisMaxEdit")
        layout.addWidget(self.maximum_edit)

        for widget in (self.minimum_edit, self.maximum_edit):
            widget.installEventFilter(self)

    def focus_first_field(self) -> None:
        self.minimum_edit.setFocus(Qt.FocusReason.PopupFocusReason)
        self.minimum_edit.selectAll()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                self._apply_and_close()
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.close()
                return True
        return super().eventFilter(watched, event)

    def _apply_and_close(self) -> None:
        minimum = self._parse_editor_value(self.minimum_edit)
        maximum = self._parse_editor_value(self.maximum_edit)
        if minimum is None or maximum is None:
            if minimum is None:
                self.minimum_edit.setFocus(Qt.FocusReason.OtherFocusReason)
                self.minimum_edit.selectAll()
            else:
                self.maximum_edit.setFocus(Qt.FocusReason.OtherFocusReason)
                self.maximum_edit.selectAll()
            return

        self.on_apply(minimum, maximum)
        self.close()

    def _create_line_edit(self, value: float, object_name: str) -> QLineEdit:
        line_edit = QLineEdit(_format_range_editor_value(value), self)
        line_edit.setObjectName(object_name)
        line_edit.textEdited.connect(lambda _text, editor=line_edit: editor.setStyleSheet(""))
        return line_edit

    def _parse_editor_value(self, line_edit: QLineEdit) -> float | None:
        try:
            value = _parse_range_editor_value(line_edit.text())
        except ValueError:
            line_edit.setStyleSheet(_RANGE_EDITOR_ERROR_STYLE)
            return None

        line_edit.setStyleSheet("")
        return value


def _format_range_editor_value(value: float) -> str:
    return f"{value:.{_RANGE_EDITOR_DECIMALS}f}"


def _parse_range_editor_value(text: str) -> float:
    match = _RANGE_EDITOR_VALUE_PATTERN.match(text)
    if match is None:
        raise ValueError(f'Invalid range value "{text}".')

    suffix = match.group(2)
    if suffix not in _RANGE_EDITOR_SUFFIX_FACTORS:
        raise ValueError(f'Unknown range value suffix "{suffix}".')

    value = float(match.group(1)) * _RANGE_EDITOR_SUFFIX_FACTORS[suffix]
    if not math.isfinite(value):
        raise ValueError(f'Range value "{text}" is not finite.')
    return value


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


class PyQtLabGraphWidget(QObject):
    """Reusable PyQtGraph live plot with optional toolbar and rolling window support."""

    def __init__(
        self,
        plot_container: QWidget,
        toolbar_container: QWidget | None = None,
        legend_container: QWidget | None = None,
        *,
        plot_identifier: str,
        layout_path: str | Path | None = None,
        show_toolbar: bool = True,
        show_legend: bool | None = None,
        legend_orientation: Qt.Orientation = Qt.Orientation.Vertical,
        rolling_window_size: float = 300.0,
        theme: str | PyQtLabGraphTheme | None = None,
        plot_style: str | PyQtLabGraphPlotStyle | None = None,
        show_component_frames: bool = True,
    ) -> None:
        super().__init__(plot_container)
        if not plot_identifier.strip():
            raise ValueError("PyQtLabGraph plot_identifier must not be empty.")
        self.plot_identifier = plot_identifier
        self.layout_path = Path(layout_path) if layout_path is not None else None
        self.plot_container = plot_container
        self.toolbar_container = toolbar_container
        self.legend_container = legend_container
        self.rolling_window_size = rolling_window_size
        self.show_component_frames = show_component_frames

        # Use SmartAxisItem for bottom and left axes
        self.bottom_axis = SmartAxisItem(orientation="bottom")
        self.left_axis = SmartAxisItem(orientation="left")
        self.bottom_axis.double_clicked.connect(self._show_axis_range_editor)
        self.left_axis.double_clicked.connect(self._show_axis_range_editor)
        
        self.plot_widget = pg.PlotWidget(
            axisItems={"bottom": self.bottom_axis, "left": self.left_axis},
            viewBox=_PyQtLabGraphViewBox(),
        )
        self.plot_widget.setObjectName("pyqtLabGraphPlotWidget")
        self.plot_widget.installEventFilter(self)
        self.plot_item = self.plot_widget.getPlotItem()
        self.view_box = self.plot_item.getViewBox()
        self.view_box.sigResized.connect(self._extend_view_box_background)
        self.x_span_filter = _AxisSpanZoomFilter(
            self.plot_widget,
            "x",
            self._apply_x_span_zoom,
            self,
        )
        self.y_span_filter = _AxisSpanZoomFilter(
            self.plot_widget,
            "y",
            self._apply_y_span_zoom,
            self,
        )
        self.toolbar: PyQtLabGraphToolbar | None = None
        self.legend: PyQtLabGraphLegend | None = None
        self.plot_frame: QFrame | None = None
        self.toolbar_frame: QFrame | None = None
        self.legend_frame: QFrame | None = None
        self._axis_range_popup: _AxisRangePopup | None = None

        self.curves: dict[str, CurveState] = {}
        self.curve_order: list[str] = []

        self.interaction_state = InteractionState()
        self.applying_axis_scaling = False
        self.antialiasing_enabled = True
        self.downsampling_enabled = True
        self.clip_to_view_enabled = True
        self.adaptive_performance_enabled = True
        self.adaptive_performance_active = False
        self.adaptive_performance_threshold = _ADAPTIVE_PERFORMANCE_THRESHOLD
        self.adaptive_performance_restore_threshold = _ADAPTIVE_PERFORMANCE_RESTORE_THRESHOLD
        self.theme = resolve_theme(theme)
        self.plot_style = resolve_plot_style(plot_style)
        self.x_label_text = "X"
        self.y_label_text = "Y"
        self.x_label_units: str | None = None
        self.y_label_units: str | None = None
        self.x_axis_mode = AxisMode.AUTO
        self.y_axis_mode = AxisMode.AUTO

        self._setup_plot()

        self.plot_frame = self._embed_component(
            self.plot_container,
            self.plot_widget,
            self._create_plot_frame,
        )
        if self.plot_frame is not None:
            self.plot_frame.installEventFilter(self)

        if show_toolbar and toolbar_container is not None:
            self.toolbar = PyQtLabGraphToolbar(
                toolbar_container,
                on_tool_requested=self.request_tool,
                on_autoscale_x_requested=self.request_autoscale_x,
                on_autoscale_y_requested=self.request_autoscale_y,
                on_rolling_requested=self.request_rolling_x,
                on_rolling_window_selected=self.set_rolling_window_size,
                get_current_x_window_size=self.get_current_x_window_size,
                on_show_all_requested=self.request_show_all,
                on_save_requested=self.save_figure,
                on_customize_requested=self.show_customize_dialog,
            )
            self.toolbar_frame = self._embed_component(
                toolbar_container,
                self.toolbar,
                self._create_toolbar_frame,
            )

        if (show_legend if show_legend is not None else legend_container is not None) and legend_container is not None:
            self.legend = PyQtLabGraphLegend(self, legend_orientation, legend_container)
            self.legend_frame = self._embed_component(
                legend_container,
                self.legend,
                self._create_legend_frame,
            )

        self.view_box.sigRangeChanged.connect(self._handle_view_range_changed)
        self.set_theme(self.theme)
        self._set_x_range(*_DEFAULT_X_RANGE)
        self._set_y_range(*_DEFAULT_Y_RANGE)

    def add_curve(
        self,
        key: str,
        *,
        label: str | None = None,
        color: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem:
        if key in self.curves:
            raise ValueError(f'Curve "{key}" already exists.')
        curve_style = self._default_curve_style(len(self.curve_order), color)
        if style is not None:
            curve_style = style
        item = self.plot_item.plot(
            [],
            [],
            name=label or key,
            antialias=self._effective_antialiasing_enabled(),
            useCache=self._marker_cache_enabled(),
        )
        curve = CurveState(key=key, label=label or key, item=item, style=curve_style)
        self.curves[key] = curve
        self.curve_order.append(key)
        self._apply_curve_rendering_options(curve)
        self._apply_curve_style(curve)
        self._refresh_legend()
        return item

    def add_point(self, key: str, x_value: float, y_value: float) -> None:
        curve = self._curve(key)
        x_values, y_values = self._curve_data(curve)
        curve.item.setData(
            np.append(x_values, x_value),
            np.append(y_values, y_value),
        )
        self.apply_axis_scaling()

    def set_data(self, key: str, *args: Any, **kwargs: Any) -> None:
        curve = self._curve(key)
        curve.item.setData(*args, **kwargs)
        self._apply_curve_rendering_options(curve)
        self._apply_curve_style(curve)
        self.apply_axis_scaling()

    def plot(
        self,
        key: str,
        *args: Any,
        label: str | None = None,
        color: str | None = None,
        style: CurveStyle | None = None,
        **kwargs: Any,
    ) -> pg.PlotDataItem:
        item = self.add_curve(key, label=label, color=color, style=style)
        self.set_data(key, *args, **kwargs)
        return item

    def curve_data(self, key: str) -> tuple[np.ndarray, np.ndarray]:
        return self._curve_data(self._curve(key))

    @property
    def native_plot_widget(self) -> pg.PlotWidget:
        return self.plot_widget

    @property
    def native_plot_item(self) -> pg.PlotItem:
        return self.plot_item

    @property
    def native_view_box(self) -> pg.ViewBox:
        return self.view_box

    def curve_item(self, key: str) -> pg.PlotDataItem:
        return self._curve(key).item

    def clear_curve(self, key: str) -> None:
        curve = self._curve(key)
        curve.item.setData([], [])
        self.apply_axis_scaling()

    def remove_curve(self, key: str) -> None:
        curve = self._curve(key)
        self.plot_item.removeItem(curve.item)
        del self.curves[key]
        self.curve_order.remove(key)
        self._refresh_legend()
        self.apply_axis_scaling()

    def set_curve_style(self, key: str, style: CurveStyle) -> None:
        curve = self._curve(key)
        curve.style = style
        self._apply_curve_style(curve)

    def curve_style(self, key: str) -> CurveStyle:
        return self._curve(key).style

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
        x_mode: str | AxisMode | None = None,
        y_mode: str | AxisMode | None = None,
    ) -> None:
        self._set_axis_labels(x_label, y_label, x_units, y_units, x_mode, y_mode)

    def set_grid_visible(self, visible: bool) -> None:
        self.grid_item.setVisible(visible)

    def set_antialiasing_enabled(self, enabled: bool) -> None:
        self.antialiasing_enabled = enabled
        self.plot_widget.setAntialiasing(self._effective_antialiasing_enabled())
        for curve in self.curves.values():
            self._apply_curve_rendering_options(curve)

    def set_downsampling_enabled(self, enabled: bool) -> None:
        self.downsampling_enabled = enabled
        for curve in self.curves.values():
            self._apply_curve_rendering_options(curve)

    def set_clip_to_view_enabled(self, enabled: bool) -> None:
        self.clip_to_view_enabled = enabled
        for curve in self.curves.values():
            self._apply_curve_rendering_options(curve)

    def set_adaptive_performance_enabled(self, enabled: bool) -> None:
        self.adaptive_performance_enabled = enabled
        self._update_adaptive_performance(force=True)

    def request_autoscale_x(self, enabled: bool) -> None:
        self.interaction_state.autoscale_x = enabled
        if enabled:
            self.interaction_state.rolling_x = False
        self._sync_toolbar_state()
        self.apply_axis_scaling()

    def request_autoscale_y(self, enabled: bool) -> None:
        self.interaction_state.autoscale_y = enabled
        self._sync_toolbar_state()
        self.apply_axis_scaling()

    def request_rolling_x(self, enabled: bool) -> None:
        self.interaction_state.rolling_x = enabled
        if enabled:
            self.interaction_state.autoscale_x = False
        self._sync_toolbar_state()
        self.apply_axis_scaling()

    def request_tool(self, tool: InteractionTool, enabled: bool) -> None:
        self.interaction_state.active_tool = tool if enabled else InteractionTool.NONE
        if enabled:
            self.interaction_state.autoscale_x = False
            self.interaction_state.autoscale_y = False
            self.interaction_state.rolling_x = False
        self._apply_interaction_behavior()
        self._sync_toolbar_state()

    def request_show_all(self) -> None:
        self.interaction_state = InteractionState()
        self._apply_interaction_behavior()
        self._sync_toolbar_state()
        self.apply_axis_scaling()

    def request_manual_navigation(self) -> None:
        self.interaction_state.autoscale_x = False
        self.interaction_state.autoscale_y = False
        self.interaction_state.rolling_x = False
        self._sync_toolbar_state()

    def set_rolling_window_size(self, size: float) -> None:
        if size <= 0.0:
            raise ValueError("Rolling window size must be greater than 0.")
        self.rolling_window_size = size
        if self.interaction_state.rolling_x:
            self.apply_axis_scaling()

    def get_current_x_window_size(self) -> float:
        xmin, xmax = self.get_x_range()
        return max(abs(xmax - xmin), 1.0)

    def get_x_range(self) -> tuple[float, float]:
        xmin, xmax = self.view_box.viewRange()[0]
        return float(xmin), float(xmax)

    def get_y_range(self) -> tuple[float, float]:
        ymin, ymax = self.view_box.viewRange()[1]
        return float(ymin), float(ymax)

    def apply_manual_x_limits(self, xmin: float, xmax: float) -> None:
        self.interaction_state.autoscale_x = False
        self.interaction_state.rolling_x = False
        self._sync_toolbar_state()
        self._set_x_range(min(xmin, xmax), max(xmin, xmax))
        self._update_adaptive_performance()

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        self.interaction_state.autoscale_y = False
        self._sync_toolbar_state()
        self._set_y_range(min(ymin, ymax), max(ymin, ymax))

    def _show_axis_range_editor(self, orientation: str, scene_pos: QPointF) -> None:
        if self._axis_range_popup is not None:
            self._axis_range_popup.close()
            self._axis_range_popup = None

        if orientation == "bottom":
            axis_label = "X"
            minimum, maximum = self.get_x_range()
            on_apply = self.apply_manual_x_limits
        elif orientation == "left":
            axis_label = "Y"
            minimum, maximum = self.get_y_range()
            on_apply = self.apply_manual_y_limits
        else:
            return

        popup = _AxisRangePopup(axis_label, minimum, maximum, on_apply, self.plot_widget)
        self._axis_range_popup = popup
        popup.destroyed.connect(
            lambda _obj=None, closed_popup=popup: self._clear_axis_range_popup(closed_popup)
        )
        popup.adjustSize()
        popup_position = (
            self.plot_widget.mapToGlobal(self.plot_widget.mapFromScene(scene_pos))
            + _RANGE_EDITOR_OFFSET
        )
        popup.move(popup_position)
        popup.show()
        popup.focus_first_field()

    def _clear_axis_range_popup(self, popup: _AxisRangePopup) -> None:
        if self._axis_range_popup is popup:
            self._axis_range_popup = None

    def set_theme(self, theme: str | PyQtLabGraphTheme | None) -> None:
        theme = resolve_theme(theme)
        self.theme = theme
        self.plot_widget.setBackground(QColor(0, 0, 0, 0))
        self.plot_widget.setStyleSheet(plot_widget_chrome_style())
        self.view_box.setBackgroundColor(theme.plot_background)
        self._extend_view_box_background()
        self._style_rect_zoom_selection()
        self.grid_item.setPen(pg.mkPen(theme.grid, width=_GRID_LINE_WIDTH))
        for curve_key in self.curve_order:
            curve = self.curves[curve_key]
            self._apply_curve_style(curve)
        self._style_legend()
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )
        self._apply_host_axis_style()
        if self.toolbar is not None:
            self.toolbar.refresh_icons()

    def apply_axis_scaling(self) -> None:
        if self.interaction_state.autoscale_x:
            self._apply_x_autoscale()
        elif self.interaction_state.rolling_x:
            self._apply_x_rolling_window()
        if self.interaction_state.autoscale_y:
            self._apply_y_autoscale()
        self._update_adaptive_performance()

    def show_customize_dialog(self, curve_key: str | None = None) -> None:
        show_customize_dialog(self, curve_key)

    def save_figure(self) -> None:
        filename, _filter = QFileDialog.getSaveFileName(
            self.plot_container,
            "Save plot",
            str(Path.cwd() / "plot.png"),
            "PNG Images (*.png);;All Files (*)",
        )
        if not filename:
            return
        try:
            import pyqtgraph.exporters as exporters

            exporter = exporters.ImageExporter(self.plot_item)
            exporter.export(filename)
        except Exception as exc:
            raise RuntimeError(f"Could not save PyQtGraph plot to {filename}: {exc}") from exc

    def set_plot_style(
        self,
        plot_style: str | PyQtLabGraphPlotStyle | None,
        *,
        apply_to_existing: bool = False,
    ) -> None:
        self.plot_style = resolve_plot_style(plot_style)
        if apply_to_existing:
            self.apply_plot_style()

    def apply_plot_style(self, plot_style: str | PyQtLabGraphPlotStyle | None = None) -> None:
        if plot_style is not None:
            self.plot_style = resolve_plot_style(plot_style)

        for index, curve_key in enumerate(self.curve_order):
            curve = self.curves[curve_key]
            curve.style = self._plot_style_curve_style(index)
            self._apply_curve_style(curve)
        self._refresh_legend()

    def load_layout(self, path: str | Path | None = None) -> bool:
        layout = load_plot_layout(self._resolve_layout_path(path), self.plot_identifier)
        if layout is None:
            return False
        PlotLayoutState.from_layout(layout, self).apply_to_widget(self)
        return True

    def save_layout(
        self,
        path: str | Path | None = None,
        *,
        include_x_range: bool = True,
        include_y_range: bool = True,
        restore_view_state_on_load: bool = True,
    ) -> None:
        save_plot_layout(
            self._resolve_layout_path(path),
            self.plot_identifier,
            PlotLayoutState.from_widget(
                self,
                include_x_range=include_x_range,
                include_y_range=include_y_range,
                restore_view_state_on_load=restore_view_state_on_load,
            ).to_layout(),
        )

    def _setup_plot(self) -> None:
        self.plot_widget.setFrameShape(QFrame.Shape.NoFrame)
        self.plot_item.layout.setContentsMargins(*_PLOT_LAYOUT_MARGINS)
        self.plot_widget.setAntialiasing(self.antialiasing_enabled)
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )
        self.grid_item = pg.GridItem(
            pen=pg.mkPen(self.theme.grid, width=_GRID_LINE_WIDTH),
            textPen=None,
        )
        self.grid_item.setZValue(_GRID_Z_VALUE)
        self.plot_item.addItem(self.grid_item, ignoreBounds=True)
        self.plot_item.showGrid(x=False, y=False)
        self.plot_item.setMenuEnabled(False)
        self.plot_item.hideButtons()
        self.plot_item.showAxis("top", show=True)
        self.plot_item.showAxis("right", show=True)

        for axis_name in ("bottom", "left"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setStyle(
                tickLength=_PRIMARY_AXIS_TICK_LENGTH,
                tickTextOffset=_PRIMARY_AXIS_TICK_TEXT_OFFSET,
                tickAlpha=_PRIMARY_AXIS_TICK_ALPHA,
                maxTickLevel=_PRIMARY_AXIS_MAX_TICK_LEVEL,
            )
        self.plot_item.getAxis("bottom").setHeight(_BOTTOM_AXIS_HEIGHT)
        self.plot_item.getAxis("left").setWidth(_LEFT_AXIS_WIDTH)
        for axis_name in ("top", "right"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setStyle(showValues=False, tickLength=_SECONDARY_AXIS_TICK_LENGTH)
        self._apply_host_axis_style()

    def _resolve_layout_path(self, path: str | Path | None) -> Path:
        if path is not None:
            return Path(path)
        if self.layout_path is not None:
            return self.layout_path
        raise RuntimeError(
            "No PyQtLabGraph layout path was provided. Pass layout_path to "
            "PyQtLabGraphWidget or call save_layout/load_layout with a path."
        )

    def _style_rect_zoom_selection(self) -> None:
        selection_color = pg.mkColor(ZOOM_SELECTION_COLOR)
        selection_color.setAlpha(ZOOM_SELECTION_FILL_ALPHA)
        border_color = pg.mkColor(ZOOM_SELECTION_COLOR)
        border_color.setAlpha(ZOOM_SELECTION_BORDER_ALPHA)
        self.view_box.rbScaleBox.setPen(
            pg.mkPen(border_color, width=_ZOOM_SELECTION_BORDER_WIDTH)
        )
        self.view_box.rbScaleBox.setBrush(pg.mkBrush(selection_color))

    def _extend_view_box_background(self, *_args: object) -> None:
        self.view_box.background.setRect(
            self.view_box.rect().adjusted(
                0.0,
                0.0,
                _VIEW_BOX_BACKGROUND_OVERDRAW,
                _VIEW_BOX_BACKGROUND_OVERDRAW,
            )
        )

    def _apply_interaction_behavior(self) -> None:
        active_tool = self.interaction_state.active_tool
        self.x_span_filter.set_enabled(active_tool == InteractionTool.X_ZOOM)
        self.y_span_filter.set_enabled(active_tool == InteractionTool.Y_ZOOM)
        if active_tool == InteractionTool.RECT_ZOOM:
            self.view_box.setMouseMode(pg.ViewBox.RectMode)
            self._style_rect_zoom_selection()
        else:
            self.view_box.setMouseMode(pg.ViewBox.PanMode)

    def _apply_x_span_zoom(self, xmin: float, xmax: float) -> None:
        if xmin != xmax:
            self.apply_manual_x_limits(xmin, xmax)

    def _apply_y_span_zoom(self, ymin: float, ymax: float) -> None:
        if ymin != ymax:
            self.apply_manual_y_limits(ymin, ymax)

    def _refresh_legend(self) -> None:
        if self.legend is not None:
            self.legend.refresh()

    def _style_legend(self) -> None:
        if self.legend is not None:
            self.legend.refresh_palette()

    def _update_legend_curve(self, key: str) -> None:
        if self.legend is not None:
            self.legend.update_curve(key)

    def _curve(self, key: str) -> CurveState:
        try:
            return self.curves[key]
        except KeyError as exc:
            raise KeyError(f'Curve "{key}" does not exist.') from exc

    def _curve_data(self, curve: CurveState) -> tuple[np.ndarray, np.ndarray]:
        x_values, y_values = curve.item.getOriginalDataset()
        if x_values is None or y_values is None:
            return np.array([]), np.array([])
        return x_values, y_values

    def _default_curve_style(self, index: int, color: str | None = None) -> CurveStyle:
        curve_style = self._plot_style_curve_style(index)
        if color is not None:
            curve_style = curve_style.with_overrides(line_color=color)
        return curve_style

    def _plot_style_curve_style(self, index: int) -> CurveStyle:
        return self.plot_style.curve_style(index)

    def _plot_style_curve_color(self, index: int) -> str:
        return self._plot_style_curve_style(index).line_color

    def _apply_curve_rendering_options(self, curve: CurveState) -> None:
        antialias = self._effective_antialiasing_enabled()
        curve.item.setClipToView(self.clip_to_view_enabled)
        curve.item.setDownsampling(auto=self.downsampling_enabled, method="peak")
        curve.item.opts["antialias"] = antialias
        curve.item.opts["useCache"] = self._marker_cache_enabled()
        curve.item.updateItems(styleUpdate=True)

    def _apply_curve_style(self, curve: CurveState) -> None:
        style = curve.style
        color = style.line_color
        line_width = style.line_width
        marker_size = style.marker_size
        marker_outline_width = style.marker_outline_width
        marker_symbol = style.marker_symbol
        line_enabled = style.line_enabled
        marker_enabled = style.marker_enabled and not self.adaptive_performance_active
        marker_filled = style.marker_filled
        marker_pen_width = 0.0 if marker_filled else marker_outline_width

        curve.item.setPen(pg.mkPen(color, width=line_width) if line_enabled else None)
        curve.item.setSymbol(marker_symbol if marker_enabled else None)
        curve.item.setSymbolSize(marker_size if marker_enabled else 0)
        curve.item.setSymbolBrush(
            pg.mkBrush(color) if marker_enabled and marker_filled else pg.mkBrush(None)
        )
        curve.item.setSymbolPen(
            pg.mkPen(color, width=marker_pen_width) if marker_enabled else None
        )
        curve.item.scatter.setPen(
            pg.mkPen(color, width=marker_pen_width) if marker_enabled else None
        )
        curve.item.scatter.setBrush(
            pg.mkBrush(color) if marker_enabled and marker_filled else pg.mkBrush(None)
        )
        self._update_legend_curve(curve.key)

    def _effective_antialiasing_enabled(self) -> bool:
        return self.antialiasing_enabled and not self.adaptive_performance_active

    def _marker_cache_enabled(self) -> bool:
        # PyQtGraph's pixel-mode marker cache is always rendered antialiased.
        # Disable the cache when antialiasing is off so marker drawing follows
        # the same setting as lines.
        return self._effective_antialiasing_enabled()

    def _update_adaptive_performance(self, *, force: bool = False) -> None:
        """Toggle expensive visual details when a dense view is visible."""
        active = self.adaptive_performance_active
        if not self.adaptive_performance_enabled:
            active = False
        else:
            visible_points = self._visible_data_point_count()
            if active:
                active = visible_points >= self.adaptive_performance_restore_threshold
            else:
                active = visible_points >= self.adaptive_performance_threshold

        if not force and active == self.adaptive_performance_active:
            return

        self.adaptive_performance_active = active
        self.plot_widget.setAntialiasing(self._effective_antialiasing_enabled())
        for curve in self.curves.values():
            self._apply_curve_rendering_options(curve)
            self._apply_curve_style(curve)

    def _visible_data_point_count(self) -> int:
        xmin, xmax = self.get_x_range()
        count = 0
        for curve in self.curves.values():
            if not curve.visible:
                continue
            x_values, _y_values = self._curve_data(curve)
            count += int(np.count_nonzero((xmin <= x_values) & (x_values <= xmax)))
        return count

    def _apply_x_autoscale(self) -> None:
        x_arrays = [
            self._curve_data(curve)[0]
            for curve in self.curves.values()
            if curve.visible
        ]
        x_arrays = [values for values in x_arrays if len(values) > 0]
        if not x_arrays:
            return
        x_values = np.concatenate(x_arrays)
        xmin = float(np.min(x_values))
        xmax = float(np.max(x_values))
        if xmin == xmax:
            xmin -= _X_AUTOSCALE_EQUAL_VALUE_MARGIN
            xmax += _X_AUTOSCALE_EQUAL_VALUE_MARGIN
        self._set_x_range(xmin, xmax)

    def _apply_x_rolling_window(self) -> None:
        x_arrays = [
            self._curve_data(curve)[0]
            for curve in self.curves.values()
            if curve.visible
        ]
        x_arrays = [values for values in x_arrays if len(values) > 0]
        if not x_arrays:
            return
        latest_x = float(np.max(np.concatenate(x_arrays)))
        right = latest_x
        left = right - self.rolling_window_size
        self._set_x_range(left, right)

    def _apply_y_autoscale(self) -> None:
        visible_values = self._visible_y_values()
        if not visible_values:
            visible_values = [
                y
                for curve in self.curves.values()
                if curve.visible
                for y in self._curve_data(curve)[1]
            ]
        if not visible_values:
            return
        minimum = min(visible_values)
        maximum = max(visible_values)
        margin = (
            _Y_AUTOSCALE_EQUAL_VALUE_MARGIN
            if minimum == maximum
            else (maximum - minimum) * _Y_AUTOSCALE_MARGIN_RATIO
        )
        self._set_y_range(minimum - margin, maximum + margin)

    def _visible_y_values(self) -> list[float]:
        xmin, xmax = self.get_x_range()
        values: list[float] = []
        for curve in self.curves.values():
            if not curve.visible:
                continue
            x_values, y_values = self._curve_data(curve)
            values.extend(y for x, y in zip(x_values, y_values) if xmin <= x <= xmax)
        return values

    def _set_x_range(self, xmin: float, xmax: float) -> None:
        self._set_range(
            lambda: self.plot_item.setXRange(xmin, xmax, padding=_RANGE_PADDING)
        )

    def _set_y_range(self, ymin: float, ymax: float) -> None:
        self._set_range(
            lambda: self.plot_item.setYRange(ymin, ymax, padding=_RANGE_PADDING)
        )

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
        x_mode: str | AxisMode | None = None,
        y_mode: str | AxisMode | None = None,
    ) -> None:
        self.x_label_text = x_label
        self.y_label_text = y_label
        self.x_label_units = x_units
        self.y_label_units = y_units
        if x_mode is not None:
            self.x_axis_mode = resolve_axis_mode(x_mode)
        if y_mode is not None:
            self.y_axis_mode = resolve_axis_mode(y_mode)

        self.bottom_axis.set_mode(self.x_axis_mode)
        self.bottom_axis.setLabel(
            x_label,
            units=x_units,
            **{"color": self._host_axis_color_name(), "margin-top": _AXIS_LABEL_TOP_MARGIN},
        )
        self.left_axis.set_mode(self.y_axis_mode)
        self.left_axis.setLabel(
            y_label,
            units=y_units,
            **{"color": self._host_axis_color_name(), "margin-right": _AXIS_LABEL_RIGHT_MARGIN},
        )

    def _apply_host_axis_style(self) -> None:
        axis_color = self._host_axis_color()
        axis_pen = pg.mkPen(axis_color, width=_AXIS_PEN_WIDTH)
        text_pen = pg.mkPen(axis_color)
        for axis_name in ("bottom", "left", "top", "right"):
            axis = self.plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setTickPen(axis_pen)
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )

    def _host_axis_color(self) -> QColor:
        return self.plot_widget.palette().color(QPalette.ColorRole.WindowText)

    def _host_axis_color_name(self) -> str:
        return self._host_axis_color().name(QColor.NameFormat.HexRgb)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        watched_widgets = {self.plot_widget}
        if self.plot_frame is not None:
            watched_widgets.add(self.plot_frame)
        if watched in watched_widgets and event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self._apply_host_axis_style()
        return super().eventFilter(watched, event)

    def _handle_view_range_changed(self, *_args: object) -> None:
        if self.applying_axis_scaling:
            return
        self.request_manual_navigation()
        self._update_adaptive_performance()

    def _sync_toolbar_state(self) -> None:
        if self.toolbar is not None:
            self.toolbar.sync_state(self.interaction_state)

    def _embed_component(
        self,
        container: QWidget,
        component: QWidget,
        frame_factory: Callable[[QWidget], QFrame],
    ) -> QFrame | None:
        if not self.show_component_frames:
            self._embed_widget(container, component)
            return None

        frame = frame_factory(component)
        self._embed_widget(container, frame)
        self._apply_host_frame_fallback_style(frame)
        return frame

    @staticmethod
    def _create_plot_frame(plot_widget: pg.PlotWidget) -> QFrame:
        frame = PyQtLabGraphWidget._create_raised_frame(
            "pyqtLabGraphPlotFrame",
            plot_widget,
            _PLOT_FRAME_MARGIN,
        )
        PyQtLabGraphWidget._apply_host_frame_fallback_style(frame)
        return frame

    @staticmethod
    def _create_toolbar_frame(toolbar: "PyQtLabGraphToolbar") -> QFrame:
        frame = PyQtLabGraphWidget._create_raised_frame(
            "pyqtLabGraphToolbarFrame",
            toolbar,
            _TOOLBAR_FRAME_MARGIN,
        )
        PyQtLabGraphWidget._apply_host_frame_fallback_style(frame)
        return frame

    @staticmethod
    def _create_legend_frame(legend: "PyQtLabGraphLegend") -> QFrame:
        frame = PyQtLabGraphWidget._create_raised_frame(
            "pyqtLabGraphLegendFrame",
            legend,
            _LEGEND_FRAME_MARGIN,
        )
        PyQtLabGraphWidget._apply_host_frame_fallback_style(frame)
        return frame

    @staticmethod
    def _create_raised_frame(object_name: str, child: QWidget, margin: int) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(margin, margin, margin, margin)
        layout.setSpacing(_FRAME_LAYOUT_SPACING)
        layout.addWidget(child)
        return frame

    @staticmethod
    def _apply_host_frame_fallback_style(frame: QFrame) -> None:
        app = QApplication.instance()
        if (app is not None and app.styleSheet()) or PyQtLabGraphWidget._has_parent_style_sheet(frame):
            frame.setStyleSheet("")
        else:
            frame.setStyleSheet(host_frame_fallback_style(frame.objectName()))

    @staticmethod
    def _has_parent_style_sheet(widget: QWidget) -> bool:
        parent = widget.parentWidget()
        while parent is not None:
            if parent.styleSheet():
                return True
            parent = parent.parentWidget()
        return False

    @staticmethod
    def _embed_widget(container: QWidget, widget: QWidget) -> None:
        layout = container.layout()
        if layout is None:
            layout = QVBoxLayout(container)
            container.setLayout(layout)
        layout.setContentsMargins(
            _EMBEDDED_CONTAINER_MARGIN,
            _EMBEDDED_CONTAINER_MARGIN,
            _EMBEDDED_CONTAINER_MARGIN,
            _EMBEDDED_CONTAINER_MARGIN,
        )
        layout.setSpacing(_FRAME_LAYOUT_SPACING)
        layout.addWidget(widget)
