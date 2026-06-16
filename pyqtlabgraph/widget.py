from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode, SmartAxisItem, resolve_axis_mode
from .axis_editors import _AxisRangePopup, _RANGE_EDITOR_OFFSET
from .curve_manager import CurveManager
from .dialogs import show_customize_dialog
from .interaction import _AxisSpanZoomFilter, _PyQtLabGraphViewBox, _ZOOM_SELECTION_BORDER_WIDTH
from .range_controller import RangeController
from .render_optimizer import RenderOptimizer
from .style_controller import StyleController
from .legend import PyQtLabGraphLegend
from .layouts import PlotLayoutState, load_plot_layout, save_plot_layout
from .models import InteractionState, InteractionTool
from .styles import CurveStyle, PyQtLabGraphPlotStyle
from .qt_styles import host_frame_fallback_style, plot_widget_chrome_style
from .themes import (
    PyQtLabGraphTheme,
    ZOOM_SELECTION_BORDER_ALPHA,
    ZOOM_SELECTION_COLOR,
    ZOOM_SELECTION_FILL_ALPHA,
)
from .toolbar import PyQtLabGraphToolbar
from .constants import (
    _AXIS_LABEL_TOP_MARGIN,
    _AXIS_LABEL_RIGHT_MARGIN,
    _GRID_LINE_WIDTH,
)


_DEFAULT_X_RANGE = (0.0, 1.0)
_DEFAULT_Y_RANGE = (0.0, 1.0)

_PLOT_LAYOUT_MARGINS = (8, 8, 12, 8)
_PRIMARY_AXIS_TICK_LENGTH = 8
_PRIMARY_AXIS_TICK_TEXT_OFFSET = 8
_PRIMARY_AXIS_TICK_ALPHA = 1.0
_PRIMARY_AXIS_MAX_TICK_LEVEL = 1

_SECONDARY_AXIS_TICK_LENGTH = 0
_BOTTOM_AXIS_HEIGHT = 54
_LEFT_AXIS_WIDTH = 62

_GRID_Z_VALUE = -10
_VIEW_BOX_BACKGROUND_OVERDRAW = 1.0

_PLOT_FRAME_MARGIN = 8
_TOOLBAR_FRAME_MARGIN = 4
_LEGEND_FRAME_MARGIN = 2
_EMBEDDED_CONTAINER_MARGIN = 0
_FRAME_LAYOUT_SPACING = 0



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
        self._customize_dialogs: list[QDialog] = []

        self.curve_manager = CurveManager(self)
        self.range_controller = RangeController(self)
        self.render_optimizer = RenderOptimizer(self)
        self.style_controller = StyleController(self)

        self.interaction_state = InteractionState()
        self.applying_axis_scaling = False
        self.x_label_text = "X"
        self.y_label_text = "Y"
        self.x_label_units: str | None = None
        self.y_label_units: str | None = None
        self.x_axis_mode = AxisMode.AUTO
        self.y_axis_mode = AxisMode.AUTO
        self._x_log = False
        self._y_log = False

        self._setup_plot()

        self.plot_frame = self._embed_component(
            self.plot_container,
            self.plot_widget,
            self._create_plot_frame,
        )
        if self.plot_frame is not None:
            self.plot_frame.installEventFilter(self.style_controller)

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
        self.style_controller.set_theme(theme)
        self.style_controller.set_plot_style(plot_style)
        self.range_controller._set_x_range(*_DEFAULT_X_RANGE)
        self.range_controller._set_y_range(*_DEFAULT_Y_RANGE)

    def add_curve(
        self,
        key: str,
        *,
        label: str | None = None,
        color: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem:
        return self.curve_manager.add_curve(key, label=label, color=color, style=style)

    def add_point(self, key: str, x_value: float, y_value: float) -> None:
        self.curve_manager.add_point(key, x_value, y_value)

    def set_data(self, key: str, *args: Any, **kwargs: Any) -> None:
        self.curve_manager.set_data(key, *args, **kwargs)

    def plot(
        self,
        key: str,
        *args: Any,
        label: str | None = None,
        color: str | None = None,
        style: CurveStyle | None = None,
        **kwargs: Any,
    ) -> pg.PlotDataItem:
        return self.curve_manager.plot(key, *args, label=label, color=color, style=style, **kwargs)

    def curve_data(self, key: str) -> tuple[np.ndarray, np.ndarray]:
        return self.curve_manager.curve_data(key)

    @property
    def _pyqt_lab_graph_customize_dialogs(self) -> list[QDialog]:
        return self._customize_dialogs

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
        return self.curve_manager.curve_item(key)

    def clear_curve(self, key: str) -> None:
        self.curve_manager.clear_curve(key)

    def remove_curve(self, key: str) -> None:
        self.curve_manager.remove_curve(key)

    def set_curve_style(self, key: str, style: CurveStyle) -> None:
        self.curve_manager.set_curve_style(key, style)

    def curve_style(self, key: str) -> CurveStyle:
        return self.curve_manager.curve_style(key)

    def set_curve_visible(self, key: str, visible: bool) -> None:
        self.curve_manager.set_curve_visible(key, visible)

    @property
    def x_log(self) -> bool:
        return self._x_log

    @x_log.setter
    def x_log(self, enabled: bool) -> None:
        self.set_x_log(enabled)

    @property
    def y_log(self) -> bool:
        return self._y_log

    @y_log.setter
    def y_log(self, enabled: bool) -> None:
        self.set_y_log(enabled)

    def set_x_log(self, enabled: bool) -> None:
        self._x_log = enabled
        self.plot_item.setLogMode(x=self._x_log, y=self._y_log)
        self.apply_axis_scaling()

    def set_y_log(self, enabled: bool) -> None:
        self._y_log = enabled
        self.plot_item.setLogMode(x=self._x_log, y=self._y_log)
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
        self.render_optimizer.set_antialiasing_enabled(enabled)

    def set_downsampling_enabled(self, enabled: bool) -> None:
        self.render_optimizer.set_downsampling_enabled(enabled)

    def set_clip_to_view_enabled(self, enabled: bool) -> None:
        self.render_optimizer.set_clip_to_view_enabled(enabled)

    def set_adaptive_performance_enabled(self, enabled: bool) -> None:
        self.render_optimizer.set_adaptive_performance_enabled(enabled)

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

    def apply_interaction_state(self, state: InteractionState) -> None:
        """Applies the interaction state to the widget and synchronizes UI."""
        self.interaction_state = state
        self._apply_interaction_behavior()
        self._sync_toolbar_state()

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
        self.range_controller.apply_manual_x_limits(xmin, xmax)

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        self.range_controller.apply_manual_y_limits(ymin, ymax)

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

    @property
    def theme(self) -> PyQtLabGraphTheme:
        return self.style_controller.theme

    @property
    def plot_style(self) -> PyQtLabGraphPlotStyle:
        return self.style_controller.plot_style

    def set_theme(self, theme: str | PyQtLabGraphTheme | None) -> None:
        self.style_controller.set_theme(theme)

    def apply_axis_scaling(self) -> None:
        self.range_controller.apply_axis_scaling()

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
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Could not save PyQtGraph plot to {filename}: {exc}") from exc

    def set_plot_style(
        self,
        plot_style: str | PyQtLabGraphPlotStyle | None,
        *,
        apply_to_existing: bool = False,
    ) -> None:
        self.style_controller.set_plot_style(plot_style, apply_to_existing=apply_to_existing)

    def apply_plot_style(self, plot_style: str | PyQtLabGraphPlotStyle | None = None) -> None:
        self.style_controller.apply_plot_style(plot_style)

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
        self.plot_widget.setAntialiasing(self.render_optimizer.antialiasing_enabled)
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )
        self.grid_item = pg.GridItem(
            pen=pg.mkPen(self.style_controller.theme.grid, width=_GRID_LINE_WIDTH),
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
        self.style_controller.apply_host_axis_style()

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
            **{"color": self.style_controller.host_axis_color_name(), "margin-top": _AXIS_LABEL_TOP_MARGIN},
        )
        self.left_axis.set_mode(self.y_axis_mode)
        self.left_axis.setLabel(
            y_label,
            units=y_units,
            **{"color": self.style_controller.host_axis_color_name(), "margin-right": _AXIS_LABEL_RIGHT_MARGIN},
        )

    def _handle_view_range_changed(self, *_args: object) -> None:
        if self.applying_axis_scaling:
            return
        self.request_manual_navigation()
        self.render_optimizer.update_adaptive_performance()

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
