from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace

import numpy as np
import pyqtgraph as pg
from numpy.typing import NDArray
from pyqtgraph import PlotItem, ViewBox

from .axis import AxisMode, format_relative_time
from .cursor_presenter import CursorPlotPresenter
from .dispatch import PlotChangeDispatcher
from .models import CursorPairState, CursorState, CursorStyle, CursorType

CurveData = tuple[NDArray[np.generic], NDArray[np.generic]]
FloatCurveData = tuple[NDArray[np.float64], NDArray[np.float64]]

_CURSOR_VALUE_COMPARE_REL_TOLERANCE = 1e-12
_CURSOR_COLORS = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
)
_DEFAULT_PAIR_ANNOTATION_POSITION = 0.08


class PyQtLabGraphCursors:
    """Cursor and cursor-pair state of one plot, available as `plot.cursors`.

    Commands validate and update immutable `CursorState`/`CursorPairState`
    values, keep the plot graphics in sync, and publish the plot widget's
    cursor signals.
    """

    def __init__(
        self,
        *,
        dispatcher: PlotChangeDispatcher,
        plot_item: PlotItem,
        view_box: ViewBox,
        curve_data_provider: Callable[[str], CurveData],
        curve_visible_provider: Callable[[str], bool],
        x_range_provider: Callable[[], tuple[float, float]],
        y_range_provider: Callable[[], tuple[float, float]],
        axis_mode_provider: Callable[[CursorType], AxisMode],
        axis_format_provider: Callable[[CursorType], tuple[float, str, str | None]],
        x_log_provider: Callable[[], bool],
        y_log_provider: Callable[[], bool],
        plot_background_provider: Callable[[], str],
    ) -> None:
        self._dispatcher = dispatcher
        self._curve_data_provider = curve_data_provider
        self._curve_visible_provider = curve_visible_provider
        self._x_range_provider = x_range_provider
        self._y_range_provider = y_range_provider
        self._axis_mode_provider = axis_mode_provider
        self._axis_format_provider = axis_format_provider
        self._x_log_provider = x_log_provider
        self._y_log_provider = y_log_provider
        self._cursors: dict[str, CursorState] = {}
        self._order: list[str] = []
        self._pairs: dict[str, CursorPairState] = {}
        self._pair_by_cursor: dict[str, str] = {}
        self._selected: list[str] = []
        self._curve_data_cache: dict[str, FloatCurveData | None] = {}
        self._sorted_x_cache: dict[str, np.ndarray] = {}
        self._key_counters = {CursorType.X: 0, CursorType.Y: 0}
        self._pair_key_counter = 0
        self.presenter = CursorPlotPresenter(
            controller=self,
            plot_item=plot_item,
            view_box=view_box,
            x_log_provider=x_log_provider,
            y_log_provider=y_log_provider,
            plot_background_provider=plot_background_provider,
        )

    # State queries

    def state(self, cursor_key: str) -> CursorState:
        try:
            return self._cursors[cursor_key]
        except KeyError as exc:
            raise KeyError(f'Cursor "{cursor_key}" does not exist.') from exc

    def states(self) -> tuple[CursorState, ...]:
        return tuple(self._cursors[key] for key in self._order)

    def pair_state(self, pair_key: str) -> CursorPairState:
        try:
            return self._pairs[pair_key]
        except KeyError as exc:
            raise KeyError(f'Cursor pair "{pair_key}" does not exist.') from exc

    def pair_states(self) -> tuple[CursorPairState, ...]:
        positions = {key: index for index, key in enumerate(self._order)}
        return tuple(sorted(self._pairs.values(), key=lambda p: positions[p.first_cursor_key]))

    def pair_for_cursor(self, cursor_key: str) -> CursorPairState | None:
        self.state(cursor_key)
        pair_key = self._pair_by_cursor.get(cursor_key)
        return self._pairs[pair_key] if pair_key is not None else None

    def selected_keys(self) -> list[str]:
        return list(self._selected)

    def effective_visible(self, cursor_key: str) -> bool:
        state = self.state(cursor_key)
        if not state.visible:
            return False
        if not state.follow_target_visibility or state.snap_target_curve_key is None:
            return True
        try:
            return bool(self._curve_visible_provider(state.snap_target_curve_key))
        except KeyError:
            return True

    def target_value(self, cursor_key: str) -> float | None:
        """Return the snap target curve's Y value at the cursor, if available."""
        state = self.state(cursor_key)
        if state.snap_target_curve_key is None:
            return None
        curve_data = self._curve_data(state.snap_target_curve_key)
        if curve_data is None:
            return None
        x_values, y_values = curve_data
        finite_x = np.isfinite(x_values)
        if not finite_x.any():
            return None
        finite_indices = np.flatnonzero(finite_x)
        index = int(finite_indices[np.argmin(np.abs(x_values[finite_x] - state.value))])
        target_value = float(y_values[index])
        return target_value if math.isfinite(target_value) else None

    def format_value(self, cursor_type: CursorType, value: float) -> str:
        if not math.isfinite(value):
            return ""
        axis_mode = self._axis_mode_provider(cursor_type)
        if axis_mode is AxisMode.TIME:
            return format_relative_time(value)
        scale, prefix, units = self._axis_format_provider(cursor_type)
        if axis_mode is not AxisMode.AUTO:
            scale, prefix = 1.0, ""
        value_text = _format_number(value * scale)
        suffix = f"{prefix}{units or ''}"
        return f"{value_text} {suffix}" if suffix else value_text

    def pair_measurement_parts(self, pair_key: str) -> tuple[str, str, str]:
        pair = self.pair_state(pair_key)
        first = self.state(pair.first_cursor_key)
        second = self.state(pair.second_cursor_key)
        delta = abs(second.value - first.value)
        axis_mode = self._axis_mode_provider(first.cursor_type)
        axis_name = "t" if axis_mode is AxisMode.TIME else first.cursor_type.value
        secondary = ""
        if axis_mode is AxisMode.TIME and delta > 0.0:
            secondary = f"f = {pg.siFormat(1.0 / delta, suffix='Hz', precision=6)}"
        return f"Δ{axis_name} =", self.format_value(first.cursor_type, delta), secondary

    def pair_measurement_text(self, pair_key: str) -> str:
        label, value, secondary = self.pair_measurement_parts(pair_key)
        text = f"{label} {value}"
        return f"{text}   {secondary}" if secondary else text

    # Cursor commands

    def add(
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
        resolved_type = _resolve_cursor_type(cursor_type)
        cursor_key = key or self._next_key(resolved_type)
        if cursor_key in self._cursors:
            raise ValueError(f'Cursor "{cursor_key}" already exists.')
        state = CursorState(
            key=cursor_key,
            name=name or self._default_name(resolved_type),
            cursor_type=resolved_type,
            value=self._default_value(resolved_type) if value is None else _finite_float(value),
            style=style or CursorStyle(line_color=_CURSOR_COLORS[len(self._order) % 6]),
            snap_target_curve_key=snap_target_curve_key,
            follow_target_visibility=follow_target_visibility,
            label_visible=label_visible,
        )
        self._cursors[cursor_key] = self._snapped(state)
        self._order.append(cursor_key)
        self.presenter.create_cursor(cursor_key)
        self._publish("cursor_added", cursor_key)
        return cursor_key

    def remove(self, cursor_key: str) -> None:
        self.state(cursor_key)
        pair = self.pair_for_cursor(cursor_key)
        if pair is not None:
            self.remove_pair(pair.key)
        del self._cursors[cursor_key]
        self._order.remove(cursor_key)
        self._selected = [key for key in self._selected if key != cursor_key]
        self.presenter.remove_cursor(cursor_key)
        self._publish("cursor_removed", cursor_key)
        self._publish("cursor_selection_changed")

    def set_value(self, cursor_key: str, value: float, *, move_selected: bool = False) -> None:
        """Move a cursor; with `move_selected`, selected peers on its axis follow."""
        before = self.state(cursor_key)
        self._replace(cursor_key, value=_finite_float(value))
        after = self.state(cursor_key)
        self._present_cursor(cursor_key)
        self._publish("cursor_moved", cursor_key, after.value)
        if move_selected and cursor_key in self._selected:
            self._move_peers(cursor_key, self._selected, after.value - before.value)

    def set_name(self, cursor_key: str, name: str) -> None:
        cursor_name = str(name).strip()
        if not cursor_name:
            raise ValueError("Cursor name must not be empty.")
        self._update(cursor_key, name=cursor_name)

    def set_style(self, cursor_key: str, style: CursorStyle) -> None:
        self._update(cursor_key, style=style)

    def set_label_visible(self, cursor_key: str, visible: bool) -> None:
        self._update(cursor_key, label_visible=visible)

    def set_visible(self, cursor_key: str, visible: bool) -> None:
        self._update(cursor_key, visible=visible)

    def set_follow_target_visibility(self, cursor_key: str, enabled: bool) -> None:
        self._update(cursor_key, follow_target_visibility=enabled)

    def set_snap_target(self, cursor_key: str, target_curve_key: str | None) -> None:
        before_value = self.state(cursor_key).value
        self._update(cursor_key, snap_target_curve_key=target_curve_key)
        after_value = self.state(cursor_key).value
        if after_value != before_value:
            self._publish("cursor_moved", cursor_key, after_value)

    def set_order(self, cursor_keys: Sequence[str]) -> None:
        ordered = list(cursor_keys)
        if (
            len(ordered) != len(self._order)
            or any(not isinstance(key, str) for key in ordered)
            or set(ordered) != set(self._order)
        ):
            raise ValueError("Cursor order must contain every current cursor key exactly once.")
        positions = {key: index for index, key in enumerate(ordered)}
        for pair in self._pairs.values():
            if positions[pair.second_cursor_key] != positions[pair.first_cursor_key] + 1:
                raise ValueError(f'Cursor pair "{pair.key}" must remain an ordered adjacent block.')
        if ordered != self._order:
            self._order = ordered
            self._publish("cursor_order_changed")

    def set_selected_keys(self, cursor_keys: Sequence[str]) -> None:
        selected = [key for key in cursor_keys if key in self._cursors]
        if selected == self._selected:
            return
        self._selected = selected
        self._dispatcher.refresh(self.presenter.update_all)
        self._publish("cursor_selection_changed")

    def nudge_group(
        self,
        cursor_key: str,
        *,
        selected_cursor_keys: list[str],
        direction: int,
        step_ratio: float,
    ) -> bool:
        """Step a cursor (snapped X cursors to the next sample) and move its peers."""
        state = self.state(cursor_key)
        if state.cursor_type is CursorType.X and state.snap_target_curve_key:
            nudged = self._nudged_snap_value(state, direction)
        else:
            nudged = self._nudged_free_value(state, direction, step_ratio)
        if nudged is None or _values_close(nudged, state.value):
            return False
        self.set_value(cursor_key, nudged)
        delta = self.state(cursor_key).value - state.value
        self._move_peers(cursor_key, selected_cursor_keys, delta)
        return True

    # Pair commands

    def add_pair(
        self,
        first_cursor_key: str,
        second_cursor_key: str,
        *,
        key: str | None = None,
        measurement_visible: bool = True,
        annotation_position: float = _DEFAULT_PAIR_ANNOTATION_POSITION,
    ) -> str:
        first = self.state(first_cursor_key)
        second = self.state(second_cursor_key)
        if first.cursor_type is not second.cursor_type:
            raise ValueError("Cursor pair requires cursors on the same axis.")
        for member in (first_cursor_key, second_cursor_key):
            if member in self._pair_by_cursor:
                raise ValueError(f'Cursor "{member}" already belongs to a pair.')
        pair_key = key or self._next_pair_key()
        if pair_key in self._pairs:
            raise ValueError(f'Cursor pair "{pair_key}" already exists.')
        self._pairs[pair_key] = CursorPairState(
            key=pair_key,
            first_cursor_key=first_cursor_key,
            second_cursor_key=second_cursor_key,
            measurement_visible=measurement_visible,
            annotation_position=_clamped_annotation_position(annotation_position),
        )
        self._pair_by_cursor[first_cursor_key] = pair_key
        self._pair_by_cursor[second_cursor_key] = pair_key
        self._order.remove(second_cursor_key)
        self._order.insert(self._order.index(first_cursor_key) + 1, second_cursor_key)
        self.presenter.create_pair(pair_key)
        self._publish("cursor_pair_added", pair_key)
        return pair_key

    def remove_pair(self, pair_key: str) -> None:
        pair = self.pair_state(pair_key)
        del self._pairs[pair_key]
        self._pair_by_cursor.pop(pair.first_cursor_key, None)
        self._pair_by_cursor.pop(pair.second_cursor_key, None)
        self.presenter.remove_pair(pair_key)
        self._publish("cursor_pair_removed", pair_key)

    def set_pair_measurement_visible(self, pair_key: str, visible: bool) -> None:
        self._update_pair(pair_key, measurement_visible=visible)

    def set_pair_annotation_position(self, pair_key: str, position: float) -> None:
        self._update_pair(pair_key, annotation_position=_clamped_annotation_position(position))

    # Plot hooks

    def refresh_presentation(self) -> None:
        """Refresh all cursor and pair graphics from the current state."""
        self._dispatcher.refresh(self.presenter.update_all)

    def refresh_for_curve(self, curve_key: str) -> None:
        """Re-snap cursors after the data of `curve_key` changed or was removed."""
        self._curve_data_cache.pop(curve_key, None)
        self._sorted_x_cache.pop(curve_key, None)
        for state in self.states():
            if state.snap_target_curve_key != curve_key:
                continue
            self._cursors[state.key] = self._snapped(state)
            after_value = self._cursors[state.key].value
            self._present_cursor(state.key)
            self._publish("cursor_changed", state.key)
            if after_value != state.value:
                self._publish("cursor_moved", state.key, after_value)

    def refresh_for_curve_visibility(self, curve_key: str) -> None:
        """Update cursors whose visibility follows `curve_key`."""
        for state in self.states():
            if state.follow_target_visibility and state.snap_target_curve_key == curve_key:
                self._present_cursor(state.key)
                self._publish("cursor_changed", state.key)

    # Internals

    def _publish(self, signal_name: str, *args: object) -> None:
        self._dispatcher.publish(signal_name, *args)

    def _present_cursor(self, cursor_key: str) -> None:
        if self._dispatcher.batching:
            self._dispatcher.refresh(self.presenter.update_all)
            return
        self.presenter.update_cursor(cursor_key)
        self.presenter.update_pair_for_cursor(cursor_key)

    def _replace(self, cursor_key: str, **changes: object) -> None:
        state = replace(self.state(cursor_key), **changes)  # type: ignore[arg-type]
        self._cursors[cursor_key] = self._snapped(state)

    def _update(self, cursor_key: str, **changes: object) -> None:
        self._replace(cursor_key, **changes)
        self._present_cursor(cursor_key)
        self._publish("cursor_changed", cursor_key)

    def _update_pair(self, pair_key: str, **changes: object) -> None:
        self._pairs[pair_key] = replace(self.pair_state(pair_key), **changes)  # type: ignore[arg-type]
        if self._dispatcher.batching:
            self._dispatcher.refresh(self.presenter.update_all)
        else:
            self.presenter.update_pair(pair_key)
        self._publish("cursor_pair_changed", pair_key)

    def _move_peers(self, anchor_key: str, selected_keys: Sequence[str], delta: float) -> None:
        if not math.isfinite(delta) or _values_close(delta, 0.0):
            return
        cursor_type = self.state(anchor_key).cursor_type
        for peer_key in selected_keys:
            peer = self._cursors.get(peer_key)
            if peer_key != anchor_key and peer is not None and peer.cursor_type is cursor_type:
                self.set_value(peer_key, peer.value + delta)

    def _snapped(self, state: CursorState) -> CursorState:
        if state.snap_target_curve_key is None:
            return state
        curve_data = self._curve_data(state.snap_target_curve_key)
        if curve_data is None:
            return state
        finite_x = curve_data[0][np.isfinite(curve_data[0])]
        if len(finite_x) == 0:
            return state
        index = int(np.argmin(np.abs(finite_x - state.value)))
        return replace(state, value=float(finite_x[index]))

    def _curve_data(self, curve_key: str) -> FloatCurveData | None:
        if curve_key in self._curve_data_cache:
            return self._curve_data_cache[curve_key]
        try:
            x_values, y_values = self._curve_data_provider(curve_key)
        except KeyError:
            return None
        x_array = np.asarray(x_values, dtype=float)
        y_array = np.asarray(y_values, dtype=float)
        if len(x_array) != len(y_array):
            raise ValueError(
                f'Curve "{curve_key}" returned {len(x_array)} x values and '
                f"{len(y_array)} y values."
            )
        self._curve_data_cache[curve_key] = (x_array, y_array)
        return x_array, y_array

    def _sorted_finite_x_values(self, curve_key: str) -> np.ndarray:
        cached = self._sorted_x_cache.get(curve_key)
        if cached is not None:
            return cached
        curve_data = self._curve_data(curve_key)
        if curve_data is None:
            return np.array([], dtype=float)
        x_values = curve_data[0]
        sorted_values = np.unique(x_values[np.isfinite(x_values)])
        self._sorted_x_cache[curve_key] = sorted_values
        return sorted_values

    def _nudged_free_value(
        self,
        state: CursorState,
        direction: int,
        step_ratio: float,
    ) -> float | None:
        is_x = state.cursor_type is CursorType.X
        minimum, maximum = self._x_range_provider() if is_x else self._y_range_provider()
        log_axis = self._x_log_provider() if is_x else self._y_log_provider()
        if log_axis and state.value <= 0.0:
            return None
        display_value = math.log10(state.value) if log_axis else state.value
        span = abs(maximum - minimum)
        if not math.isfinite(span) or span <= 0.0:
            span = 1.0
        display_value += (1 if direction > 0 else -1) * span * step_ratio
        if not math.isfinite(display_value):
            return None
        if not log_axis:
            return display_value
        raw_value = 10**display_value
        return raw_value if math.isfinite(raw_value) and raw_value > 0.0 else None

    def _nudged_snap_value(self, state: CursorState, direction: int) -> float | None:
        assert state.snap_target_curve_key is not None
        sorted_values = self._sorted_finite_x_values(state.snap_target_curve_key)
        tolerance = max(abs(state.value), 1.0) * _CURSOR_VALUE_COMPARE_REL_TOLERANCE
        if direction > 0:
            candidates = sorted_values[sorted_values > state.value + tolerance]
            return float(candidates[0]) if len(candidates) else None
        candidates = sorted_values[sorted_values < state.value - tolerance]
        return float(candidates[-1]) if len(candidates) else None

    def _next_key(self, cursor_type: CursorType) -> str:
        prefix = "x_cursor" if cursor_type is CursorType.X else "y_cursor"
        while True:
            self._key_counters[cursor_type] += 1
            key = f"{prefix}_{self._key_counters[cursor_type]}"
            if key not in self._cursors:
                return key

    def _next_pair_key(self) -> str:
        while True:
            self._pair_key_counter += 1
            key = f"cursor_pair_{self._pair_key_counter}"
            if key not in self._pairs:
                return key

    def _default_name(self, cursor_type: CursorType) -> str:
        count = sum(1 for state in self._cursors.values() if state.cursor_type is cursor_type)
        return f"{cursor_type.value.upper()} Cursor {count + 1}"

    def _default_value(self, cursor_type: CursorType) -> float:
        provider = self._x_range_provider if cursor_type is CursorType.X else self._y_range_provider
        minimum, maximum = provider()
        return _finite_float((minimum + maximum) / 2.0)


def _resolve_cursor_type(cursor_type: CursorType | str) -> CursorType:
    if isinstance(cursor_type, CursorType):
        return cursor_type
    try:
        return CursorType(cursor_type.lower())
    except (AttributeError, ValueError) as exc:
        raise ValueError(f'Unknown cursor type "{cursor_type}".') from exc


def _finite_float(value: float) -> float:
    numeric_value = float(value)
    if not math.isfinite(numeric_value):
        raise ValueError("Cursor value must be finite.")
    return numeric_value


def _clamped_annotation_position(value: float) -> float:
    return min(1.0, max(0.0, _finite_float(value)))


def _values_close(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=_CURSOR_VALUE_COMPARE_REL_TOLERANCE,
        abs_tol=_CURSOR_VALUE_COMPARE_REL_TOLERANCE,
    )


def _format_number(value: float) -> str:
    return "" if not math.isfinite(value) else f"{value:.6g}"
