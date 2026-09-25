from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np
import pyqtgraph as pg

from .constants import (
    _RANGE_PADDING,
    _X_AUTOSCALE_EQUAL_VALUE_MARGIN,
    _Y_AUTOSCALE_EQUAL_VALUE_MARGIN,
    _Y_AUTOSCALE_MARGIN_RATIO,
)
from .models import CurveState, InteractionState

CurveProvider = Callable[[], Sequence[CurveState]]
CurveDataProvider = Callable[[CurveState], tuple[np.ndarray, np.ndarray]]


class RangeController:
    """Calculates and applies plot ranges from explicit read-only providers."""

    def __init__(
        self,
        *,
        view_box: pg.ViewBox,
        curves_provider: CurveProvider,
        curve_data_provider: CurveDataProvider,
        interaction_state_provider: Callable[[], InteractionState],
        x_log_provider: Callable[[], bool],
        y_log_provider: Callable[[], bool],
        rolling_window_size_provider: Callable[[], float],
    ) -> None:
        self._view_box = view_box
        self._curves_provider = curves_provider
        self._curve_data_provider = curve_data_provider
        self._interaction_state_provider = interaction_state_provider
        self._x_log_provider = x_log_provider
        self._y_log_provider = y_log_provider
        self._rolling_window_size_provider = rolling_window_size_provider
        self.applying_range = False

    def apply_axis_scaling(self) -> None:
        state = self._interaction_state_provider()
        if state.autoscale_x:
            self._apply_x_autoscale()
        elif state.rolling_x:
            self._apply_x_rolling_window()
        if state.autoscale_y:
            self._apply_y_autoscale()

    def get_x_range(self) -> tuple[float, float]:
        xmin, xmax = self._view_box.viewRange()[0]
        return float(xmin), float(xmax)

    def get_y_range(self) -> tuple[float, float]:
        ymin, ymax = self._view_box.viewRange()[1]
        return float(ymin), float(ymax)

    def apply_manual_x_limits(self, xmin: float, xmax: float) -> None:
        self._set_x_range(min(xmin, xmax), max(xmin, xmax))

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        self._set_y_range(min(ymin, ymax), max(ymin, ymax))

    def _apply_x_autoscale(self) -> None:
        bounds = _finite_bounds(self._visible_values(0), log=self._x_log_provider())
        if bounds is None:
            return
        xmin, xmax = bounds
        if xmin == xmax:
            xmin -= _X_AUTOSCALE_EQUAL_VALUE_MARGIN
            xmax += _X_AUTOSCALE_EQUAL_VALUE_MARGIN
        self._set_x_range(xmin, xmax)

    def _apply_x_rolling_window(self) -> None:
        bounds = _finite_bounds(self._visible_values(0), log=self._x_log_provider())
        if bounds is None:
            return
        right = bounds[1]
        self._set_x_range(right - self._rolling_window_size_provider(), right)

    def _apply_y_autoscale(self) -> None:
        log = self._y_log_provider()
        bounds = _finite_bounds(self._visible_y_values(), log=log)
        if bounds is None:
            bounds = _finite_bounds(self._visible_values(1), log=log)
        if bounds is None:
            return
        minimum, maximum = bounds
        margin = (
            _Y_AUTOSCALE_EQUAL_VALUE_MARGIN
            if minimum == maximum
            else (maximum - minimum) * _Y_AUTOSCALE_MARGIN_RATIO
        )
        self._set_y_range(minimum - margin, maximum + margin)

    def _visible_values(self, axis: int) -> list[np.ndarray]:
        return [
            self._curve_data_provider(curve)[axis]
            for curve in self._curves_provider()
            if curve.visible
        ]

    def _visible_y_values(self) -> list[np.ndarray]:
        xmin, xmax = self.get_x_range()
        arrays: list[np.ndarray] = []
        for curve in self._curves_provider():
            if not curve.visible:
                continue
            x_values, y_values = self._curve_data_provider(curve)
            if len(x_values) == 0:
                continue
            if self._x_log_provider():
                raw_xmin = 10**xmin
                raw_xmax = 10**xmax
                mask = (x_values >= raw_xmin) & (x_values <= raw_xmax)
            else:
                mask = (x_values >= xmin) & (x_values <= xmax)
            visible_y = y_values[mask]
            if len(visible_y) > 0:
                arrays.append(visible_y)
        return arrays

    def set_x_range(self, xmin: float, xmax: float) -> None:
        """Set the X range without invoking user-navigation handling."""
        self._set_x_range(xmin, xmax)

    def set_y_range(self, ymin: float, ymax: float) -> None:
        """Set the Y range without invoking user-navigation handling."""
        self._set_y_range(ymin, ymax)

    def _set_x_range(self, xmin: float, xmax: float) -> None:
        self._set_range(
            lambda: self._view_box.setXRange(xmin, xmax, padding=_RANGE_PADDING)
        )

    def _set_y_range(self, ymin: float, ymax: float) -> None:
        self._set_range(
            lambda: self._view_box.setYRange(ymin, ymax, padding=_RANGE_PADDING)
        )

    def _set_range(self, setter: Callable[[], None]) -> None:
        self.applying_range = True
        try:
            setter()
        finally:
            self.applying_range = False


def _finite_bounds(arrays: Sequence[np.ndarray], *, log: bool) -> tuple[float, float] | None:
    """Return finite data bounds in view coordinates, ignoring NaN and Inf."""
    minimum = math.inf
    maximum = -math.inf
    for values in arrays:
        values = np.asarray(values, dtype=float)
        valid = values[np.isfinite(values) & (values > 0)] if log else values[np.isfinite(values)]
        if len(valid) > 0:
            minimum = min(minimum, float(valid.min()))
            maximum = max(maximum, float(valid.max()))
    if minimum > maximum:
        return None
    if log:
        return math.log10(minimum), math.log10(maximum)
    return minimum, maximum
