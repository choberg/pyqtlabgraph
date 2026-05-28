from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget
    from .models import CurveState

from .constants import (
    _ADAPTIVE_PERFORMANCE_THRESHOLD,
    _ADAPTIVE_PERFORMANCE_RESTORE_THRESHOLD,
)


class RenderOptimizer:
    """Manages Adaptive Performance and rendering flags."""

    def __init__(self, widget: PyQtLabGraphWidget) -> None:
        self._widget = widget
        self.enabled = True
        self.active = False
        self.threshold = _ADAPTIVE_PERFORMANCE_THRESHOLD
        self.restore_threshold = _ADAPTIVE_PERFORMANCE_RESTORE_THRESHOLD
        self.antialiasing_enabled = True
        self.downsampling_enabled = True
        self.clip_to_view_enabled = True

    def set_adaptive_performance_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.update_adaptive_performance(force=True)

    def effective_antialiasing_enabled(self) -> bool:
        return self.antialiasing_enabled and not self.active

    def marker_cache_enabled(self) -> bool:
        # Evaluate decoupling later as noted in roadmap, but for now replicate behavior
        return self.effective_antialiasing_enabled()

    def update_adaptive_performance(self, *, force: bool = False) -> None:
        """Toggle expensive visual details when a dense view is visible."""
        active = self.active
        if not self.enabled:
            active = False
        else:
            visible_points = self._visible_data_point_count()
            if active:
                active = visible_points >= self.restore_threshold
            else:
                active = visible_points >= self.threshold

        if not force and active == self.active:
            return

        self.active = active
        self._widget.plot_widget.setAntialiasing(self.effective_antialiasing_enabled())
        for curve in self._widget.curve_manager.curves.values():
            self.apply_curve_rendering_options(curve)
            self._widget.style_controller.apply_curve_style(curve)

    def _visible_data_point_count(self) -> int:
        xmin, xmax = self._widget.get_x_range()
        count = 0
        for curve in self._widget.curve_manager.curves.values():
            if not curve.visible:
                continue
            x_values, _y_values = self._widget.curve_manager.get_curve_data(curve)
            count += int(np.count_nonzero((xmin <= x_values) & (x_values <= xmax)))
        return count

    def set_antialiasing_enabled(self, enabled: bool) -> None:
        self.antialiasing_enabled = enabled
        self._widget.plot_widget.setAntialiasing(self.effective_antialiasing_enabled())
        for curve in self._widget.curve_manager.curves.values():
            self.apply_curve_rendering_options(curve)

    def set_downsampling_enabled(self, enabled: bool) -> None:
        self.downsampling_enabled = enabled
        for curve in self._widget.curve_manager.curves.values():
            self.apply_curve_rendering_options(curve)

    def set_clip_to_view_enabled(self, enabled: bool) -> None:
        self.clip_to_view_enabled = enabled
        for curve in self._widget.curve_manager.curves.values():
            self.apply_curve_rendering_options(curve)

    def apply_curve_rendering_options(self, curve: CurveState) -> None:
        antialias = self.effective_antialiasing_enabled()
        curve.item.setClipToView(self.clip_to_view_enabled)
        curve.item.setDownsampling(auto=self.downsampling_enabled, method="peak")
        curve.item.opts["antialias"] = antialias
        curve.item.opts["useCache"] = self.marker_cache_enabled()
        curve.item.updateItems(styleUpdate=True)
