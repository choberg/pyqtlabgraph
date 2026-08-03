from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pyqtgraph as pg

from .constants import (
    _ADAPTIVE_PERFORMANCE_RESTORE_THRESHOLD,
    _ADAPTIVE_PERFORMANCE_THRESHOLD,
)
from .models import CurveState


class RenderOptimizer:
    """Owns rendering flags and adaptive-performance policy."""

    def __init__(
        self,
        *,
        plot_widget: pg.PlotWidget,
        curves_provider: Callable[[], Sequence[CurveState]],
        curve_data_provider: Callable[[CurveState], tuple[np.ndarray, np.ndarray]],
        x_range_provider: Callable[[], tuple[float, float]],
        x_log_provider: Callable[[], bool],
    ) -> None:
        self._plot_widget = plot_widget
        self._curves_provider = curves_provider
        self._curve_data_provider = curve_data_provider
        self._x_range_provider = x_range_provider
        self._x_log_provider = x_log_provider
        self.enabled = True
        self.active = False
        self.threshold = _ADAPTIVE_PERFORMANCE_THRESHOLD
        self.restore_threshold = _ADAPTIVE_PERFORMANCE_RESTORE_THRESHOLD
        self.antialiasing_enabled = True
        self.downsampling_enabled = True
        self.clip_to_view_enabled = True

    def set_adaptive_performance_enabled(self, enabled: bool) -> bool:
        self.enabled = enabled
        return self.update_adaptive_performance(force=True)

    def effective_antialiasing_enabled(self) -> bool:
        return self.antialiasing_enabled and not self.active

    def marker_cache_enabled(self) -> bool:
        return self.effective_antialiasing_enabled()

    def update_adaptive_performance(self, *, force: bool = False) -> bool:
        """Apply rendering options and report whether adaptive mode changed."""
        previous_active = self.active
        active = previous_active
        if not self.enabled:
            active = False
        else:
            visible_points = self._visible_data_point_count()
            if active:
                active = visible_points >= self.restore_threshold
            else:
                active = visible_points >= self.threshold

        mode_changed = active != previous_active
        if not force and not mode_changed:
            return False

        self.active = active
        self._plot_widget.setAntialiasing(self.effective_antialiasing_enabled())
        for curve in self._curves_provider():
            self.apply_curve_rendering_options(curve)
        return mode_changed

    def _visible_data_point_count(self) -> int:
        xmin, xmax = self._x_range_provider()
        count = 0
        for curve in self._curves_provider():
            if not curve.visible:
                continue
            x_values, _y_values = self._curve_data_provider(curve)
            count += int(np.count_nonzero(self._visible_x_mask(x_values, xmin, xmax)))
        return count

    def _visible_x_mask(
        self,
        x_values: np.ndarray,
        xmin: float,
        xmax: float,
    ) -> np.ndarray:
        if self._x_log_provider():
            xmin = 10**xmin
            xmax = 10**xmax
        return (xmin <= x_values) & (x_values <= xmax)

    def set_antialiasing_enabled(self, enabled: bool) -> None:
        self.antialiasing_enabled = enabled
        self._plot_widget.setAntialiasing(self.effective_antialiasing_enabled())
        for curve in self._curves_provider():
            self.apply_curve_rendering_options(curve)

    def set_downsampling_enabled(self, enabled: bool) -> None:
        self.downsampling_enabled = enabled
        for curve in self._curves_provider():
            self.apply_curve_rendering_options(curve)

    def set_clip_to_view_enabled(self, enabled: bool) -> None:
        self.clip_to_view_enabled = enabled
        for curve in self._curves_provider():
            self.apply_curve_rendering_options(curve)

    def apply_curve_rendering_options(self, curve: CurveState) -> None:
        antialias = self.effective_antialiasing_enabled()
        curve.item.setClipToView(self.clip_to_view_enabled)
        curve.item.setDownsampling(auto=self.downsampling_enabled, method="peak")
        curve.item.opts["antialias"] = antialias
        curve.item.opts["useCache"] = self.marker_cache_enabled()
        curve.item.updateItems(styleUpdate=True)
