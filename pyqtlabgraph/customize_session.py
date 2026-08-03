from __future__ import annotations

from typing import TYPE_CHECKING

from .customize_controls import CurveStyleEditor, GlobalControls, optional_text
from .runtime_state import PlotSnapshot

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


class CustomizeSession:
    """Owns Customize preview mutations and the rollback baseline."""

    def __init__(self, plot: PyQtLabGraphWidget) -> None:
        self.plot = plot
        self.baseline = self._capture_state()
        self.synced_x_range = plot.get_x_range()
        self.synced_y_range = plot.get_y_range()

    def capture_baseline(self) -> None:
        self.baseline = self._capture_state()

    def sync_ranges_from_plot(self) -> tuple[tuple[float, float], tuple[float, float]]:
        self.synced_x_range = self.plot.get_x_range()
        self.synced_y_range = self.plot.get_y_range()
        return self.synced_x_range, self.synced_y_range

    def preview_axes(self, controls: GlobalControls) -> tuple[tuple[float, float], tuple[float, float]]:
        self.plot.set_x_log(controls.x_log.isChecked())
        self.plot.set_y_log(controls.y_log.isChecked())
        self.plot.set_axis_labels(
            controls.x_label.text(),
            controls.y_label.text(),
            x_units=optional_text(controls.x_units),
            y_units=optional_text(controls.y_units),
            x_mode=controls.x_mode.currentData(),
            y_mode=controls.y_mode.currentData(),
        )
        return self.sync_ranges_from_plot()

    def preview_rendering(self, controls: GlobalControls) -> None:
        self.plot.set_grid_visible(controls.grid.isChecked())
        self.plot.set_antialiasing_enabled(controls.antialiasing.isChecked())
        self.plot.set_downsampling_enabled(controls.downsampling.isChecked())
        self.plot.set_clip_to_view_enabled(controls.clip_to_view.isChecked())
        self.plot.set_adaptive_performance_enabled(controls.adaptive_performance.isChecked())

    def preview_theme(self, controls: GlobalControls) -> None:
        self.plot.set_theme(str(controls.plot_background.currentData()))

    def preview_curve(self, key: str, editor: CurveStyleEditor) -> None:
        self.plot.set_curve_visible(key, editor.visible.isChecked())
        self.plot.set_curve_style(key, editor.curve_style())

    def preview_x_range(self, controls: GlobalControls) -> None:
        self.plot.apply_manual_x_limits(controls.x_min.value(), controls.x_max.value())
        self.synced_x_range = self.plot.get_x_range()

    def preview_y_range(self, controls: GlobalControls) -> None:
        self.plot.apply_manual_y_limits(controls.y_min.value(), controls.y_max.value())
        self.synced_y_range = self.plot.get_y_range()

    def apply_all(
        self,
        controls: GlobalControls,
        curve_editors: dict[str, CurveStyleEditor],
    ) -> None:
        self.preview_axes(controls)
        self.preview_rendering(controls)
        self.preview_theme(controls)
        self.plot.set_plot_style(str(controls.plot_style.currentData()))
        for key, editor in curve_editors.items():
            self.preview_curve(key, editor)
        requested_x = (controls.x_min.value(), controls.x_max.value())
        requested_y = (controls.y_min.value(), controls.y_max.value())
        if requested_x != self.synced_x_range:
            self.preview_x_range(controls)
        if requested_y != self.synced_y_range:
            self.preview_y_range(controls)

    def save_layout(
        self,
        controls: GlobalControls,
        curve_editors: dict[str, CurveStyleEditor],
    ) -> None:
        self.apply_all(controls, curve_editors)
        restore_view = controls.restore_view_state_on_load.isChecked()
        self.plot.save_layout(
            include_x_range=True,
            include_y_range=True,
            restore_view_state_on_load=restore_view,
        )
        self.capture_baseline()

    def rollback(self) -> None:
        self.plot.restore_snapshot(self.baseline)

    def _capture_state(self) -> PlotSnapshot:
        return PlotSnapshot.capture(self.plot)
