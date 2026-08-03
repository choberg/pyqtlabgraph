from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import replace

import numpy as np

from .models import CursorPairState, CursorState, CursorStyle, CursorType

CurveDataProvider = Callable[[str], tuple[np.ndarray, np.ndarray]]
CurveVisibleProvider = Callable[[str], bool]
RangeProvider = Callable[[], tuple[float, float]]

_DEFAULT_X_RANGE = (0.0, 1.0)
_DEFAULT_Y_RANGE = (0.0, 1.0)
_CURSOR_COLORS = (
    "#0072B2",
    "#D55E00",
    "#009E73",
    "#CC79A7",
    "#E69F00",
    "#56B4E9",
)
_DEFAULT_PAIR_ANNOTATION_POSITION = 0.08


class CursorManager:
    """Headless cursor state controller.

    This class deliberately has no dependency on widgets, table models, or
    pyqtgraph plot items. Callers provide curve data and visibility accessors.
    """

    def __init__(
        self,
        *,
        curve_data_provider: CurveDataProvider | None = None,
        curve_visible_provider: CurveVisibleProvider | None = None,
        x_range_provider: RangeProvider | None = None,
        y_range_provider: RangeProvider | None = None,
    ) -> None:
        self._curve_data_provider = curve_data_provider
        self._curve_visible_provider = curve_visible_provider
        self._x_range_provider = x_range_provider
        self._y_range_provider = y_range_provider
        self._cursors: dict[str, CursorState] = {}
        self._cursor_order: list[str] = []
        self._cursor_pairs: dict[str, CursorPairState] = {}
        self._pair_by_cursor: dict[str, str] = {}
        self._curve_data_cache: dict[str, tuple[np.ndarray, np.ndarray] | None] = {}
        self._sorted_x_cache: dict[str, np.ndarray] = {}
        self._pair_key_counter = 0
        self._key_counters = {
            CursorType.X: 0,
            CursorType.Y: 0,
        }

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
        visible: bool = True,
    ) -> str:
        resolved_type = resolve_cursor_type(cursor_type)
        cursor_key = key or self._next_key(resolved_type)
        if cursor_key in self._cursors:
            raise ValueError(f'Cursor "{cursor_key}" already exists.')

        cursor_style = style or self._default_style()
        cursor_value = self._default_value(resolved_type) if value is None else _finite_float(value)
        state = CursorState(
            key=cursor_key,
            name=name or self._default_name(resolved_type),
            cursor_type=resolved_type,
            value=cursor_value,
            visible=visible,
            style=cursor_style,
            snap_target_curve_key=snap_target_curve_key,
            follow_target_visibility=follow_target_visibility,
            label_visible=label_visible,
        )
        state = self._normalize_snap_state(state)
        self._cursors[cursor_key] = state
        self._cursor_order.append(cursor_key)
        return cursor_key

    def remove_cursor(self, cursor_key: str) -> None:
        self._require_cursor(cursor_key)
        for pair_state in tuple(self._cursor_pairs.values()):
            if cursor_key in {pair_state.first_cursor_key, pair_state.second_cursor_key}:
                self.remove_cursor_pair(pair_state.key)
        del self._cursors[cursor_key]
        self._cursor_order.remove(cursor_key)

    def cursor_state(self, cursor_key: str) -> CursorState:
        return self._require_cursor(cursor_key)

    def cursor_states(self) -> tuple[CursorState, ...]:
        return tuple(self._cursors[key] for key in self._cursor_order)

    def set_cursor_order(self, cursor_keys: Sequence[str]) -> bool:
        ordered_keys = list(cursor_keys)
        if (
            len(ordered_keys) != len(self._cursor_order)
            or any(not isinstance(key, str) for key in ordered_keys)
            or len(set(ordered_keys)) != len(ordered_keys)
            or set(ordered_keys) != set(self._cursor_order)
        ):
            raise ValueError("Cursor order must contain every current cursor key exactly once.")

        positions = {key: index for index, key in enumerate(ordered_keys)}
        for pair_state in self._cursor_pairs.values():
            first_index = positions[pair_state.first_cursor_key]
            if positions[pair_state.second_cursor_key] != first_index + 1:
                raise ValueError(
                    f'Cursor pair "{pair_state.key}" must remain an ordered adjacent block.'
                )

        if ordered_keys == self._cursor_order:
            return False
        self._cursor_order = ordered_keys
        return True

    def add_cursor_pair(
        self,
        first_cursor_key: str,
        second_cursor_key: str,
        *,
        key: str | None = None,
        measurement_visible: bool = True,
        annotation_position: float = _DEFAULT_PAIR_ANNOTATION_POSITION,
    ) -> str:
        first_state = self._require_cursor(first_cursor_key)
        second_state = self._require_cursor(second_cursor_key)
        if first_cursor_key == second_cursor_key:
            raise ValueError("Cursor pair requires two distinct cursors.")
        if first_state.cursor_type is not second_state.cursor_type:
            raise ValueError("Cursor pair requires cursors on the same axis.")
        if self.cursor_pair_for_cursor(first_cursor_key) is not None:
            raise ValueError(f'Cursor "{first_cursor_key}" already belongs to a pair.')
        if self.cursor_pair_for_cursor(second_cursor_key) is not None:
            raise ValueError(f'Cursor "{second_cursor_key}" already belongs to a pair.')

        pair_key = key or self._next_pair_key()
        if pair_key in self._cursor_pairs:
            raise ValueError(f'Cursor pair "{pair_key}" already exists.')

        pair_state = CursorPairState(
            key=pair_key,
            first_cursor_key=first_cursor_key,
            second_cursor_key=second_cursor_key,
            measurement_visible=measurement_visible,
            annotation_position=_normalized_annotation_position(annotation_position),
        )
        self._cursor_pairs[pair_key] = pair_state
        self._pair_by_cursor[first_cursor_key] = pair_key
        self._pair_by_cursor[second_cursor_key] = pair_key
        self._move_paired_cursors_together(first_cursor_key, second_cursor_key)
        return pair_key

    def remove_cursor_pair(self, pair_key: str) -> None:
        self._require_cursor_pair(pair_key)
        state = self._cursor_pairs.pop(pair_key)
        self._pair_by_cursor.pop(state.first_cursor_key, None)
        self._pair_by_cursor.pop(state.second_cursor_key, None)

    def set_cursor_pair_measurement_visible(self, pair_key: str, visible: bool) -> None:
        state = self._require_cursor_pair(pair_key)
        self._cursor_pairs[pair_key] = replace(state, measurement_visible=visible)

    def set_cursor_pair_annotation_position(self, pair_key: str, position: float) -> None:
        state = self._require_cursor_pair(pair_key)
        self._cursor_pairs[pair_key] = replace(
            state,
            annotation_position=_normalized_annotation_position(position),
        )

    def cursor_pair_state(self, pair_key: str) -> CursorPairState:
        return self._require_cursor_pair(pair_key)

    def cursor_pair_states(self) -> tuple[CursorPairState, ...]:
        positions = {key: index for index, key in enumerate(self._cursor_order)}
        return tuple(
            sorted(
                self._cursor_pairs.values(),
                key=lambda pair: positions[pair.first_cursor_key],
            )
        )

    def cursor_pair_for_cursor(self, cursor_key: str) -> CursorPairState | None:
        self._require_cursor(cursor_key)
        pair_key = self._pair_by_cursor.get(cursor_key)
        return self._cursor_pairs.get(pair_key) if pair_key is not None else None

    def set_cursor_value(self, cursor_key: str, value: float) -> None:
        state = self._require_cursor(cursor_key)
        updated = replace(state, value=_finite_float(value))
        self._cursors[cursor_key] = self._normalize_snap_state(updated)

    def set_cursor_name(self, cursor_key: str, name: str) -> None:
        state = self._require_cursor(cursor_key)
        cursor_name = str(name).strip()
        if not cursor_name:
            raise ValueError("Cursor name must not be empty.")
        self._cursors[cursor_key] = replace(state, name=cursor_name)

    def set_cursor_style(self, cursor_key: str, style: CursorStyle) -> None:
        state = self._require_cursor(cursor_key)
        self._cursors[cursor_key] = replace(state, style=style)

    def set_cursor_visible(self, cursor_key: str, visible: bool) -> None:
        state = self._require_cursor(cursor_key)
        self._cursors[cursor_key] = replace(state, visible=visible)

    def set_cursor_snap_target(
        self,
        cursor_key: str,
        target_curve_key: str | None,
    ) -> None:
        state = self._require_cursor(cursor_key)
        updated = replace(state, snap_target_curve_key=target_curve_key)
        self._cursors[cursor_key] = self._normalize_snap_state(updated)

    def set_cursor_follow_target_visibility(self, cursor_key: str, enabled: bool) -> None:
        state = self._require_cursor(cursor_key)
        if enabled and state.snap_target_curve_key is None:
            raise ValueError("Target visibility coupling requires a snap target.")
        self._cursors[cursor_key] = replace(state, follow_target_visibility=enabled)

    def set_cursor_label_visible(self, cursor_key: str, visible: bool) -> None:
        state = self._require_cursor(cursor_key)
        self._cursors[cursor_key] = replace(state, label_visible=visible)

    def effective_visible(self, cursor_key: str) -> bool:
        state = self._require_cursor(cursor_key)
        if not state.visible:
            return False
        if (
            not state.follow_target_visibility
            or state.snap_target_curve_key is None
            or self._curve_visible_provider is None
        ):
            return True
        try:
            return bool(self._curve_visible_provider(state.snap_target_curve_key))
        except KeyError:
            return True

    def target_value(self, cursor_key: str) -> float | None:
        state = self._require_cursor(cursor_key)
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

    def refresh_cursor(
        self,
        cursor_key: str,
        *,
        invalidate_curve_data: bool = True,
    ) -> None:
        state = self._require_cursor(cursor_key)
        if invalidate_curve_data and state.snap_target_curve_key is not None:
            self.invalidate_curve_data(state.snap_target_curve_key)
        self._cursors[cursor_key] = self._normalize_snap_state(state)

    def refresh_all(self) -> None:
        for curve_key in {
            state.snap_target_curve_key
            for state in self.cursor_states()
            if state.snap_target_curve_key is not None
        }:
            self.invalidate_curve_data(curve_key)
        for cursor_key in tuple(self._cursor_order):
            self.refresh_cursor(cursor_key, invalidate_curve_data=False)

    def invalidate_curve_data(self, curve_key: str) -> None:
        self._curve_data_cache.pop(curve_key, None)
        self._sorted_x_cache.pop(curve_key, None)

    def sorted_finite_x_values(self, curve_key: str) -> np.ndarray:
        cached = self._sorted_x_cache.get(curve_key)
        if cached is not None:
            return cached
        curve_data = self._curve_data(curve_key)
        if curve_data is None:
            return np.array([], dtype=float)
        x_values, _y_values = curve_data
        finite = x_values[np.isfinite(x_values)]
        sorted_values = np.unique(np.sort(finite))
        self._sorted_x_cache[curve_key] = sorted_values
        return sorted_values

    def _require_cursor(self, cursor_key: str) -> CursorState:
        try:
            return self._cursors[cursor_key]
        except KeyError as exc:
            raise KeyError(f'Cursor "{cursor_key}" does not exist.') from exc

    def _require_cursor_pair(self, pair_key: str) -> CursorPairState:
        try:
            return self._cursor_pairs[pair_key]
        except KeyError as exc:
            raise KeyError(f'Cursor pair "{pair_key}" does not exist.') from exc

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
            if key not in self._cursor_pairs:
                return key

    def _move_paired_cursors_together(self, first_cursor_key: str, second_cursor_key: str) -> None:
        self._cursor_order.remove(second_cursor_key)
        first_index = self._cursor_order.index(first_cursor_key)
        self._cursor_order.insert(first_index + 1, second_cursor_key)

    def _default_name(self, cursor_type: CursorType) -> str:
        label = "X" if cursor_type is CursorType.X else "Y"
        count = sum(
            1 for state in self._cursors.values() if state.cursor_type is cursor_type
        )
        return f"{label} Cursor {count + 1}"

    def _default_style(self) -> CursorStyle:
        color = _CURSOR_COLORS[len(self._cursor_order) % len(_CURSOR_COLORS)]
        return CursorStyle(line_color=color)

    def _default_value(self, cursor_type: CursorType) -> float:
        provider = self._x_range_provider if cursor_type is CursorType.X else self._y_range_provider
        minimum, maximum = provider() if provider is not None else (
            _DEFAULT_X_RANGE if cursor_type is CursorType.X else _DEFAULT_Y_RANGE
        )
        return _finite_float((minimum + maximum) / 2.0)

    def _normalize_snap_state(self, state: CursorState) -> CursorState:
        if state.snap_target_curve_key is None:
            if state.follow_target_visibility:
                raise ValueError("Target visibility coupling requires a snap target.")
            return state
        if state.cursor_type is not CursorType.X:
            raise ValueError("Only X cursors support snapping.")
        if not state.snap_target_curve_key:
            raise ValueError("Snapping requires a target curve key.")

        curve_data = self._curve_data(state.snap_target_curve_key)
        if curve_data is None:
            return state
        x_values, _y_values = curve_data
        finite_x_values = x_values[np.isfinite(x_values)]
        if len(finite_x_values) == 0:
            return state

        index = int(np.argmin(np.abs(finite_x_values - state.value)))
        return replace(state, value=float(finite_x_values[index]))

    def _curve_data(self, curve_key: str) -> tuple[np.ndarray, np.ndarray] | None:
        if curve_key in self._curve_data_cache:
            return self._curve_data_cache[curve_key]
        if self._curve_data_provider is None:
            return None
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
        curve_data = (x_array, y_array)
        self._curve_data_cache[curve_key] = curve_data
        return curve_data


def resolve_cursor_type(cursor_type: CursorType | str) -> CursorType:
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


def _normalized_annotation_position(value: float) -> float:
    return min(1.0, max(0.0, _finite_float(value)))
