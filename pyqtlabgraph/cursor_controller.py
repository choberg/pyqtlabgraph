from __future__ import annotations

import math
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from pyqtgraph import PlotItem, ViewBox
from PySide6.QtCore import QObject, Signal

from .axis import AxisMode, format_relative_time
from .cursor_manager import CursorManager
from .cursor_presenter import CursorPlotPresenter
from .models import CursorPairState, CursorState, CursorStyle, CursorType

_CURSOR_VALUE_COMPARE_REL_TOLERANCE = 1e-12


class CursorController(QObject):
    """Coordinates cursor domain state and its plot/UI presentations."""

    cursor_added = Signal(str)
    cursor_removed = Signal(str)
    cursor_moved = Signal(str, float)
    cursor_changed = Signal(str)
    cursor_pair_added = Signal(str)
    cursor_pair_removed = Signal(str)
    cursor_pair_changed = Signal(str)
    cursor_order_changed = Signal()
    selection_changed = Signal()

    def __init__(
        self,
        *,
        parent: QObject,
        plot_item: PlotItem,
        view_box: ViewBox,
        curve_data_provider: Callable[
            [str],
            tuple[NDArray[np.generic], NDArray[np.generic]],
        ],
        curve_visible_provider: Callable[[str], bool],
        curve_choices_provider: Callable[[], tuple[tuple[str, str], ...]],
        x_range_provider: Callable[[], tuple[float, float]],
        y_range_provider: Callable[[], tuple[float, float]],
        axis_mode_provider: Callable[[CursorType], AxisMode],
        axis_format_provider: Callable[[CursorType], tuple[float, str, str | None]],
        x_log_provider: Callable[[], bool],
        y_log_provider: Callable[[], bool],
        plot_background_provider: Callable[[], str],
    ) -> None:
        super().__init__(parent)
        self._curve_choices_provider = curve_choices_provider
        self._x_range_provider = x_range_provider
        self._y_range_provider = y_range_provider
        self._axis_mode_provider = axis_mode_provider
        self._axis_format_provider = axis_format_provider
        self._x_log_provider = x_log_provider
        self._y_log_provider = y_log_provider
        self.manager = CursorManager(
            curve_data_provider=curve_data_provider,
            curve_visible_provider=curve_visible_provider,
            x_range_provider=x_range_provider,
            y_range_provider=y_range_provider,
        )
        self._selected_cursor_keys: list[str] = []
        self.presenter = CursorPlotPresenter(
            controller=self,
            plot_item=plot_item,
            view_box=view_box,
            x_log_provider=x_log_provider,
            y_log_provider=y_log_provider,
            plot_background_provider=plot_background_provider,
        )
        self._batch_depth = 0
        self._batch_needs_refresh = False
        self._pending_events: dict[tuple[str, str], tuple[object, ...]] = {}

    @contextmanager
    def batch_changes(self) -> Iterator[None]:
        self._batch_depth += 1
        try:
            yield
        finally:
            self._batch_depth -= 1
            if self._batch_depth == 0:
                if self._batch_needs_refresh:
                    self.presenter.update_all()
                self._batch_needs_refresh = False
                pending = tuple(self._pending_events.items())
                self._pending_events.clear()
                for (signal_name, _event_key), args in pending:
                    getattr(self, signal_name).emit(*args)

    def discard_batched_changes(self) -> None:
        """Discard presentation work and events queued by an enclosing command."""
        self._batch_needs_refresh = False
        self._pending_events.clear()

    def suppress_batched_events(self) -> None:
        """Keep the final presentation refresh but suppress granular signals."""
        self._pending_events.clear()

    def _present_cursor(self, cursor_key: str) -> None:
        if self._batch_depth:
            self._batch_needs_refresh = True
            return
        self.presenter.update_cursor(cursor_key)

    def refresh_presentation(self) -> None:
        """Refresh all cursor and pair graphics from authoritative state."""
        if self._batch_depth:
            self._batch_needs_refresh = True
            return
        self.presenter.update_all()

    def _present_pair_for_cursor(self, cursor_key: str) -> None:
        if self._batch_depth:
            self._batch_needs_refresh = True
            return
        self.presenter.update_pair_for_cursor(cursor_key)

    def _present_pair(self, pair_key: str) -> None:
        if self._batch_depth:
            self._batch_needs_refresh = True
            return
        self.presenter.update_pair(pair_key)

    def _emit(self, signal_name: str, *args: object) -> None:
        if self._batch_depth:
            event_key = str(args[0]) if args else signal_name
            self._pending_events[(signal_name, event_key)] = args
            return
        getattr(self, signal_name).emit(*args)

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
        cursor_key = self.manager.add_cursor(
            cursor_type,
            key=key,
            name=name,
            value=value,
            style=style,
            snap_target_curve_key=snap_target_curve_key,
            follow_target_visibility=follow_target_visibility,
            label_visible=label_visible,
        )
        self.presenter.create_cursor(cursor_key)
        self._emit("cursor_added", cursor_key)
        return cursor_key

    def remove_cursor(self, cursor_key: str) -> None:
        removed_pair_keys = [
            pair_state.key
            for pair_state in self.manager.cursor_pair_states()
            if cursor_key in {pair_state.first_cursor_key, pair_state.second_cursor_key}
        ]
        self.manager.remove_cursor(cursor_key)
        self._selected_cursor_keys = [key for key in self._selected_cursor_keys if key != cursor_key]
        for pair_key in removed_pair_keys:
            self.presenter.remove_pair(pair_key)
            self._emit("cursor_pair_removed", pair_key)
        self.presenter.remove_cursor(cursor_key)
        self._emit("cursor_removed", cursor_key)
        self._emit("selection_changed")

    def set_cursor_value(self, cursor_key: str, value: float) -> None:
        self.manager.set_cursor_value(cursor_key, value)
        self._present_cursor(cursor_key)
        self._present_pair_for_cursor(cursor_key)
        self._emit("cursor_moved", cursor_key, self.manager.cursor_state(cursor_key).value)

    def set_cursor_name(self, cursor_key: str, name: str) -> None:
        self.manager.set_cursor_name(cursor_key, name)
        self._present_cursor(cursor_key)
        self._emit("cursor_changed", cursor_key)

    def set_cursor_style(self, cursor_key: str, style: CursorStyle) -> None:
        self.manager.set_cursor_style(cursor_key, style)
        self._present_cursor(cursor_key)
        self._emit("cursor_changed", cursor_key)

    def set_cursor_snap_target(
        self,
        cursor_key: str,
        target_curve_key: str | None,
    ) -> None:
        before_value = self.manager.cursor_state(cursor_key).value
        self.manager.set_cursor_snap_target(
            cursor_key,
            target_curve_key=target_curve_key,
        )
        self._finish_snap_change(cursor_key, before_value)

    def _finish_snap_change(self, cursor_key: str, before_value: float) -> None:
        after_value = self.manager.cursor_state(cursor_key).value
        self._present_cursor(cursor_key)
        self._present_pair_for_cursor(cursor_key)
        self._emit("cursor_changed", cursor_key)
        if after_value != before_value:
            self._emit("cursor_moved", cursor_key, after_value)

    def set_cursor_label_visible(self, cursor_key: str, visible: bool) -> None:
        self.manager.set_cursor_label_visible(cursor_key, visible)
        self._present_cursor(cursor_key)
        self._emit("cursor_changed", cursor_key)

    def set_cursor_visible(self, cursor_key: str, visible: bool) -> None:
        self.manager.set_cursor_visible(cursor_key, visible)
        self._present_cursor(cursor_key)
        self._present_pair_for_cursor(cursor_key)
        self._emit("cursor_changed", cursor_key)

    def set_cursor_follow_target_visibility(self, cursor_key: str, enabled: bool) -> None:
        self.manager.set_cursor_follow_target_visibility(cursor_key, enabled)
        self._present_cursor(cursor_key)
        self._present_pair_for_cursor(cursor_key)
        self._emit("cursor_changed", cursor_key)

    def cursor_state(self, cursor_key: str) -> CursorState:
        return self.manager.cursor_state(cursor_key)

    def cursor_states(self) -> tuple[CursorState, ...]:
        return self.manager.cursor_states()

    def set_cursor_order(self, cursor_keys: Sequence[str]) -> None:
        if self.manager.set_cursor_order(cursor_keys):
            self._emit("cursor_order_changed")

    def cursor_target_value(self, cursor_key: str) -> float | None:
        return self.manager.target_value(cursor_key)

    def cursor_effective_visible(self, cursor_key: str) -> bool:
        return self.manager.effective_visible(cursor_key)

    def curve_choices(self) -> tuple[tuple[str, str], ...]:
        return self._curve_choices_provider()

    def add_cursor_pair(
        self,
        first_cursor_key: str,
        second_cursor_key: str,
        *,
        key: str | None = None,
        measurement_visible: bool = True,
        annotation_position: float = 0.08,
    ) -> str:
        pair_key = self.manager.add_cursor_pair(
            first_cursor_key,
            second_cursor_key,
            key=key,
            measurement_visible=measurement_visible,
            annotation_position=annotation_position,
        )
        self.presenter.create_pair(pair_key)
        self._emit("cursor_pair_added", pair_key)
        return pair_key

    def remove_cursor_pair(self, pair_key: str) -> None:
        self.manager.remove_cursor_pair(pair_key)
        self.presenter.remove_pair(pair_key)
        self._emit("cursor_pair_removed", pair_key)

    def set_cursor_pair_measurement_visible(self, pair_key: str, visible: bool) -> None:
        self.manager.set_cursor_pair_measurement_visible(pair_key, visible)
        self._present_pair(pair_key)
        self._emit("cursor_pair_changed", pair_key)

    def set_cursor_pair_annotation_position(self, pair_key: str, position: float) -> None:
        self.manager.set_cursor_pair_annotation_position(pair_key, position)
        self._present_pair(pair_key)
        self._emit("cursor_pair_changed", pair_key)

    def cursor_pair_state(self, pair_key: str) -> CursorPairState:
        return self.manager.cursor_pair_state(pair_key)

    def cursor_pair_states(self) -> tuple[CursorPairState, ...]:
        return self.manager.cursor_pair_states()

    def cursor_pair_for_cursor(self, cursor_key: str) -> CursorPairState | None:
        return self.manager.cursor_pair_for_cursor(cursor_key)

    def cursor_pair_measurement_text(self, pair_key: str) -> str:
        label, value, secondary = self.cursor_pair_measurement_parts(pair_key)
        text = f"{label} {value}"
        return f"{text}   {secondary}" if secondary else text

    def cursor_pair_measurement_parts(self, pair_key: str) -> tuple[str, str, str]:
        pair_state = self.manager.cursor_pair_state(pair_key)
        first_state = self.manager.cursor_state(pair_state.first_cursor_key)
        second_state = self.manager.cursor_state(pair_state.second_cursor_key)
        delta = abs(second_state.value - first_state.value)
        axis_mode = self.cursor_axis_mode(first_state.cursor_type)
        axis_name = "t" if axis_mode is AxisMode.TIME else first_state.cursor_type.value
        value_text = self.format_cursor_value(first_state.cursor_type, delta)
        secondary = ""
        if axis_mode is AxisMode.TIME and delta > 0.0:
            secondary = f"f = {pg.siFormat(1.0 / delta, suffix='Hz', precision=6)}"
        return f"Δ{axis_name} =", value_text, secondary

    def format_cursor_value(self, cursor_type: CursorType, value: float) -> str:
        if not math.isfinite(value):
            return ""
        axis_mode = self.cursor_axis_mode(cursor_type)
        if axis_mode is AxisMode.TIME:
            return format_relative_time(value)
        scale, prefix, units = self._axis_format_provider(cursor_type)
        if axis_mode is not AxisMode.AUTO:
            scale, prefix = 1.0, ""
        value_text = _format_number(value * scale)
        suffix = f"{prefix}{units or ''}"
        return f"{value_text} {suffix}" if suffix else value_text

    def cursor_axis_mode(self, cursor_type: CursorType) -> AxisMode:
        return self._axis_mode_provider(cursor_type)

    def set_selected_cursor_keys(self, cursor_keys: Sequence[str]) -> None:
        current_keys = {state.key for state in self.manager.cursor_states()}
        selected = [key for key in cursor_keys if key in current_keys]
        if selected == self._selected_cursor_keys:
            return
        self._selected_cursor_keys = selected
        self.presenter.update_all()
        self._emit("selection_changed")

    def selected_cursor_keys(self) -> list[str]:
        return list(self._selected_cursor_keys)

    def nudge_cursor_group(
        self,
        cursor_key: str,
        *,
        selected_cursor_keys: list[str],
        direction: int,
        step_ratio: float,
    ) -> bool:
        state = self.manager.cursor_state(cursor_key)
        before_value = state.value
        if not self._nudge_cursor_value(cursor_key, direction=direction, step_ratio=step_ratio):
            return False
        after_value = self.manager.cursor_state(cursor_key).value
        self.move_selected_cursor_peers(
            anchor_cursor_key=cursor_key,
            selected_cursor_keys=selected_cursor_keys,
            cursor_type=state.cursor_type,
            raw_delta=after_value - before_value,
        )
        return True

    def _nudge_cursor_value(self, cursor_key: str, *, direction: int, step_ratio: float) -> bool:
        state = self.manager.cursor_state(cursor_key)
        if state.cursor_type is CursorType.X and state.snap_target_curve_key:
            nudged_value = self._nudged_snap_cursor_value(state, direction)
        else:
            nudged_value = self._nudged_free_cursor_value(state, direction, step_ratio)
        if nudged_value is None or _values_close(nudged_value, state.value):
            return False
        self.set_cursor_value(cursor_key, nudged_value)
        return True

    def _nudged_free_cursor_value(
        self,
        state: CursorState,
        direction: int,
        step_ratio: float,
    ) -> float | None:
        minimum, maximum = (
            self._x_range_provider()
            if state.cursor_type is CursorType.X
            else self._y_range_provider()
        )
        display_value = self.cursor_display_value(state)
        if display_value is None:
            return None
        span = abs(maximum - minimum)
        if not math.isfinite(span) or span <= 0.0:
            span = 1.0
        display_value += (1 if direction > 0 else -1) * span * step_ratio
        return self.cursor_raw_value(state, display_value)

    def _nudged_snap_cursor_value(self, state: CursorState, direction: int) -> float | None:
        if state.snap_target_curve_key is None:
            return None
        sorted_values = self.manager.sorted_finite_x_values(state.snap_target_curve_key)
        if len(sorted_values) == 0:
            return None
        tolerance = max(abs(state.value), 1.0) * _CURSOR_VALUE_COMPARE_REL_TOLERANCE
        candidates = (
            sorted_values[sorted_values > state.value + tolerance]
            if direction > 0
            else sorted_values[sorted_values < state.value - tolerance]
        )
        if len(candidates) == 0:
            return None
        return float(candidates[0] if direction > 0 else candidates[-1])

    def cursor_display_value(self, state: CursorState) -> float | None:
        log_axis = self._x_log_provider() if state.cursor_type is CursorType.X else self._y_log_provider()
        if not log_axis:
            return state.value
        return math.log10(state.value) if state.value > 0.0 else None

    def cursor_raw_value(self, state: CursorState, display_value: float) -> float | None:
        if not math.isfinite(display_value):
            return None
        log_axis = self._x_log_provider() if state.cursor_type is CursorType.X else self._y_log_provider()
        if not log_axis:
            return display_value
        raw_value = 10**display_value
        return raw_value if math.isfinite(raw_value) and raw_value > 0.0 else None

    def move_selected_cursor_peers(
        self,
        *,
        anchor_cursor_key: str,
        selected_cursor_keys: list[str],
        cursor_type: CursorType,
        raw_delta: float,
    ) -> None:
        if not math.isfinite(raw_delta) or _values_close(raw_delta, 0.0):
            return
        for peer_key in selected_cursor_keys:
            if peer_key == anchor_cursor_key:
                continue
            try:
                peer_state = self.manager.cursor_state(peer_key)
            except KeyError:
                continue
            if peer_state.cursor_type is cursor_type:
                self.set_cursor_value(peer_key, peer_state.value + raw_delta)

    def refresh_for_curve(self, curve_key: str) -> None:
        self.manager.invalidate_curve_data(curve_key)
        affected = [
            state
            for state in self.manager.cursor_states()
            if state.snap_target_curve_key == curve_key
        ]
        for state in affected:
            before_value = state.value
            self.manager.refresh_cursor(state.key, invalidate_curve_data=False)
            self.presenter.update_cursor(state.key)
            self.presenter.update_pair_for_cursor(state.key)
            self._emit("cursor_changed", state.key)
            after_value = self.manager.cursor_state(state.key).value
            if after_value != before_value:
                self._emit("cursor_moved", state.key, after_value)

    def handle_curve_visibility_changed(self, curve_key: str) -> None:
        for state in self.manager.cursor_states():
            if state.follow_target_visibility and state.snap_target_curve_key == curve_key:
                self.presenter.update_cursor(state.key)
                self.presenter.update_pair_for_cursor(state.key)
                self._emit("cursor_changed", state.key)

def _values_close(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=_CURSOR_VALUE_COMPARE_REL_TOLERANCE,
        abs_tol=_CURSOR_VALUE_COMPARE_REL_TOLERANCE,
    )


def _format_number(value: float) -> str:
    return "" if not math.isfinite(value) else f"{value:.6g}"
