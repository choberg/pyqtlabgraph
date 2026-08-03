from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .axis import AxisMode
from .models import CursorPairState, CursorState, InteractionState
from .styles import CurveStyle, PyQtLabGraphPlotStyle
from .themes import PyQtLabGraphTheme

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


@dataclass(frozen=True)
class CurveSnapshot:
    key: str
    visible: bool
    style: CurveStyle


@dataclass(frozen=True)
class PlotSnapshot:
    """Exact layout-relevant runtime state used for rollback and replacement."""

    theme: PyQtLabGraphTheme
    plot_style: PyQtLabGraphPlotStyle
    x_label: str
    y_label: str
    x_units: str | None
    y_units: str | None
    x_mode: AxisMode
    y_mode: AxisMode
    x_log: bool
    y_log: bool
    grid_visible: bool
    antialiasing: bool
    downsampling: bool
    clip_to_view: bool
    adaptive_performance: bool
    curves: tuple[CurveSnapshot, ...]
    cursors: tuple[CursorState, ...]
    cursor_pairs: tuple[CursorPairState, ...]
    selected_cursor_keys: tuple[str, ...]
    x_range: tuple[float, float]
    y_range: tuple[float, float]
    interaction_state: InteractionState

    @classmethod
    def capture(cls, plot: PyQtLabGraphWidget) -> PlotSnapshot:
        return cls(
            theme=plot.theme,
            plot_style=plot.plot_style,
            x_label=plot.x_label_text,
            y_label=plot.y_label_text,
            x_units=plot.x_label_units,
            y_units=plot.y_label_units,
            x_mode=plot.x_axis_mode,
            y_mode=plot.y_axis_mode,
            x_log=plot.x_log,
            y_log=plot.y_log,
            grid_visible=plot.grid_visible,
            antialiasing=plot.antialiasing_enabled,
            downsampling=plot.downsampling_enabled,
            clip_to_view=plot.clip_to_view_enabled,
            adaptive_performance=plot.adaptive_performance_enabled,
            curves=tuple(
                CurveSnapshot(
                    key=key,
                    visible=plot.curve_visible(key),
                    style=plot.curve_style(key),
                )
                for key, _label in plot.curve_choices()
            ),
            cursors=plot.cursor_states(),
            cursor_pairs=plot.cursor_pair_states(),
            selected_cursor_keys=tuple(plot.selected_cursor_keys()),
            x_range=plot.get_x_range(),
            y_range=plot.get_y_range(),
            interaction_state=plot.interaction_state,
        )
