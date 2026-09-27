from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .customize_controls import (
    _CURVE_COLOR_KIND_ROLE,
    _CURVE_COLOR_PALETTE,
    CurveStyleEditor,
    GlobalControls,
    optional_text,
)
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
        # Last view ranges set by the dialog itself. A plot view that differs
        # from them was navigated by the user and survives Cancel.
        self._dialog_x_range = self.baseline.x_range
        self._dialog_y_range = self.baseline.y_range

    def capture_baseline(self) -> None:
        self.baseline = self._capture_state()
        self._dialog_x_range = self.baseline.x_range
        self._dialog_y_range = self.baseline.y_range

    def sync_ranges_from_plot(self) -> tuple[tuple[float, float], tuple[float, float]]:
        self.synced_x_range = self.plot.get_x_range()
        self.synced_y_range = self.plot.get_y_range()
        return self.synced_x_range, self.synced_y_range

    def preview_axes(
        self, controls: GlobalControls
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        before = self._view()
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
        self._track_dialog_view(before)
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
        before = self._view()
        self.plot.apply_manual_x_limits(controls.x_min.value(), controls.x_max.value())
        self.synced_x_range = self.plot.get_x_range()
        self._track_dialog_view(before)

    def preview_y_range(self, controls: GlobalControls) -> None:
        before = self._view()
        self.plot.apply_manual_y_limits(controls.y_min.value(), controls.y_max.value())
        self.synced_y_range = self.plot.get_y_range()
        self._track_dialog_view(before)

    def apply_all(
        self,
        controls: GlobalControls,
        curve_editors: dict[str, CurveStyleEditor],
    ) -> None:
        requested_x = (controls.x_min.value(), controls.x_max.value())
        requested_y = (controls.y_min.value(), controls.y_max.value())
        x_edited = requested_x != self.synced_x_range
        y_edited = requested_y != self.synced_y_range
        self.preview_axes(controls)
        self.preview_rendering(controls)
        self.preview_theme(controls)
        kind = controls.curve_colors.currentData(_CURVE_COLOR_KIND_ROLE)
        if kind == _CURVE_COLOR_PALETTE:
            palette_name = controls.curve_colors.currentData()
            self.plot.set_curve_palette(
                str(palette_name),
                reverse=controls.curve_color_reverse.isChecked(),
            )
        for key, editor in curve_editors.items():
            self.preview_curve(key, editor)
            self.plot.set_curve_persistence(key, editor.persistence_config())
        if x_edited:
            self.preview_x_range(controls)
        if y_edited:
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
        """Undo dialog edits while keeping view navigation done in the plot."""
        current = self._capture_state()
        keep_x = current.x_range != self._dialog_x_range and current.x_log == self.baseline.x_log
        keep_y = current.y_range != self._dialog_y_range and current.y_log == self.baseline.y_log
        target = self.baseline
        if keep_x or keep_y:
            target = replace(
                target,
                interaction_state=current.interaction_state,
                x_range=current.x_range if keep_x else target.x_range,
                y_range=current.y_range if keep_y else target.y_range,
            )
        self.plot.restore_snapshot(target)

    def _view(self) -> tuple[tuple[float, float], tuple[float, float]]:
        return self.plot.get_x_range(), self.plot.get_y_range()

    def _track_dialog_view(self, before: tuple[tuple[float, float], tuple[float, float]]) -> None:
        """Mark axes whose view the dialog changed as dialog-owned."""
        x_range, y_range = self._view()
        if x_range != before[0]:
            self._dialog_x_range = x_range
        if y_range != before[1]:
            self._dialog_y_range = y_range

    def _capture_state(self) -> PlotSnapshot:
        return PlotSnapshot.capture(self.plot)
