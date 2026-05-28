from __future__ import annotations

from typing import TYPE_CHECKING, Callable

import numpy as np


if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


from .constants import (
    _X_AUTOSCALE_EQUAL_VALUE_MARGIN,
    _Y_AUTOSCALE_EQUAL_VALUE_MARGIN,
    _Y_AUTOSCALE_MARGIN_RATIO,
    _RANGE_PADDING,
)


class RangeController:
    """Encapsulates the math and logic for axis limits, Autoscale, and Rolling-Windows."""

    def __init__(self, widget: PyQtLabGraphWidget) -> None:
        self._widget = widget

    def apply_axis_scaling(self) -> None:
        state = self._widget.interaction_state
        if state.autoscale_x:
            self._apply_x_autoscale()
        elif state.rolling_x:
            self._apply_x_rolling_window()
        if state.autoscale_y:
            self._apply_y_autoscale()
        self._widget.render_optimizer.update_adaptive_performance()

    def get_x_range(self) -> tuple[float, float]:
        xmin, xmax = self._widget.view_box.viewRange()[0]
        return float(xmin), float(xmax)

    def get_y_range(self) -> tuple[float, float]:
        ymin, ymax = self._widget.view_box.viewRange()[1]
        return float(ymin), float(ymax)

    def apply_manual_x_limits(self, xmin: float, xmax: float) -> None:
        self._widget.interaction_state.autoscale_x = False
        self._widget.interaction_state.rolling_x = False
        self._widget._sync_toolbar_state()
        self._set_x_range(min(xmin, xmax), max(xmin, xmax))
        self._widget.render_optimizer.update_adaptive_performance()

    def apply_manual_y_limits(self, ymin: float, ymax: float) -> None:
        self._widget.interaction_state.autoscale_y = False
        self._widget._sync_toolbar_state()
        self._set_y_range(min(ymin, ymax), max(ymin, ymax))

    def _apply_x_autoscale(self) -> None:
        x_arrays = [
            self._widget.curve_manager.get_curve_data(curve)[0]
            for curve in self._widget.curve_manager.curves.values()
            if curve.visible
        ]
        x_arrays = [arr for arr in x_arrays if len(arr) > 0]
        if not x_arrays:
            return
        
        min_vals = [float(np.min(arr)) for arr in x_arrays]
        max_vals = [float(np.max(arr)) for arr in x_arrays]
        xmin = min(min_vals)
        xmax = max(max_vals)
        
        if xmin == xmax:
            xmin -= _X_AUTOSCALE_EQUAL_VALUE_MARGIN
            xmax += _X_AUTOSCALE_EQUAL_VALUE_MARGIN
        self._set_x_range(xmin, xmax)

    def _apply_x_rolling_window(self) -> None:
        x_arrays = [
            self._widget.curve_manager.get_curve_data(curve)[0]
            for curve in self._widget.curve_manager.curves.values()
            if curve.visible
        ]
        x_arrays = [arr for arr in x_arrays if len(arr) > 0]
        if not x_arrays:
            return
        
        max_vals = [float(np.max(arr)) for arr in x_arrays]
        latest_x = max(max_vals)
        right = latest_x
        left = right - self._widget.rolling_window_size
        self._set_x_range(left, right)

    def _apply_y_autoscale(self) -> None:
        visible_arrays = self._visible_y_values()
        if not visible_arrays:
            for curve in self._widget.curve_manager.curves.values():
                if curve.visible:
                    y_arr = self._widget.curve_manager.get_curve_data(curve)[1]
                    if len(y_arr) > 0:
                        visible_arrays.append(y_arr)
        if not visible_arrays:
            return
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
        for curve in self._widget.curve_manager.curves.values():
            if not curve.visible:
                continue
            x_values, y_values = self._widget.curve_manager.get_curve_data(curve)
            if len(x_values) == 0:
                continue
            mask = (x_values >= xmin) & (x_values <= xmax)
            visible_y = y_values[mask]
            if len(visible_y) > 0:
                arrays.append(visible_y)
        return arrays

    def set_x_range(self, xmin: float, xmax: float) -> None:
        """Sets the X axis range without triggering user-interaction handlers."""
        self._set_x_range(xmin, xmax)

    def set_y_range(self, ymin: float, ymax: float) -> None:
        """Sets the Y axis range without triggering user-interaction handlers."""
        self._set_y_range(ymin, ymax)

    def _set_x_range(self, xmin: float, xmax: float) -> None:
        self._set_range(
            lambda: self._widget.plot_item.setXRange(xmin, xmax, padding=_RANGE_PADDING)
        )

    def _set_y_range(self, ymin: float, ymax: float) -> None:
        self._set_range(
            lambda: self._widget.plot_item.setYRange(ymin, ymax, padding=_RANGE_PADDING)
        )

    def _set_range(self, setter: Callable[[], None]) -> None:
        # Set the applying_axis_scaling flag to prevent recursive scaling and range updates.
        self._widget.applying_axis_scaling = True
        try:
            setter()
        finally:
            self._widget.applying_axis_scaling = False
