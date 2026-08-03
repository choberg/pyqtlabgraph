from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from pathlib import Path
from typing import overload

import numpy as np
import pyqtgraph as pg
from numpy.typing import ArrayLike
from PySide6.QtCore import QPointF, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode, SmartAxisItem, resolve_axis_mode
from .axis_editors import _RANGE_EDITOR_OFFSET, _AxisRangePopup
from .constants import (
    _AXIS_LABEL_RIGHT_MARGIN,
    _AXIS_LABEL_TOP_MARGIN,
    _GRID_LINE_WIDTH,
)
from .cursor_controller import CursorController
from .curve_manager import CurveManager
from .dialogs import prepare_customize_dialog
from .dispatch import PlotChangeDispatcher
from .interaction import (
    _AxisSpanZoomFilter,
    _PyQtLabGraphPlotWidget,
    _PyQtLabGraphViewBox,
)
from .layouts import (
    apply_plot_layout,
    capture_plot_layout,
    load_plot_layout,
    save_plot_layout,
)
from .models import (
    CursorPairState,
    CursorState,
    CursorStyle,
    CursorType,
    InteractionState,
    InteractionTool,
)
from .range_controller import RangeController
from .render_optimizer import RenderOptimizer
from .runtime_state import PlotSnapshot
from .style_controller import StyleController
from .style_registry import PyQtLabGraphStyleRegistry
from .styles import CurveStyle, PyQtLabGraphPlotStyle
from .themes import (
    PyQtLabGraphTheme,
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
_PLOT_FRAME_MARGIN = 8
_FRAME_LAYOUT_SPACING = 0

class PyQtLabGraphWidget(QWidget):
    """Independent embeddable PyQtGraph plot component."""

    curve_added = Signal(str)
    curve_removed = Signal(str)
    curve_changed = Signal(str)
    curve_data_changed = Signal(str)
    interaction_state_changed = Signal(object)
    presentation_changed = Signal()
    state_reset = Signal()
    cursor_added = Signal(str)
    cursor_removed = Signal(str)
    cursor_moved = Signal(str, float)
    cursor_changed = Signal(str)
    cursor_pair_added = Signal(str)
    cursor_pair_removed = Signal(str)
    cursor_pair_changed = Signal(str)
    cursor_order_changed = Signal()
    cursor_selection_changed = Signal()

    def __init__(
        self,
        *,
        plot_identifier: str,
        layout_path: str | Path | None = None,
        rolling_window_size: float = 300.0,
        theme: str | PyQtLabGraphTheme | None = None,
        plot_style: str | PyQtLabGraphPlotStyle | None = None,
        style_registry: PyQtLabGraphStyleRegistry | None = None,
        parent: QWidget | None = None,
        show_frame: bool = True,
    ) -> None:
        super().__init__(parent)
        if not plot_identifier.strip():
            raise ValueError("PyQtLabGraph plot_identifier must not be empty.")
        self.plot_identifier = plot_identifier
        self.layout_path = Path(layout_path) if layout_path is not None else None
        self.rolling_window_size = rolling_window_size
        self._style_registry = (
            style_registry
            if style_registry is not None
            else PyQtLabGraphStyleRegistry()
        )
        self._change_dispatcher = PlotChangeDispatcher(
            emit_curve_added=self.curve_added.emit,
            emit_curve_removed=self.curve_removed.emit,
            emit_curve_changed=self.curve_changed.emit,
            emit_curve_data_changed=self.curve_data_changed.emit,
            emit_interaction_state_changed=self.interaction_state_changed.emit,
            emit_presentation_changed=self.presentation_changed.emit,
            emit_state_reset=self.state_reset.emit,
        )
        self.setObjectName("pyqtLabGraphWidget")

        # Use SmartAxisItem for bottom and left axes
        self.bottom_axis = SmartAxisItem(orientation="bottom")
        self.left_axis = SmartAxisItem(orientation="left")
        self.bottom_axis.double_clicked.connect(self._show_axis_range_editor)
        self.left_axis.double_clicked.connect(self._show_axis_range_editor)

        self._plot_widget = _PyQtLabGraphPlotWidget(
            axisItems={"bottom": self.bottom_axis, "left": self.left_axis},
            viewBox=_PyQtLabGraphViewBox(),
        )
        self._plot_widget.setObjectName("pyqtLabGraphPlotWidget")
        self._plot_item = self._plot_widget.getPlotItem()
        self._view_box = self._plot_item.getViewBox()
        self.x_span_filter = _AxisSpanZoomFilter(
            self._plot_widget,
            "x",
            self._apply_x_span_zoom,
            self,
        )
        self.y_span_filter = _AxisSpanZoomFilter(
            self._plot_widget,
            "y",
            self._apply_y_span_zoom,
            self,
        )
        self._axis_range_popup: _AxisRangePopup | None = None
        self._customize_dialog: QDialog | None = None

        self._interaction_state = InteractionState()
        self.applying_axis_scaling = False
        self.x_label_text = "X"
        self.y_label_text = "Y"
        self.x_label_units: str | None = None
        self.y_label_units: str | None = None
        self.x_axis_mode = AxisMode.AUTO
        self.y_axis_mode = AxisMode.AUTO
        self._x_log = False
        self._y_log = False

        self._curve_manager = CurveManager(self._plot_item)
        self._range_controller = RangeController(
            view_box=self._view_box,
            curves_provider=self._curve_manager.ordered_curves,
            curve_data_provider=self._curve_manager.get_curve_data,
            interaction_state_provider=lambda: self._interaction_state,
            x_log_provider=lambda: self._x_log,
            y_log_provider=lambda: self._y_log,
            rolling_window_size_provider=lambda: self.rolling_window_size,
        )
        self._render_optimizer = RenderOptimizer(
            plot_widget=self._plot_widget,
            curves_provider=self._curve_manager.ordered_curves,
            curve_data_provider=self._curve_manager.get_curve_data,
            x_range_provider=self._range_controller.get_x_range,
            x_log_provider=lambda: self._x_log,
        )
        initial_theme = self._style_registry.resolve_theme(None)
        self.grid_item = pg.GridItem(
            pen=pg.mkPen(initial_theme.grid, width=_GRID_LINE_WIDTH),
            textPen=None,
        )
        self._style_controller = StyleController(
            plot_widget=self._plot_widget,
            plot_item=self._plot_item,
            view_box=self._view_box,
            grid_item=self.grid_item,
            registry=self._style_registry,
            curves_provider=self._curve_manager.ordered_curves,
            adaptive_mode_provider=lambda: self._render_optimizer.active,
        )
        self._view_box.sigResized.connect(
            self._style_controller.extend_view_box_background
        )

        self._cursor_controller = CursorController(
            parent=self,
            plot_item=self._plot_item,
            view_box=self._view_box,
            curve_data_provider=self.curve_data,
            curve_visible_provider=self._curve_manager.curve_visible,
            curve_choices_provider=self._curve_manager.curve_choices,
            x_range_provider=self._range_controller.get_x_range,
            y_range_provider=self._range_controller.get_y_range,
            axis_mode_provider=lambda cursor_type: (
                self.x_axis_mode if cursor_type is CursorType.X else self.y_axis_mode
            ),
            axis_format_provider=lambda cursor_type: self._cursor_axis_format(cursor_type),
            x_log_provider=lambda: self._x_log,
            y_log_provider=lambda: self._y_log,
            plot_background_provider=lambda: self.theme.plot_background,
        )
        self._cursor_controller.cursor_added.connect(self.cursor_added.emit)
        self._cursor_controller.cursor_removed.connect(self.cursor_removed.emit)
        self._cursor_controller.cursor_moved.connect(self.cursor_moved.emit)
        self._cursor_controller.cursor_changed.connect(self.cursor_changed.emit)
        self._cursor_controller.cursor_pair_added.connect(self.cursor_pair_added.emit)
        self._cursor_controller.cursor_pair_removed.connect(self.cursor_pair_removed.emit)
        self._cursor_controller.cursor_pair_changed.connect(self.cursor_pair_changed.emit)
        self._cursor_controller.cursor_order_changed.connect(self.cursor_order_changed.emit)
        self._cursor_controller.selection_changed.connect(self.cursor_selection_changed.emit)
        self._change_dispatcher.set_batch_participant(
            self._cursor_controller.batch_changes,
            discard_changes=self._cursor_controller.discard_batched_changes,
            suppress_events=self._cursor_controller.suppress_batched_events,
        )
        self._setup_plot()
        component: QWidget = self._plot_widget
        if show_frame:
            component = self._create_plot_frame(self._plot_widget)
            self._style_controller.watch_palette_widget(component)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(component)

        self._view_box.sigRangeChanged.connect(self._handle_view_range_changed)
        self._style_controller.set_theme(theme)
        self._style_controller.set_plot_style(plot_style)
        self._range_controller._set_x_range(*_DEFAULT_X_RANGE)
        self._range_controller._set_y_range(*_DEFAULT_Y_RANGE)
        self._cursor_controller.refresh_presentation()

    def _publish_curve_changed(self, key: str) -> None:
        self._change_dispatcher.curve_changed(key)

    def _publish_presentation_changed(self) -> None:
        self._change_dispatcher.presentation_changed()

    def _reapply_curve_styles(self) -> None:
        for curve in self._curve_manager.ordered_curves():
            self._style_controller.apply_curve_style(curve)

    def _finish_range_and_presentation_update(self) -> None:
        self._range_controller.apply_axis_scaling()
        if self._render_optimizer.update_adaptive_performance():
            self._reapply_curve_styles()
        self._cursor_controller.refresh_presentation()

    def _finish_curve_data_update(self, key: str, *, notify: bool) -> None:
        self._cursor_controller.refresh_for_curve(key)
        self._finish_range_and_presentation_update()
        if notify:
            self._change_dispatcher.curve_data_changed(key)

    def add_curve(
        self,
        key: str,
        *,
        label: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem:
        curve_style = style or self._style_controller.default_curve_style(
            len(self._curve_manager.curve_order)
        )
        with self._change_dispatcher.batch():
            item = self._curve_manager.add_curve(
                key,
                label=label,
                style=curve_style,
            )
            try:
                curve = self._curve_manager.get_curve(key)
                self._render_optimizer.apply_curve_rendering_options(curve)
                self._style_controller.apply_curve_style(curve)
            except Exception:
                self._curve_manager._discard_curve(key)
                raise
            self._change_dispatcher.curve_added(key)
            return item

    def add_point(self, key: str, x_value: float, y_value: float) -> None:
        with self._change_dispatcher.batch():
            self._curve_manager.add_point(key, x_value, y_value)
            self._finish_curve_data_update(key, notify=True)

    @overload
    def set_data(self, key: str, x: ArrayLike) -> None: ...

    @overload
    def set_data(self, key: str, x: ArrayLike, y: ArrayLike) -> None: ...

    def set_data(
        self,
        key: str,
        x: ArrayLike,
        y: ArrayLike | None = None,
    ) -> None:
        with self._change_dispatcher.batch():
            self._curve_manager.set_data(key, x, y)
            self._finish_curve_data_update(key, notify=True)

    @overload
    def plot(
        self,
        key: str,
        x: ArrayLike,
        *,
        label: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem: ...

    @overload
    def plot(
        self,
        key: str,
        x: ArrayLike,
        y: ArrayLike,
        *,
        label: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem: ...

    def plot(
        self,
        key: str,
        x: ArrayLike,
        y: ArrayLike | None = None,
        *,
        label: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem:
        curve_style = style or self._style_controller.default_curve_style(
            len(self._curve_manager.curve_order)
        )
        with self._change_dispatcher.batch():
            item = self._curve_manager.plot(
                key,
                x,
                y,
                label=label,
                style=curve_style,
            )
            try:
                curve = self._curve_manager.get_curve(key)
                self._render_optimizer.apply_curve_rendering_options(curve)
                self._style_controller.apply_curve_style(curve)
                self._finish_curve_data_update(key, notify=False)
            except Exception:
                self._curve_manager._discard_curve(key)
                raise
            self._change_dispatcher.curve_added(key)
            return item

    def curve_data(self, key: str) -> tuple[np.ndarray, np.ndarray]:
        return self._curve_manager.curve_data(key)

    @property
    def native_plot_widget(self) -> pg.PlotWidget:
        return self._plot_widget

    @property
    def native_plot_item(self) -> pg.PlotItem:
        return self._plot_item

    @property
    def native_view_box(self) -> pg.ViewBox:
        return self._view_box

    def curve_item(self, key: str) -> pg.PlotDataItem:
        return self._curve_manager.curve_item(key)

    def clear_curve(self, key: str) -> None:
        with self._change_dispatcher.batch():
            self._curve_manager.clear_curve(key)
            self._finish_curve_data_update(key, notify=True)

    def remove_curve(self, key: str) -> None:
        with self._change_dispatcher.batch():
            self._curve_manager.remove_curve(key)
            self._cursor_controller.refresh_for_curve(key)
            self._finish_range_and_presentation_update()
            self._change_dispatcher.curve_removed(key)

    def set_curve_style(self, key: str, style: CurveStyle) -> None:
        if self._curve_manager.set_curve_style(key, style):
            self._style_controller.apply_curve_style(
                self._curve_manager.get_curve(key)
            )
            self._publish_curve_changed(key)

    def curve_style(self, key: str) -> CurveStyle:
        return self._curve_manager.curve_style(key)

    def curve_choices(self) -> tuple[tuple[str, str], ...]:
        return self._curve_manager.curve_choices()

    def curve_visible(self, key: str) -> bool:
        return self._curve_manager.curve_visible(key)

    def set_curve_visible(self, key: str, visible: bool) -> None:
        if not self._curve_manager.set_curve_visible(key, visible):
            return
        with self._change_dispatcher.batch():
            self._cursor_controller.handle_curve_visibility_changed(key)
            self._finish_range_and_presentation_update()
            self._publish_curve_changed(key)

    def add_cursor(
        self,
        cursor_type: CursorType | str,
        *,
        key: str | None = None,
        name: str | None = None,
        value: float | None = None,
        style: CursorStyle | None = None,
        snap_target_curve_key: str | None = None,
        follow_target_visibility: bool = False,
        label_visible: bool = False,
    ) -> str:
        return self._cursor_controller.add_cursor(
            cursor_type,
            key=key,
            name=name,
            value=value,
            style=style,
            snap_target_curve_key=snap_target_curve_key,
            follow_target_visibility=follow_target_visibility,
            label_visible=label_visible,
        )

    def remove_cursor(self, cursor_key: str) -> None:
        self._cursor_controller.remove_cursor(cursor_key)

    def set_cursor_value(self, cursor_key: str, value: float) -> None:
        self._cursor_controller.set_cursor_value(cursor_key, value)

    def set_cursor_name(self, cursor_key: str, name: str) -> None:
        self._cursor_controller.set_cursor_name(cursor_key, name)

    def set_cursor_style(self, cursor_key: str, style: CursorStyle) -> None:
        self._cursor_controller.set_cursor_style(cursor_key, style)

    def set_cursor_snap_target(
        self,
        cursor_key: str,
        target_curve_key: str | None,
    ) -> None:
        self._cursor_controller.set_cursor_snap_target(cursor_key, target_curve_key)

    def set_cursor_label_visible(self, cursor_key: str, visible: bool) -> None:
        self._cursor_controller.set_cursor_label_visible(cursor_key, visible)

    def set_cursor_visible(self, cursor_key: str, visible: bool) -> None:
        self._cursor_controller.set_cursor_visible(cursor_key, visible)

    def set_cursor_follow_target_visibility(self, cursor_key: str, enabled: bool) -> None:
        self._cursor_controller.set_cursor_follow_target_visibility(cursor_key, enabled)

    def cursor_state(self, cursor_key: str) -> CursorState:
        return self._cursor_controller.cursor_state(cursor_key)

    def cursor_states(self) -> tuple[CursorState, ...]:
        return self._cursor_controller.cursor_states()

    def set_cursor_order(self, cursor_keys: Sequence[str]) -> None:
        self._cursor_controller.set_cursor_order(cursor_keys)

    def selected_cursor_keys(self) -> list[str]:
        return self._cursor_controller.selected_cursor_keys()

    def set_selected_cursor_keys(self, cursor_keys: Sequence[str]) -> None:
        self._cursor_controller.set_selected_cursor_keys(cursor_keys)

    def cursor_target_value(self, cursor_key: str) -> float | None:
        return self._cursor_controller.cursor_target_value(cursor_key)

    def cursor_effective_visible(self, cursor_key: str) -> bool:
        return self._cursor_controller.cursor_effective_visible(cursor_key)

    def add_cursor_pair(
        self,
        first_cursor_key: str,
        second_cursor_key: str,
        *,
        key: str | None = None,
        measurement_visible: bool = True,
        annotation_position: float = 0.08,
    ) -> str:
        return self._cursor_controller.add_cursor_pair(
            first_cursor_key,
            second_cursor_key,
            key=key,
            measurement_visible=measurement_visible,
            annotation_position=annotation_position,
        )

    def remove_cursor_pair(self, pair_key: str) -> None:
        self._cursor_controller.remove_cursor_pair(pair_key)

    def set_cursor_pair_measurement_visible(self, pair_key: str, visible: bool) -> None:
        self._cursor_controller.set_cursor_pair_measurement_visible(pair_key, visible)

    def set_cursor_pair_annotation_position(self, pair_key: str, position: float) -> None:
        self._cursor_controller.set_cursor_pair_annotation_position(pair_key, position)

    def cursor_pair_state(self, pair_key: str) -> CursorPairState:
        return self._cursor_controller.cursor_pair_state(pair_key)

    def cursor_pair_states(self) -> tuple[CursorPairState, ...]:
        return self._cursor_controller.cursor_pair_states()

    def cursor_pair_for_cursor(self, cursor_key: str) -> CursorPairState | None:
        return self._cursor_controller.cursor_pair_for_cursor(cursor_key)

    def cursor_pair_measurement_text(self, pair_key: str) -> str:
        return self._cursor_controller.cursor_pair_measurement_text(pair_key)

    def cursor_pair_measurement_parts(self, pair_key: str) -> tuple[str, str, str]:
        return self._cursor_controller.cursor_pair_measurement_parts(pair_key)

    def format_cursor_value(self, cursor_type: CursorType, value: float) -> str:
        return self._cursor_controller.format_cursor_value(cursor_type, value)

    def _cursor_axis_format(
        self,
        cursor_type: CursorType,
    ) -> tuple[float, str, str | None]:
        axis = self.bottom_axis if cursor_type is CursorType.X else self.left_axis
        units = self.x_label_units if cursor_type is CursorType.X else self.y_label_units
        return axis.autoSIPrefixScale, axis.labelUnitPrefix, units

    def nudge_cursor_group(
        self,
        cursor_key: str,
        *,
        selected_cursor_keys: list[str],
        direction: int,
        step_ratio: float,
    ) -> bool:
        return self._cursor_controller.nudge_cursor_group(
            cursor_key,
            selected_cursor_keys=selected_cursor_keys,
            direction=direction,
            step_ratio=step_ratio,
        )

    @property
    def x_log(self) -> bool:
        return self._x_log

    @property
    def y_log(self) -> bool:
        return self._y_log

    def set_x_log(self, enabled: bool) -> None:
        if self._x_log == enabled:
            return
        with self._change_dispatcher.batch():
            if enabled and self.x_axis_mode == AxisMode.TIME:
                self.x_axis_mode = AxisMode.LINEAR
                self.bottom_axis.set_mode(self.x_axis_mode)
                self.bottom_axis.setLabel(
                    self.x_label_text,
                    units=self.x_label_units,
                    **{"color": self._style_controller.host_axis_color_name(), "margin-top": _AXIS_LABEL_TOP_MARGIN},
                )
            self.applying_axis_scaling = True
            try:
                xmin, xmax = self.get_x_range()
                self._x_log = enabled
                self._plot_item.setLogMode(x=self._x_log, y=self._y_log)

                if not self._interaction_state.autoscale_x and not self._interaction_state.rolling_x:
                    if enabled:
                        if xmin <= 0:
                            xmin = 0.1
                        if xmax <= 0:
                            xmax = 10.0
                        xmin_new = np.log10(xmin)
                        xmax_new = np.log10(xmax)
                    else:
                        xmin = np.clip(xmin, -20.0, 20.0)
                        xmax = np.clip(xmax, -20.0, 20.0)
                        xmin_new = 10**xmin
                        xmax_new = 10**xmax
                    self._range_controller.set_x_range(xmin_new, xmax_new)
                else:
                    self._range_controller.apply_axis_scaling()
            finally:
                self.applying_axis_scaling = False
            if self._render_optimizer.update_adaptive_performance(force=True):
                self._reapply_curve_styles()
            self._cursor_controller.refresh_presentation()
            self._publish_presentation_changed()

    def set_y_log(self, enabled: bool) -> None:
        if self._y_log == enabled:
            return
        with self._change_dispatcher.batch():
            if enabled and self.y_axis_mode == AxisMode.TIME:
                self.y_axis_mode = AxisMode.LINEAR
                self.left_axis.set_mode(self.y_axis_mode)
                self.left_axis.setLabel(
                    self.y_label_text,
                    units=self.y_label_units,
                    **{"color": self._style_controller.host_axis_color_name(), "margin-right": _AXIS_LABEL_RIGHT_MARGIN},
                )
            self.applying_axis_scaling = True
            try:
                ymin, ymax = self.get_y_range()
                self._y_log = enabled
                self._plot_item.setLogMode(x=self._x_log, y=self._y_log)

                if not self._interaction_state.autoscale_y:
                    if enabled:
                        if ymin <= 0:
                            ymin = 0.1
                        if ymax <= 0:
                            ymax = 10.0
                        ymin_new = np.log10(ymin)
                        ymax_new = np.log10(ymax)
                    else:
                        ymin = np.clip(ymin, -20.0, 20.0)
                        ymax = np.clip(ymax, -20.0, 20.0)
                        ymin_new = 10**ymin
                        ymax_new = 10**ymax
                    self._range_controller.set_y_range(ymin_new, ymax_new)
                else:
                    self._range_controller.apply_axis_scaling()
            finally:
                self.applying_axis_scaling = False
            self._cursor_controller.refresh_presentation()
            self._publish_presentation_changed()

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

    @property
    def grid_visible(self) -> bool:
        return self.grid_item.isVisible()

    def set_antialiasing_enabled(self, enabled: bool) -> None:
        self._render_optimizer.set_antialiasing_enabled(enabled)

    @property
    def antialiasing_enabled(self) -> bool:
        return self._render_optimizer.antialiasing_enabled

    def set_downsampling_enabled(self, enabled: bool) -> None:
        self._render_optimizer.set_downsampling_enabled(enabled)

    @property
    def downsampling_enabled(self) -> bool:
        return self._render_optimizer.downsampling_enabled

    def set_clip_to_view_enabled(self, enabled: bool) -> None:
        self._render_optimizer.set_clip_to_view_enabled(enabled)

    @property
    def clip_to_view_enabled(self) -> bool:
        return self._render_optimizer.clip_to_view_enabled

    def set_adaptive_performance_enabled(self, enabled: bool) -> None:
        if self._render_optimizer.set_adaptive_performance_enabled(enabled):
            self._reapply_curve_styles()

    @property
    def adaptive_performance_enabled(self) -> bool:
        return self._render_optimizer.enabled

    @property
    def interaction_state(self) -> InteractionState:
        return self._interaction_state

    def _emit_interaction_state(self) -> None:
        self._change_dispatcher.interaction_state_changed(self.interaction_state)

    def _set_interaction_state(self, state: InteractionState) -> bool:
        validated = InteractionState(
            autoscale_x=state.autoscale_x,
            autoscale_y=state.autoscale_y,
            rolling_x=state.rolling_x,
            active_tool=state.active_tool,
        )
        if validated == self._interaction_state:
            return False
        self._interaction_state = validated
        self._apply_interaction_behavior()
        self._emit_interaction_state()
        return True

    def _replace_interaction_state(self, **changes: object) -> bool:
        updated = replace(
            self._interaction_state,
            **changes,  # type: ignore[arg-type]
        )
        return self._set_interaction_state(updated)

    def request_autoscale_x(self, enabled: bool) -> None:
        with self._change_dispatcher.batch():
            changes: dict[str, object] = {"autoscale_x": enabled}
            if enabled:
                changes["rolling_x"] = False
                changes["active_tool"] = InteractionTool.NONE
            self._replace_interaction_state(**changes)
            self._finish_range_and_presentation_update()

    def request_autoscale_y(self, enabled: bool) -> None:
        with self._change_dispatcher.batch():
            changes: dict[str, object] = {"autoscale_y": enabled}
            if enabled:
                changes["active_tool"] = InteractionTool.NONE
            self._replace_interaction_state(**changes)
            self._finish_range_and_presentation_update()

    def request_rolling_x(self, enabled: bool) -> None:
        with self._change_dispatcher.batch():
            changes: dict[str, object] = {"rolling_x": enabled}
            if enabled:
                changes["autoscale_x"] = False
                changes["active_tool"] = InteractionTool.NONE
            self._replace_interaction_state(**changes)
            self._finish_range_and_presentation_update()

    def request_tool(self, tool: InteractionTool, enabled: bool) -> None:
        changes: dict[str, object] = {
            "active_tool": tool if enabled else InteractionTool.NONE
        }
        if enabled and tool is not InteractionTool.NONE:
            changes.update(
                autoscale_x=False,
                autoscale_y=False,
                rolling_x=False,
            )
        self._replace_interaction_state(**changes)

    def request_show_all(self) -> None:
        with self._change_dispatcher.batch():
            self._set_interaction_state(InteractionState())
            self._finish_range_and_presentation_update()

    def apply_interaction_state(self, state: InteractionState) -> None:
        """Applies the interaction state to the widget and synchronizes UI."""
        self._set_interaction_state(state)

    def request_manual_navigation(self) -> None:
        self._replace_interaction_state(
            autoscale_x=False,
            autoscale_y=False,
            rolling_x=False,
        )

    def set_rolling_window_size(self, size: float) -> None:
        if size <= 0.0:
            raise ValueError("Rolling window size must be greater than 0.")
        self.rolling_window_size = size
        if self._interaction_state.rolling_x:
            self.apply_axis_scaling()

    def get_current_x_window_size(self) -> float:
        xmin, xmax = self.get_x_range()
        return max(abs(xmax - xmin), 1.0)

    def get_x_range(self) -> tuple[float, float]:
        xmin, xmax = self._view_box.viewRange()[0]
        return float(xmin), float(xmax)

    def get_y_range(self) -> tuple[float, float]:
        ymin, ymax = self._view_box.viewRange()[1]
        return float(ymin), float(ymax)

    def apply_manual_x_limits(self, xmin: float, xmax: float) -> None:
        with self._change_dispatcher.batch():
            self._replace_interaction_state(
                autoscale_x=False,
                rolling_x=False,
            )
            self._range_controller.apply_manual_x_limits(xmin, xmax)
            if self._render_optimizer.update_adaptive_performance():
                self._reapply_curve_styles()
            self._cursor_controller.refresh_presentation()

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        with self._change_dispatcher.batch():
            self._replace_interaction_state(autoscale_y=False)
            self._range_controller.apply_manual_y_limits(ymin, ymax)
            self._cursor_controller.refresh_presentation()

    def _show_axis_range_editor(self, orientation: str, scene_pos: QPointF) -> None:
        if self._axis_range_popup is not None:
            self._axis_range_popup.close()
            self._axis_range_popup = None

        on_apply: Callable[[float, float], None]
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

        popup = _AxisRangePopup(axis_label, minimum, maximum, on_apply, self._plot_widget)
        self._axis_range_popup = popup
        popup.destroyed.connect(
            lambda _obj=None, closed_popup=popup: self._clear_axis_range_popup(closed_popup)
        )
        popup.adjustSize()
        popup_position = (
            self._plot_widget.mapToGlobal(self._plot_widget.mapFromScene(scene_pos))
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
        return self._style_controller.theme

    @property
    def plot_style(self) -> PyQtLabGraphPlotStyle:
        return self._style_controller.plot_style

    @property
    def style_registry(self) -> PyQtLabGraphStyleRegistry:
        return self._style_registry

    def set_theme(self, theme: str | PyQtLabGraphTheme | None) -> None:
        with self._change_dispatcher.batch():
            self._style_controller.set_theme(theme)
            self._set_axis_labels(
                self.x_label_text,
                self.y_label_text,
                self.x_label_units,
                self.y_label_units,
            )
            self._apply_zoom_tool_cursor()
            self._cursor_controller.refresh_presentation()
            self._publish_presentation_changed()

    def apply_axis_scaling(self) -> None:
        with self._change_dispatcher.batch():
            self._finish_range_and_presentation_update()

    def show_customize_dialog(self, curve_key: str | None = None) -> None:
        current_dialog = self._customize_dialog
        dialog, created = prepare_customize_dialog(
            self,
            curve_key,
            existing_dialog=current_dialog,
        )
        if not created:
            return
        self._customize_dialog = dialog
        dialog.finished.connect(
            lambda _result, dialog=dialog: self._forget_customize_dialog(dialog)
        )
        dialog.show()

    def _forget_customize_dialog(self, dialog: QDialog) -> None:
        if self._customize_dialog is dialog:
            self._customize_dialog = None

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
            import pyqtgraph.exporters as exporters

            exporter = exporters.ImageExporter(self._plot_item)
            exporter.export(filename)
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Could not save PyQtGraph plot to {filename}: {exc}") from exc

    def set_plot_style(
        self,
        plot_style: str | PyQtLabGraphPlotStyle,
    ) -> None:
        with self._change_dispatcher.batch():
            style_changed, changed_keys = self._style_controller.set_plot_style(plot_style)
            for key in changed_keys:
                self._publish_curve_changed(key)
            if style_changed or changed_keys:
                self._publish_presentation_changed()

    def restore_snapshot(self, snapshot: PlotSnapshot) -> None:
        """Atomically restore an exact runtime snapshot."""
        if not isinstance(snapshot, PlotSnapshot):
            raise TypeError("snapshot must be a PlotSnapshot.")
        before = PlotSnapshot.capture(self)
        with self._change_dispatcher.state_replacement():
            try:
                self._apply_snapshot(snapshot)
            except BaseException:
                self._apply_snapshot(before)
                raise

    def _apply_snapshot(self, snapshot: PlotSnapshot) -> None:
        current_curve_keys = {
            key for key, _label in self.curve_choices()
        }
        snapshot_curve_keys = {state.key for state in snapshot.curves}
        if snapshot_curve_keys != current_curve_keys:
            raise ValueError(
                "PlotSnapshot curve keys must match the target widget."
            )

        self.set_x_log(snapshot.x_log)
        self.set_y_log(snapshot.y_log)
        self.set_axis_labels(
            snapshot.x_label,
            snapshot.y_label,
            x_units=snapshot.x_units,
            y_units=snapshot.y_units,
            x_mode=snapshot.x_mode,
            y_mode=snapshot.y_mode,
        )
        self.set_grid_visible(snapshot.grid_visible)
        self.set_antialiasing_enabled(snapshot.antialiasing)
        self.set_downsampling_enabled(snapshot.downsampling)
        self.set_clip_to_view_enabled(snapshot.clip_to_view)
        self.set_adaptive_performance_enabled(snapshot.adaptive_performance)
        self.set_theme(snapshot.theme)
        self.set_plot_style(snapshot.plot_style)
        for curve in snapshot.curves:
            self.set_curve_visible(curve.key, curve.visible)
            self.set_curve_style(curve.key, curve.style)

        for cursor in tuple(self.cursor_states()):
            self.remove_cursor(cursor.key)
        for cursor in snapshot.cursors:
            self.add_cursor(
                cursor.cursor_type,
                key=cursor.key,
                name=cursor.name,
                value=cursor.value,
                style=cursor.style,
                snap_target_curve_key=cursor.snap_target_curve_key,
                follow_target_visibility=cursor.follow_target_visibility,
                label_visible=cursor.label_visible,
            )
            if not cursor.visible:
                self.set_cursor_visible(cursor.key, False)
        for pair in snapshot.cursor_pairs:
            self.add_cursor_pair(
                pair.first_cursor_key,
                pair.second_cursor_key,
                key=pair.key,
                measurement_visible=pair.measurement_visible,
                annotation_position=pair.annotation_position,
            )
        self.set_cursor_order([state.key for state in snapshot.cursors])
        self.set_selected_cursor_keys(snapshot.selected_cursor_keys)

        self.apply_interaction_state(snapshot.interaction_state)
        self._range_controller.set_x_range(*snapshot.x_range)
        self._range_controller.set_y_range(*snapshot.y_range)
        if self._render_optimizer.update_adaptive_performance(force=True):
            self._reapply_curve_styles()
        self._cursor_controller.refresh_presentation()

    def load_layout(self, path: str | Path | None = None) -> bool:
        layout = load_plot_layout(self._resolve_layout_path(path), self.plot_identifier)
        if layout is None:
            return False
        apply_plot_layout(self, layout)
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
            capture_plot_layout(
                self,
                include_x_range=include_x_range,
                include_y_range=include_y_range,
                restore_view_state_on_load=restore_view_state_on_load,
            ),
        )

    def _setup_plot(self) -> None:
        self._plot_widget.setFrameShape(QFrame.Shape.NoFrame)
        self._plot_item.layout.setContentsMargins(*_PLOT_LAYOUT_MARGINS)
        self._plot_widget.setAntialiasing(self._render_optimizer.antialiasing_enabled)
        self._set_axis_labels(
            self.x_label_text,
            self.y_label_text,
            self.x_label_units,
            self.y_label_units,
        )
        self.grid_item.setZValue(_GRID_Z_VALUE)
        self._plot_item.addItem(self.grid_item, ignoreBounds=True)
        self._plot_item.showGrid(x=False, y=False)
        self._plot_item.setMenuEnabled(False)
        self._plot_item.hideButtons()
        self._plot_item.showAxis("top", show=True)
        self._plot_item.showAxis("right", show=True)

        for axis_name in ("bottom", "left"):
            axis = self._plot_item.getAxis(axis_name)
            axis.setStyle(
                tickLength=_PRIMARY_AXIS_TICK_LENGTH,
                tickTextOffset=_PRIMARY_AXIS_TICK_TEXT_OFFSET,
                tickAlpha=_PRIMARY_AXIS_TICK_ALPHA,
                maxTickLevel=_PRIMARY_AXIS_MAX_TICK_LEVEL,
            )
        self._plot_item.getAxis("bottom").setHeight(_BOTTOM_AXIS_HEIGHT)
        self._plot_item.getAxis("left").setWidth(_LEFT_AXIS_WIDTH)
        for axis_name in ("top", "right"):
            axis = self._plot_item.getAxis(axis_name)
            axis.setStyle(showValues=False, tickLength=_SECONDARY_AXIS_TICK_LENGTH)
        self._style_controller.apply_host_axis_style()

    def _resolve_layout_path(self, path: str | Path | None) -> Path:
        if path is not None:
            return Path(path)
        if self.layout_path is not None:
            return self.layout_path
        raise RuntimeError(
            "No PyQtLabGraph layout path was provided. Pass layout_path to "
            "PyQtLabGraphWidget or call save_layout/load_layout with a path."
        )

    def _apply_interaction_behavior(self) -> None:
        active_tool = self._interaction_state.active_tool
        self.x_span_filter.set_enabled(active_tool == InteractionTool.X_ZOOM)
        self.y_span_filter.set_enabled(active_tool == InteractionTool.Y_ZOOM)
        if active_tool == InteractionTool.RECT_ZOOM:
            self._view_box.setMouseMode(pg.ViewBox.RectMode)
            self._style_controller.style_rect_zoom_selection()
        else:
            self._view_box.setMouseMode(pg.ViewBox.PanMode)
        self._apply_zoom_tool_cursor()

    def _apply_zoom_tool_cursor(self) -> None:
        self._plot_widget.set_zoom_tool_cursor(
            self._interaction_state.active_tool,
            self.theme.plot_background,
        )

    def _apply_x_span_zoom(self, xmin: float, xmax: float) -> None:
        if xmin != xmax:
            self.apply_manual_x_limits(xmin, xmax)

    def _apply_y_span_zoom(self, ymin: float, ymax: float) -> None:
        if ymin != ymax:
            self.apply_manual_y_limits(ymin, ymax)

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
        if self.x_axis_mode == AxisMode.TIME and self._x_log:
            self.set_x_log(False)
        if self.y_axis_mode == AxisMode.TIME and self._y_log:
            self.set_y_log(False)

        self.bottom_axis.set_mode(self.x_axis_mode)
        self.bottom_axis.setLabel(
            x_label,
            units=x_units,
            **{"color": self._style_controller.host_axis_color_name(), "margin-top": _AXIS_LABEL_TOP_MARGIN},
        )
        self.left_axis.set_mode(self.y_axis_mode)
        self.left_axis.setLabel(
            y_label,
            units=y_units,
            **{"color": self._style_controller.host_axis_color_name(), "margin-right": _AXIS_LABEL_RIGHT_MARGIN},
        )
        self._cursor_controller.refresh_presentation()
        self._publish_presentation_changed()

    def _handle_view_range_changed(self, *_args: object) -> None:
        if self.applying_axis_scaling or self._range_controller.applying_range:
            return
        with self._change_dispatcher.batch():
            self.request_manual_navigation()
            if self._render_optimizer.update_adaptive_performance():
                self._reapply_curve_styles()
            self._cursor_controller.refresh_presentation()
            self._publish_presentation_changed()

    @staticmethod
    def _create_plot_frame(plot_widget: pg.PlotWidget) -> QFrame:
        frame = PyQtLabGraphWidget._create_raised_frame(
            "pyqtLabGraphPlotFrame",
            plot_widget,
            _PLOT_FRAME_MARGIN,
        )
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
