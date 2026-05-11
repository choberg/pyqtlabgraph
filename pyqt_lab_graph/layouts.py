from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .models import InteractionState, InteractionTool
from .styles import CurveStyle

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


LAYOUT_SCHEMA_VERSION = 2


class LayoutFileError(RuntimeError):
    """Raised when a PyQtLabGraph layout file cannot be read or written."""


@dataclass(frozen=True)
class PlotLayoutState:
    theme: str
    plot_style: str
    x_label: str
    y_label: str
    x_units: str | None
    y_units: str | None
    x_mode: str
    y_mode: str
    grid_visible: bool
    antialiasing: bool
    downsampling: bool
    clip_to_view: bool
    adaptive_performance: bool
    curves: dict[str, dict[str, object]]
    ranges: dict[str, tuple[float, float]]
    interaction_state: InteractionState
    restore_view_state_on_load: bool = True

    @classmethod
    def from_widget(
        cls,
        plot: PyQtLabGraphWidget,
        *,
        include_x_range: bool,
        include_y_range: bool,
        restore_view_state_on_load: bool = True,
    ) -> PlotLayoutState:
        ranges: dict[str, tuple[float, float]] = {}
        if include_x_range:
            ranges["x"] = plot.get_x_range()
        if include_y_range:
            ranges["y"] = plot.get_y_range()

        return cls(
            theme=plot.theme.name,
            plot_style=plot.plot_style.name,
            x_label=plot.x_label_text,
            y_label=plot.y_label_text,
            x_units=plot.x_label_units,
            y_units=plot.y_label_units,
            x_mode=plot.x_axis_mode.value,
            y_mode=plot.y_axis_mode.value,
            grid_visible=plot.grid_item.isVisible(),
            antialiasing=plot.antialiasing_enabled,
            downsampling=plot.downsampling_enabled,
            clip_to_view=plot.clip_to_view_enabled,
            adaptive_performance=plot.adaptive_performance_enabled,
            curves={
                key: {
                    "visible": plot.curves[key].visible,
                    "style": _curve_style_to_layout(plot.curves[key].style),
                }
                for key in plot.curve_order
            },
            ranges=ranges,
            interaction_state=InteractionState(
                autoscale_x=plot.interaction_state.autoscale_x,
                autoscale_y=plot.interaction_state.autoscale_y,
                rolling_x=plot.interaction_state.rolling_x,
                active_tool=plot.interaction_state.active_tool,
            ),
            restore_view_state_on_load=restore_view_state_on_load,
        )

    @classmethod
    def from_layout(cls, layout: dict[str, Any], plot: PyQtLabGraphWidget) -> PlotLayoutState:
        if not isinstance(layout, dict):
            raise RuntimeError("PyQtLabGraph plot layout must be an object.")

        axes = _optional_layout_object(layout, "axes")
        x_axis = _optional_layout_object(axes, "x")
        y_axis = _optional_layout_object(axes, "y")
        rendering = _optional_layout_object(layout, "rendering")
        interaction = _optional_layout_object(layout, "interaction")

        return cls(
            theme=str(layout.get("theme", plot.theme.name)),
            plot_style=str(layout.get("plot_style", plot.plot_style.name)),
            x_label=str(x_axis.get("label", plot.x_label_text)),
            y_label=str(y_axis.get("label", plot.y_label_text)),
            x_units=_layout_optional_string(x_axis.get("units", plot.x_label_units)),
            y_units=_layout_optional_string(y_axis.get("units", plot.y_label_units)),
            x_mode=str(x_axis.get("mode", plot.x_axis_mode.value)),
            y_mode=str(y_axis.get("mode", plot.y_axis_mode.value)),
            grid_visible=bool(layout.get("grid_visible", plot.grid_item.isVisible())),
            antialiasing=bool(rendering.get("antialiasing", plot.antialiasing_enabled)),
            downsampling=bool(rendering.get("downsampling", plot.downsampling_enabled)),
            clip_to_view=bool(rendering.get("clip_to_view", plot.clip_to_view_enabled)),
            adaptive_performance=bool(
                rendering.get("adaptive_performance", plot.adaptive_performance_enabled)
            ),
            curves=_curves_from_layout(_optional_layout_object(layout, "curves"), plot),
            ranges=_ranges_from_layout(_optional_layout_object(layout, "ranges")),
            interaction_state=_interaction_from_layout(interaction, plot.interaction_state),
            restore_view_state_on_load=bool(layout.get("restore_view_state_on_load", True)),
        )

    def to_layout(self) -> dict[str, Any]:
        return {
            "restore_view_state_on_load": self.restore_view_state_on_load,
            "theme": self.theme,
            "plot_style": self.plot_style,
            "axes": {
                "x": {
                    "label": self.x_label,
                    "units": self.x_units,
                    "mode": self.x_mode,
                },
                "y": {
                    "label": self.y_label,
                    "units": self.y_units,
                    "mode": self.y_mode,
                },
            },
            "grid_visible": self.grid_visible,
            "rendering": {
                "antialiasing": self.antialiasing,
                "downsampling": self.downsampling,
                "clip_to_view": self.clip_to_view,
                "adaptive_performance": self.adaptive_performance,
            },
            "interaction": {
                "autoscale_x": self.interaction_state.autoscale_x,
                "autoscale_y": self.interaction_state.autoscale_y,
                "rolling_x": self.interaction_state.rolling_x,
                "active_tool": self.interaction_state.active_tool.value,
            },
            "ranges": {
                axis: [float(values[0]), float(values[1])]
                for axis, values in self.ranges.items()
            },
            "curves": self.curves,
        }

    def apply_to_widget(
        self,
        plot: PyQtLabGraphWidget,
        *,
        restore_view_state: bool | None = None,
    ) -> None:
        plot.set_axis_labels(
            self.x_label,
            self.y_label,
            x_units=self.x_units,
            y_units=self.y_units,
            x_mode=self.x_mode,
            y_mode=self.y_mode,
        )
        plot.set_grid_visible(self.grid_visible)
        plot.set_antialiasing_enabled(self.antialiasing)
        plot.set_downsampling_enabled(self.downsampling)
        plot.set_clip_to_view_enabled(self.clip_to_view)
        plot.set_adaptive_performance_enabled(self.adaptive_performance)
        plot.set_theme(self.theme)
        plot.set_plot_style(self.plot_style)

        for key, curve_layout in self.curves.items():
            if key not in plot.curves:
                continue
            if "visible" in curve_layout:
                plot.set_curve_visible(key, bool(curve_layout["visible"]))
            if "style" in curve_layout:
                plot.set_curve_style(key, _curve_style_from_layout(key, curve_layout["style"], plot))

        should_restore_view = (
            self.restore_view_state_on_load if restore_view_state is None else restore_view_state
        )
        if should_restore_view:
            plot.interaction_state = InteractionState(
                autoscale_x=self.interaction_state.autoscale_x,
                autoscale_y=self.interaction_state.autoscale_y,
                rolling_x=self.interaction_state.rolling_x,
                active_tool=self.interaction_state.active_tool,
            )
            plot._apply_interaction_behavior()
            plot._sync_toolbar_state()
            if (
                "x" in self.ranges
                and not plot.interaction_state.autoscale_x
                and not plot.interaction_state.rolling_x
            ):
                xmin, xmax = self.ranges["x"]
                plot._set_x_range(xmin, xmax)
            if "y" in self.ranges and not plot.interaction_state.autoscale_y:
                ymin, ymax = self.ranges["y"]
                plot._set_y_range(ymin, ymax)
            plot.apply_axis_scaling()


def load_plot_layout(path: str | Path, plot_identifier: str) -> dict[str, Any] | None:
    layout_path = Path(path)
    if not layout_path.exists():
        return None

    document = _read_layout_document(layout_path)
    plot_layout = document["plots"].get(plot_identifier)
    if plot_layout is None:
        return None
    if not isinstance(plot_layout, dict):
        raise LayoutFileError(
            f'Layout entry for plot "{plot_identifier}" in {layout_path} must be an object.'
        )
    return plot_layout


def save_plot_layout(
    path: str | Path,
    plot_identifier: str,
    plot_layout: dict[str, Any],
) -> None:
    layout_path = Path(path)
    if layout_path.exists():
        document = _read_layout_document(layout_path)
    else:
        document = {"version": LAYOUT_SCHEMA_VERSION, "plots": {}}

    document["plots"][plot_identifier] = plot_layout
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        layout_path.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as exc:
        raise LayoutFileError(f"Could not write PyQtLabGraph layout file {layout_path}: {exc}") from exc


def _read_layout_document(path: Path) -> dict[str, Any]:
    try:
        raw_document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LayoutFileError(f"Could not parse PyQtLabGraph layout file {path}: {exc}") from exc
    except OSError as exc:
        raise LayoutFileError(f"Could not read PyQtLabGraph layout file {path}: {exc}") from exc

    if not isinstance(raw_document, dict):
        raise LayoutFileError(f"PyQtLabGraph layout file {path} must contain a JSON object.")
    if raw_document.get("version") != LAYOUT_SCHEMA_VERSION:
        raise LayoutFileError(
            f"Unsupported PyQtLabGraph layout file version in {path}: "
            f"{raw_document.get('version')!r}."
        )
    plots = raw_document.get("plots")
    if not isinstance(plots, dict):
        raise LayoutFileError(f'PyQtLabGraph layout file {path} must contain a "plots" object.')

    return raw_document


def _curve_style_from_layout(
    key: str,
    raw_style: object,
    plot: PyQtLabGraphWidget,
) -> CurveStyle:
    if not isinstance(raw_style, dict):
        raise RuntimeError(f'PyQtLabGraph layout style for curve "{key}" must be an object.')
    current_style = plot.curve_style(key)
    return CurveStyle(
        line_enabled=bool(raw_style.get("line_enabled", current_style.line_enabled)),
        line_color=str(raw_style.get("line_color", current_style.line_color)),
        line_width=float(raw_style.get("line_width", current_style.line_width)),
        marker_symbol=str(raw_style.get("marker_symbol", current_style.marker_symbol)),
        marker_size=int(raw_style.get("marker_size", current_style.marker_size)),
        marker_outline_width=float(
            raw_style.get("marker_outline_width", current_style.marker_outline_width)
        ),
        marker_enabled=bool(raw_style.get("marker_enabled", current_style.marker_enabled)),
        marker_filled=bool(raw_style.get("marker_filled", current_style.marker_filled)),
    )


def _curve_style_to_layout(style: CurveStyle) -> dict[str, object]:
    return {
        "line_enabled": style.line_enabled,
        "line_color": style.line_color,
        "line_width": style.line_width,
        "marker_symbol": style.marker_symbol,
        "marker_size": style.marker_size,
        "marker_outline_width": style.marker_outline_width,
        "marker_enabled": style.marker_enabled,
        "marker_filled": style.marker_filled,
    }


def _curves_from_layout(
    curves: dict[str, Any],
    plot: PyQtLabGraphWidget,
) -> dict[str, dict[str, object]]:
    parsed: dict[str, dict[str, object]] = {}
    for key, curve_layout in curves.items():
        if key not in plot.curves:
            continue
        if not isinstance(curve_layout, dict):
            raise RuntimeError(f'PyQtLabGraph layout for curve "{key}" must be an object.')
        parsed[key] = dict(curve_layout)
    return parsed


def _interaction_from_layout(
    interaction: dict[str, Any],
    current_state: InteractionState,
) -> InteractionState:
    active_tool_name = str(interaction.get("active_tool", current_state.active_tool.value))
    try:
        active_tool = InteractionTool(active_tool_name)
    except ValueError:
        active_tool = InteractionTool.NONE

    return InteractionState(
        autoscale_x=bool(interaction.get("autoscale_x", current_state.autoscale_x)),
        autoscale_y=bool(interaction.get("autoscale_y", current_state.autoscale_y)),
        rolling_x=bool(interaction.get("rolling_x", current_state.rolling_x)),
        active_tool=active_tool,
    )


def _layout_optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _optional_layout_object(layout: dict[str, Any], key: str) -> dict[str, Any]:
    raw_value = layout.get(key, {})
    if raw_value is None:
        return {}
    if not isinstance(raw_value, dict):
        raise RuntimeError(f'PyQtLabGraph layout field "{key}" must be an object.')
    return raw_value


def _range_from_layout(raw_range: object, axis_name: str) -> tuple[float, float]:
    if not isinstance(raw_range, list | tuple) or len(raw_range) != 2:
        raise RuntimeError(f'PyQtLabGraph layout range "{axis_name}" must contain two numbers.')
    try:
        first = float(raw_range[0])
        second = float(raw_range[1])
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f'PyQtLabGraph layout range "{axis_name}" must contain two numbers.'
        ) from exc
    return min(first, second), max(first, second)


def _ranges_from_layout(ranges: dict[str, Any]) -> dict[str, tuple[float, float]]:
    parsed: dict[str, tuple[float, float]] = {}
    if "x" in ranges:
        parsed["x"] = _range_from_layout(ranges["x"], "x")
    if "y" in ranges:
        parsed["y"] = _range_from_layout(ranges["y"], "y")
    return parsed
