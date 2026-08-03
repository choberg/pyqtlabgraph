from __future__ import annotations

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
        x_arrays = [
            self._curve_data_provider(curve)[0]
            for curve in self._curves_provider()
            if curve.visible
        ]
        if self._x_log_provider():
            x_arrays = [values[values > 0] for values in x_arrays if len(values) > 0]
            x_arrays = [values for values in x_arrays if len(values) > 0]
            if not x_arrays:
                return
            xmin = np.log10(min(float(np.min(values)) for values in x_arrays))
            xmax = np.log10(max(float(np.max(values)) for values in x_arrays))
        else:
            x_arrays = [values for values in x_arrays if len(values) > 0]
            if not x_arrays:
                return
            xmin = min(float(np.min(values)) for values in x_arrays)
            xmax = max(float(np.max(values)) for values in x_arrays)

        if xmin == xmax:
            xmin -= _X_AUTOSCALE_EQUAL_VALUE_MARGIN
            xmax += _X_AUTOSCALE_EQUAL_VALUE_MARGIN
        self._set_x_range(xmin, xmax)

    def _apply_x_rolling_window(self) -> None:
        x_arrays = [
            self._curve_data_provider(curve)[0]
            for curve in self._curves_provider()
            if curve.visible
        ]
        x_arrays = [values for values in x_arrays if len(values) > 0]
        if not x_arrays:
            return

        if self._x_log_provider():
            maxima = [float(np.max(values)) for values in x_arrays if np.max(values) > 0]
            if not maxima:
                return
            right = np.log10(max(maxima))
        else:
            right = max(float(np.max(values)) for values in x_arrays)
        left = right - self._rolling_window_size_provider()
        self._set_x_range(left, right)

    def _apply_y_autoscale(self) -> None:
        visible_arrays = self._visible_y_values()
        if not visible_arrays:
            for curve in self._curves_provider():
                if not curve.visible:
                    continue
                y_values = self._curve_data_provider(curve)[1]
                if len(y_values) > 0:
                    visible_arrays.append(y_values)
        if not visible_arrays:
            return

        if self._y_log_provider():
            visible_arrays = [
                values[values > 0] for values in visible_arrays if len(values) > 0
            ]
            visible_arrays = [values for values in visible_arrays if len(values) > 0]
            if not visible_arrays:
                return
            all_y = np.concatenate(visible_arrays)
            minimum = np.log10(float(all_y.min()))
            maximum = np.log10(float(all_y.max()))
        else:
            all_y = np.concatenate(visible_arrays)
            if len(all_y) == 0:
                return
            minimum = float(all_y.min())
            maximum = float(all_y.max())

        margin = (
            _Y_AUTOSCALE_EQUAL_VALUE_MARGIN
            if minimum == maximum
            else (maximum - minimum) * _Y_AUTOSCALE_MARGIN_RATIO
        )
        self._set_y_range(minimum - margin, maximum + margin)

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
