from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import overload

import numpy as np
import pyqtgraph as pg
from numpy.typing import ArrayLike
from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode, SmartAxisItem, resolve_axis_mode
from .axis_editors import _RANGE_EDITOR_OFFSET, _AxisRangePopup
from .colormaps import PyQtLabGraphColorGradient, PyQtLabGraphCurvePalette
from .constants import (
    _AXIS_LABEL_RIGHT_MARGIN,
    _AXIS_LABEL_TOP_MARGIN,
    _GRID_LINE_WIDTH,
)
from .cursors import PyQtLabGraphCursors
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
    CursorType,
    InteractionState,
    InteractionTool,
)
from .persistence import TracePersistenceConfig, TracePersistenceManager
from .range_controller import RangeController
from .render_optimizer import RenderOptimizer
from .runtime_state import PlotSnapshot
from .style_controller import StyleController
from .style_registry import PyQtLabGraphStyleRegistry
from .styles import CurveStyle
from .themes import (
    PyQtLabGraphTheme,
)

_DEFAULT_X_RANGE = (0.0, 1.0)
_DEFAULT_Y_RANGE = (0.0, 1.0)
_DEFAULT_CURVE_PALETTE_NAME = "default-light"

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
        curve_palette: str | PyQtLabGraphCurvePalette = _DEFAULT_CURVE_PALETTE_NAME,
        curve_palette_reverse: bool = False,
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
            style_registry if style_registry is not None else PyQtLabGraphStyleRegistry()
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
        self._trace_persistence = TracePersistenceManager(self._plot_item)
        self._curve_palette = self._style_registry.resolve_curve_palette(curve_palette)
        if not isinstance(curve_palette_reverse, bool):
            raise TypeError("curve_palette_reverse must be a bool.")
        self._curve_palette_reverse = curve_palette_reverse
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
        self._view_box.sigResized.connect(self._style_controller.extend_view_box_background)

        self._cursors = PyQtLabGraphCursors(
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
        self._cursors.cursor_added.connect(self.cursor_added.emit)
        self._cursors.cursor_removed.connect(self.cursor_removed.emit)
        self._cursors.cursor_moved.connect(self.cursor_moved.emit)
        self._cursors.cursor_changed.connect(self.cursor_changed.emit)
        self._cursors.cursor_pair_added.connect(self.cursor_pair_added.emit)
        self._cursors.cursor_pair_removed.connect(self.cursor_pair_removed.emit)
        self._cursors.cursor_pair_changed.connect(self.cursor_pair_changed.emit)
        self._cursors.cursor_order_changed.connect(self.cursor_order_changed.emit)
        self._cursors.selection_changed.connect(self.cursor_selection_changed.emit)
        self._change_dispatcher.set_batch_participant(
            self._cursors.batch_changes,
            discard_changes=self._cursors.discard_batched_changes,
            suppress_events=self._cursors.suppress_batched_events,
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
        self._range_controller._set_x_range(*_DEFAULT_X_RANGE)
        self._range_controller._set_y_range(*_DEFAULT_Y_RANGE)
        self._cursors.refresh_presentation()

    def _publish_curve_changed(self, key: str) -> None:
        self._change_dispatcher.curve_changed(key)

    def _publish_presentation_changed(self) -> None:
        self._change_dispatcher.presentation_changed()

    def _reapply_curve_styles(self) -> None:
        for curve in self._curve_manager.ordered_curves():
            self._style_controller.apply_curve_style(curve)
            self._trace_persistence.update_curve(curve.key, curve.style, curve.visible)
        self._apply_persistence_rendering()

    def _apply_persistence_rendering(self) -> None:
        self._trace_persistence.apply_rendering(
            clip_to_view=self.clip_to_view_enabled,
            downsampling=self.downsampling_enabled,
            antialias=self._render_optimizer.effective_antialiasing_enabled(),
        )

    def _finish_range_and_presentation_update(self) -> None:
        self._range_controller.apply_axis_scaling()
        if self._render_optimizer.update_adaptive_performance():
            self._reapply_curve_styles()
        self._cursors.refresh_presentation()

    def _finish_curve_data_update(self, key: str, *, notify: bool) -> None:
        self._cursors.refresh_for_curve(key)
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
        index = len(self._curve_manager.curve_order)
        curve_style = style or CurveStyle(line_color=self._curve_palette_color(index).name())
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
            previous_x, previous_y = self._curve_manager.curve_data(key)
            self._curve_manager.set_data(key, x, y)
            curve = self._curve_manager.get_curve(key)
            self._trace_persistence.capture(key, previous_x, previous_y, curve.style, curve.visible)
            self._apply_persistence_rendering()
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
        index = len(self._curve_manager.curve_order)
        curve_style = style or CurveStyle(line_color=self._curve_palette_color(index).name())
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
            self._trace_persistence.clear(key)
            self._finish_curve_data_update(key, notify=True)

    def remove_curve(self, key: str) -> None:
        with self._change_dispatcher.batch():
            self._trace_persistence.remove(key)
            self._curve_manager.remove_curve(key)
            self._cursors.refresh_for_curve(key)
            self._finish_range_and_presentation_update()
            self._change_dispatcher.curve_removed(key)

    def set_curve_style(self, key: str, style: CurveStyle) -> None:
        if self._curve_manager.set_curve_style(key, style):
            self._style_controller.apply_curve_style(self._curve_manager.get_curve(key))
            curve = self._curve_manager.get_curve(key)
            self._trace_persistence.update_curve(key, curve.style, curve.visible)
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
            curve = self._curve_manager.get_curve(key)
            self._trace_persistence.update_curve(key, curve.style, curve.visible)
            self._cursors.handle_curve_visibility_changed(key)
            self._finish_range_and_presentation_update()
            self._publish_curve_changed(key)

    def _cursor_axis_format(
        self,
        cursor_type: CursorType,
    ) -> tuple[float, str, str | None]:
        axis = self.bottom_axis if cursor_type is CursorType.X else self.left_axis
        units = self.x_label_units if cursor_type is CursorType.X else self.y_label_units
        return axis.autoSIPrefixScale, axis.labelUnitPrefix, units

    @property
    def cursors(self) -> PyQtLabGraphCursors:
        """Cursor and cursor-pair commands and state for this plot."""
        return self._cursors

    @property
    def x_log(self) -> bool:
        return self._x_log

    @property
    def y_log(self) -> bool:
        return self._y_log

    def set_x_log(self, enabled: bool) -> None:
        self._set_axis_log(CursorType.X, enabled)

    def set_y_log(self, enabled: bool) -> None:
        self._set_axis_log(CursorType.Y, enabled)

    def _set_axis_log(self, axis: CursorType, enabled: bool) -> None:
        is_x = axis is CursorType.X
        if (self._x_log if is_x else self._y_log) == enabled:
            return
        with self._change_dispatcher.batch():
            if enabled and is_x and self.x_axis_mode == AxisMode.TIME:
                self.x_axis_mode = AxisMode.LINEAR
                self._apply_axis_label(CursorType.X)
            elif enabled and not is_x and self.y_axis_mode == AxisMode.TIME:
                self.y_axis_mode = AxisMode.LINEAR
                self._apply_axis_label(CursorType.Y)
            self.applying_axis_scaling = True
            try:
                minimum, maximum = self.get_x_range() if is_x else self.get_y_range()
                if is_x:
                    self._x_log = enabled
                else:
                    self._y_log = enabled
                self._plot_item.setLogMode(x=self._x_log, y=self._y_log)

                state = self._interaction_state
                autoscaled = (
                    state.autoscale_x or state.rolling_x if is_x else state.autoscale_y
                )
                if autoscaled:
                    self._range_controller.apply_axis_scaling()
                else:
                    converted = _convert_log_range(minimum, maximum, enabled)
                    if is_x:
                        self._range_controller.set_x_range(*converted)
                    else:
                        self._range_controller.set_y_range(*converted)
            finally:
                self.applying_axis_scaling = False
            if self._render_optimizer.update_adaptive_performance(force=True):
                self._reapply_curve_styles()
            self._cursors.refresh_presentation()
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
        self._apply_persistence_rendering()

    @property
    def antialiasing_enabled(self) -> bool:
        return self._render_optimizer.antialiasing_enabled

    def set_downsampling_enabled(self, enabled: bool) -> None:
        self._render_optimizer.set_downsampling_enabled(enabled)
        self._apply_persistence_rendering()

    @property
    def downsampling_enabled(self) -> bool:
        return self._render_optimizer.downsampling_enabled

    def set_clip_to_view_enabled(self, enabled: bool) -> None:
        self._render_optimizer.set_clip_to_view_enabled(enabled)
        self._apply_persistence_rendering()

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
        changes: dict[str, object] = {"active_tool": tool if enabled else InteractionTool.NONE}
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
            self._cursors.refresh_presentation()

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        with self._change_dispatcher.batch():
            self._replace_interaction_state(autoscale_y=False)
            self._range_controller.apply_manual_y_limits(ymin, ymax)
            self._cursors.refresh_presentation()

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
            self._cursors.refresh_presentation()
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

    @property
    def curve_palette(self) -> PyQtLabGraphCurvePalette:
        return self._curve_palette

    @property
    def curve_palette_reversed(self) -> bool:
        return self._curve_palette_reverse

    def _curve_palette_color(self, index: int) -> QColor:
        palette_index = -index - 1 if self._curve_palette_reverse else index
        return self._curve_palette.color(palette_index)

    def set_curve_palette(
        self,
        palette: str | PyQtLabGraphCurvePalette,
        *,
        reverse: bool | None = None,
    ) -> None:
        """Assign palette colors to all current curves and future curves."""
        resolved = self._style_registry.resolve_curve_palette(palette)
        if reverse is not None and not isinstance(reverse, bool):
            raise TypeError("reverse must be a bool or None.")
        next_reverse = self._curve_palette_reverse if reverse is None else reverse
        palette_changed = resolved != self._curve_palette
        reverse_changed = next_reverse != self._curve_palette_reverse
        recolor = tuple(
            (index, curve)
            for index, curve in enumerate(self._curve_manager.ordered_curves())
            if curve.style.line_color
            != resolved.color(-index - 1 if next_reverse else index).name()
        )
        if not palette_changed and not reverse_changed and not recolor:
            return
        self._curve_palette = resolved
        self._curve_palette_reverse = next_reverse
        with self._change_dispatcher.batch():
            for index, curve in recolor:
                self.set_curve_style(
                    curve.key,
                    replace(
                        curve.style,
                        line_color=resolved.color(
                            -index - 1 if next_reverse else index
                        ).name(),
                    ),
                )
            if palette_changed or reverse_changed:
                self._publish_presentation_changed()

    def apply_curve_gradient(
        self,
        gradient: str | PyQtLabGraphColorGradient,
        *,
        values: Mapping[str, float] | None = None,
        value_range: tuple[float, float] | None = None,
        reverse: bool = False,
    ) -> None:
        resolved = self._style_registry.resolve_color_gradient(gradient)
        if not isinstance(reverse, bool):
            raise TypeError("reverse must be a bool.")
        keys = [key for key, _label in self.curve_choices()]
        if values is None:
            if value_range is not None:
                raise ValueError("value_range requires explicit curve values.")
            positions = {
                key: (0.5 if len(keys) == 1 else index / (len(keys) - 1))
                for index, key in enumerate(keys)
            }
        else:
            if not isinstance(values, Mapping) or not values:
                raise ValueError("values must be a non-empty mapping.")
            if any(not isinstance(key, str) for key in values):
                raise TypeError("Gradient curve keys must be strings.")
            unknown = set(values).difference(keys)
            if unknown:
                raise KeyError(f'Curve "{sorted(unknown)[0]}" does not exist.')
            numeric: dict[str, float] = {}
            for key, raw in values.items():
                if isinstance(raw, bool) or not isinstance(raw, (int, float)):
                    raise TypeError("Gradient curve values must be real numbers.")
                value = float(raw)
                if not np.isfinite(value):
                    raise ValueError("Gradient curve values must be finite.")
                numeric[key] = value
            if value_range is None:
                low, high = min(numeric.values()), max(numeric.values())
            else:
                if len(value_range) != 2:
                    raise ValueError("value_range must contain exactly two values.")
                if any(
                    isinstance(value, bool) or not isinstance(value, (int, float))
                    for value in value_range
                ):
                    raise TypeError("value_range values must be real numbers.")
                low, high = float(value_range[0]), float(value_range[1])
                if not np.isfinite(low) or not np.isfinite(high) or low >= high:
                    raise ValueError("value_range must be finite and strictly increasing.")
            positions = {
                key: 0.5 if low == high else (value - low) / (high - low)
                for key, value in numeric.items()
            }
        updates = {
            key: replace(
                self.curve_style(key),
                line_color=resolved.color_at(position, reverse=reverse).name(),
            )
            for key, position in positions.items()
        }
        with self._change_dispatcher.batch():
            for key, style in updates.items():
                self.set_curve_style(key, style)

    def set_curve_persistence(self, key: str, config: TracePersistenceConfig | None) -> None:
        curve = self._curve_manager.get_curve(key)
        if self._trace_persistence.config(key) == config:
            return
        self._trace_persistence.set_config(key, config)
        self._trace_persistence.update_curve(key, curve.style, curve.visible)
        self._apply_persistence_rendering()
        self._publish_curve_changed(key)

    def curve_persistence(self, key: str) -> TracePersistenceConfig | None:
        self._curve_manager.get_curve(key)
        return self._trace_persistence.config(key)

    def clear_curve_persistence_history(self, key: str) -> None:
        self._curve_manager.get_curve(key)
        self._trace_persistence.clear(key)

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
        current_curve_keys = {key for key, _label in self.curve_choices()}
        snapshot_curve_keys = {state.key for state in snapshot.curves}
        if snapshot_curve_keys != current_curve_keys:
            raise ValueError("PlotSnapshot curve keys must match the target widget.")

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
        self.set_curve_palette(
            snapshot.curve_palette,
            reverse=snapshot.curve_palette_reverse,
        )
        for curve in snapshot.curves:
            self.set_curve_visible(curve.key, curve.visible)
            self.set_curve_style(curve.key, curve.style)
            self.set_curve_persistence(curve.key, curve.persistence)

        for cursor in tuple(self._cursors.states()):
            self._cursors.remove(cursor.key)
        for cursor in snapshot.cursors:
            self._cursors.add(
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
                self._cursors.set_visible(cursor.key, False)
        for pair in snapshot.cursor_pairs:
            self._cursors.add_pair(
                pair.first_cursor_key,
                pair.second_cursor_key,
                key=pair.key,
                measurement_visible=pair.measurement_visible,
                annotation_position=pair.annotation_position,
            )
        self._cursors.set_order([state.key for state in snapshot.cursors])
        self._cursors.set_selected_keys(snapshot.selected_cursor_keys)

        self.apply_interaction_state(snapshot.interaction_state)
        self._range_controller.set_x_range(*snapshot.x_range)
        self._range_controller.set_y_range(*snapshot.y_range)
        if self._render_optimizer.update_adaptive_performance(force=True):
            self._reapply_curve_styles()
        self._cursors.refresh_presentation()

    def load_layout(self, path: str | Path | None = None) -> bool:
        layout = load_plot_layout(self._resolve_layout_path(path), self.plot_identifier)
        if layout is None:
            return False
        apply_plot_layout(self, layout)
        self._trace_persistence.clear_all()
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

        self._apply_axis_label(CursorType.X)
        self._apply_axis_label(CursorType.Y)
        self._cursors.refresh_presentation()
        self._publish_presentation_changed()

    def _apply_axis_label(self, axis: CursorType) -> None:
        if axis is CursorType.X:
            self.bottom_axis.set_mode(self.x_axis_mode)
            self.bottom_axis.setLabel(
                self.x_label_text,
                units=self.x_label_units,
                **{
                    "color": self._style_controller.host_axis_color_name(),
                    "margin-top": _AXIS_LABEL_TOP_MARGIN,
                },
            )
        else:
            self.left_axis.set_mode(self.y_axis_mode)
            self.left_axis.setLabel(
                self.y_label_text,
                units=self.y_label_units,
                **{
                    "color": self._style_controller.host_axis_color_name(),
                    "margin-right": _AXIS_LABEL_RIGHT_MARGIN,
                },
            )

    def _handle_view_range_changed(self, *_args: object) -> None:
        if self.applying_axis_scaling or self._range_controller.applying_range:
            return
        with self._change_dispatcher.batch():
            self.request_manual_navigation()
            if self._render_optimizer.update_adaptive_performance():
                self._reapply_curve_styles()
            self._cursors.refresh_presentation()
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


def _convert_log_range(
    minimum: float,
    maximum: float,
    to_log: bool,
) -> tuple[float, float]:
    """Convert a manual view range between linear and log10 view coordinates."""
    if to_log:
        return (
            float(np.log10(minimum if minimum > 0 else 0.1)),
            float(np.log10(maximum if maximum > 0 else 10.0)),
        )
    return (
        float(10 ** np.clip(minimum, -20.0, 20.0)),
        float(10 ** np.clip(maximum, -20.0, 20.0)),
    )
