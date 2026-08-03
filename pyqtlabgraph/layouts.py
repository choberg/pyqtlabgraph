from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .axis import AxisMode, resolve_axis_mode
from .models import (
    CursorLineStyle,
    CursorPairState,
    CursorState,
    CursorStyle,
    CursorType,
    InteractionState,
    InteractionTool,
)
from .runtime_state import CurveSnapshot, PlotSnapshot
from .styles import CurveStyle

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


LAYOUT_FORMAT_VERSION = 1

_DOCUMENT_FIELDS = frozenset({"version", "plots"})
_PLOT_FIELDS = frozenset(
    {
        "restore_view_state_on_load",
        "theme",
        "plot_style",
        "axes",
        "grid_visible",
        "rendering",
        "interaction",
        "ranges",
        "curves",
        "cursors",
        "cursor_pairs",
    }
)
_AXES_FIELDS = frozenset({"x", "y"})
_AXIS_FIELDS = frozenset({"label", "units", "mode", "log"})
_RENDERING_FIELDS = frozenset(
    {"antialiasing", "downsampling", "clip_to_view", "adaptive_performance"}
)
_INTERACTION_FIELDS = frozenset(
    {"autoscale_x", "autoscale_y", "rolling_x", "active_tool"}
)
_RANGE_FIELDS = frozenset({"x", "y"})
_CURVE_FIELDS = frozenset({"visible", "style"})
_CURVE_STYLE_FIELDS = frozenset(
    {
        "line_enabled",
        "line_color",
        "line_width",
        "marker_symbol",
        "marker_size",
        "marker_outline_width",
        "marker_enabled",
        "marker_filled",
    }
)
_CURSOR_FIELDS = frozenset(
    {
        "key",
        "name",
        "type",
        "value",
        "visible",
        "style",
        "snap_target_curve_key",
        "follow_target_visibility",
        "label_visible",
    }
)
_CURSOR_STYLE_FIELDS = frozenset({"line_color", "line_width", "line_style"})
_CURSOR_PAIR_FIELDS = frozenset(
    {"key", "members", "measurement_visible", "annotation_position"}
)


class LayoutFileError(RuntimeError):
    """Raised when a PyQtLabGraph layout file is invalid or cannot be accessed."""


@dataclass(frozen=True)
class AxisLayoutState:
    label: str
    units: str | None
    mode: AxisMode
    log: bool


@dataclass(frozen=True)
class RenderingLayoutState:
    antialiasing: bool
    downsampling: bool
    clip_to_view: bool
    adaptive_performance: bool


@dataclass(frozen=True)
class CurveLayoutState:
    visible: bool
    style: CurveStyle


@dataclass(frozen=True)
class CursorLayoutState:
    key: str
    name: str
    cursor_type: CursorType
    value: float
    visible: bool
    style: CursorStyle
    snap_target_curve_key: str | None
    follow_target_visibility: bool
    label_visible: bool


@dataclass(frozen=True)
class CursorPairLayoutState:
    key: str
    first_cursor_key: str
    second_cursor_key: str
    measurement_visible: bool
    annotation_position: float


@dataclass(frozen=True)
class PlotLayoutState:
    restore_view_state_on_load: bool
    theme: str
    plot_style: str
    x_axis: AxisLayoutState
    y_axis: AxisLayoutState
    grid_visible: bool
    rendering: RenderingLayoutState
    interaction_state: InteractionState
    ranges: dict[str, tuple[float, float]]
    curves: dict[str, CurveLayoutState]
    cursors: tuple[CursorLayoutState, ...]
    cursor_pairs: tuple[CursorPairLayoutState, ...]


@dataclass(frozen=True)
class LayoutDocument:
    version: int
    plots: dict[str, PlotLayoutState]


def decode_layout_document(source: str) -> LayoutDocument:
    """Decode and validate a complete layout document without a Qt application."""
    try:
        raw = json.loads(
            source,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except LayoutFileError:
        raise
    except json.JSONDecodeError as exc:
        raise LayoutFileError(f"Malformed PyQtLabGraph layout JSON: {exc}") from exc
    return _parse_document(raw)


def encode_layout_document(document: LayoutDocument) -> str:
    if document.version != LAYOUT_FORMAT_VERSION:
        raise LayoutFileError(
            "Cannot encode PyQtLabGraph layout file version "
            f"{document.version!r}; version {LAYOUT_FORMAT_VERSION} is required."
        )
    raw = {
        "version": document.version,
        "plots": {
            identifier: _plot_layout_to_mapping(layout)
            for identifier, layout in document.plots.items()
        },
    }
    return json.dumps(raw, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_plot_layout(
    path: str | Path,
    plot_identifier: str,
) -> PlotLayoutState | None:
    layout_path = Path(path)
    if not layout_path.exists():
        return None
    document = _read_layout_document(layout_path)
    return document.plots.get(plot_identifier)


def save_plot_layout(
    path: str | Path,
    plot_identifier: str,
    plot_layout: PlotLayoutState,
) -> None:
    if not isinstance(plot_identifier, str) or not plot_identifier.strip():
        raise LayoutFileError("PyQtLabGraph plot identifier must not be empty.")
    layout_path = Path(path)
    document = (
        _read_layout_document(layout_path)
        if layout_path.exists()
        else LayoutDocument(version=LAYOUT_FORMAT_VERSION, plots={})
    )
    plots = dict(document.plots)
    plots[plot_identifier] = plot_layout
    encoded = encode_layout_document(
        LayoutDocument(version=LAYOUT_FORMAT_VERSION, plots=plots)
    )
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(
            dir=str(layout_path.parent),
            suffix=".tmp",
        )
        temporary = Path(name)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(encoded)
        os.replace(name, layout_path)
    except Exception as exc:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise LayoutFileError(
            f"Could not write PyQtLabGraph layout file {layout_path}: {exc}"
        ) from exc


def capture_plot_layout(
    plot: PyQtLabGraphWidget,
    *,
    include_x_range: bool,
    include_y_range: bool,
    restore_view_state_on_load: bool = True,
) -> PlotLayoutState:
    snapshot = PlotSnapshot.capture(plot)
    ranges: dict[str, tuple[float, float]] = {}
    if include_x_range:
        ranges["x"] = snapshot.x_range
    if include_y_range:
        ranges["y"] = snapshot.y_range
    return PlotLayoutState(
        restore_view_state_on_load=restore_view_state_on_load,
        theme=snapshot.theme.name,
        plot_style=snapshot.plot_style.name,
        x_axis=AxisLayoutState(
            snapshot.x_label,
            snapshot.x_units,
            snapshot.x_mode,
            snapshot.x_log,
        ),
        y_axis=AxisLayoutState(
            snapshot.y_label,
            snapshot.y_units,
            snapshot.y_mode,
            snapshot.y_log,
        ),
        grid_visible=snapshot.grid_visible,
        rendering=RenderingLayoutState(
            antialiasing=snapshot.antialiasing,
            downsampling=snapshot.downsampling,
            clip_to_view=snapshot.clip_to_view,
            adaptive_performance=snapshot.adaptive_performance,
        ),
        interaction_state=snapshot.interaction_state,
        ranges=ranges,
        curves={
            curve.key: CurveLayoutState(curve.visible, curve.style)
            for curve in snapshot.curves
        },
        cursors=tuple(
            CursorLayoutState(
                key=cursor.key,
                name=cursor.name,
                cursor_type=cursor.cursor_type,
                value=cursor.value,
                visible=cursor.visible,
                style=cursor.style,
                snap_target_curve_key=cursor.snap_target_curve_key,
                follow_target_visibility=cursor.follow_target_visibility,
                label_visible=cursor.label_visible,
            )
            for cursor in snapshot.cursors
        ),
        cursor_pairs=tuple(
            CursorPairLayoutState(
                key=pair.key,
                first_cursor_key=pair.first_cursor_key,
                second_cursor_key=pair.second_cursor_key,
                measurement_visible=pair.measurement_visible,
                annotation_position=pair.annotation_position,
            )
            for pair in snapshot.cursor_pairs
        ),
    )


def apply_plot_layout(
    plot: PyQtLabGraphWidget,
    layout: PlotLayoutState,
    *,
    restore_view_state: bool | None = None,
) -> None:
    """Reconcile a validated layout and replace widget state atomically."""
    restore_view = (
        layout.restore_view_state_on_load
        if restore_view_state is None
        else restore_view_state
    )
    target = _reconcile_layout(plot, layout, restore_view=restore_view)
    plot.restore_snapshot(target)


def _reconcile_layout(
    plot: PyQtLabGraphWidget,
    layout: PlotLayoutState,
    *,
    restore_view: bool,
) -> PlotSnapshot:
    current = PlotSnapshot.capture(plot)
    try:
        theme = plot.style_registry.resolve_theme(layout.theme)
        plot_style = plot.style_registry.resolve_plot_style(layout.plot_style)
    except ValueError as exc:
        raise LayoutFileError(str(exc)) from exc

    curves = tuple(
        CurveSnapshot(
            key=state.key,
            visible=(
                layout.curves[state.key].visible
                if state.key in layout.curves
                else state.visible
            ),
            style=(
                layout.curves[state.key].style
                if state.key in layout.curves
                else state.style
            ),
        )
        for state in current.curves
    )
    curve_keys = {state.key for state in current.curves}
    cursors = tuple(
        _cursor_layout_to_state(state, curve_keys)
        for state in layout.cursors
    )
    pairs = tuple(
        CursorPairState(
            key=state.key,
            first_cursor_key=state.first_cursor_key,
            second_cursor_key=state.second_cursor_key,
            measurement_visible=state.measurement_visible,
            annotation_position=state.annotation_position,
        )
        for state in layout.cursor_pairs
    )

    interaction = (
        layout.interaction_state if restore_view else current.interaction_state
    )
    x_range = current.x_range
    y_range = current.y_range
    if restore_view:
        if (
            "x" in layout.ranges
            and not interaction.autoscale_x
            and not interaction.rolling_x
        ):
            x_range = layout.ranges["x"]
        if "y" in layout.ranges and not interaction.autoscale_y:
            y_range = layout.ranges["y"]

    return PlotSnapshot(
        theme=theme,
        plot_style=plot_style,
        x_label=layout.x_axis.label,
        y_label=layout.y_axis.label,
        x_units=layout.x_axis.units,
        y_units=layout.y_axis.units,
        x_mode=layout.x_axis.mode,
        y_mode=layout.y_axis.mode,
        x_log=layout.x_axis.log,
        y_log=layout.y_axis.log,
        grid_visible=layout.grid_visible,
        antialiasing=layout.rendering.antialiasing,
        downsampling=layout.rendering.downsampling,
        clip_to_view=layout.rendering.clip_to_view,
        adaptive_performance=layout.rendering.adaptive_performance,
        curves=curves,
        cursors=cursors,
        cursor_pairs=pairs,
        selected_cursor_keys=(),
        x_range=x_range,
        y_range=y_range,
        interaction_state=interaction,
    )


def _cursor_layout_to_state(
    state: CursorLayoutState,
    curve_keys: set[str],
) -> CursorState:
    target = state.snap_target_curve_key
    if target is not None and target not in curve_keys:
        raise LayoutFileError(
            f'Cursor "{state.key}" refers to unknown snap target curve "{target}".'
        )
    return CursorState(
        key=state.key,
        name=state.name,
        cursor_type=state.cursor_type,
        value=state.value,
        visible=state.visible,
        style=state.style,
        snap_target_curve_key=target,
        follow_target_visibility=state.follow_target_visibility,
        label_visible=state.label_visible,
    )


def _read_layout_document(path: Path) -> LayoutDocument:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LayoutFileError(
            f"Could not read PyQtLabGraph layout file {path}: {exc}"
        ) from exc
    try:
        return decode_layout_document(source)
    except LayoutFileError as exc:
        raise LayoutFileError(
            f"Could not read PyQtLabGraph layout file {path}: {exc}"
        ) from exc


def _parse_document(raw: object) -> LayoutDocument:
    document = _mapping(raw, "PyQtLabGraph layout document")
    _validate_fields(document, _DOCUMENT_FIELDS, "PyQtLabGraph layout document")
    version = document["version"]
    if type(version) is not int or version != LAYOUT_FORMAT_VERSION:
        raise LayoutFileError(
            "Unsupported PyQtLabGraph layout file version: "
            f"{version!r}; version {LAYOUT_FORMAT_VERSION} is required."
        )
    plots_raw = _mapping(
        document["plots"],
        'PyQtLabGraph layout field "plots"',
    )
    plots: dict[str, PlotLayoutState] = {}
    for identifier, value in plots_raw.items():
        if not isinstance(identifier, str) or not identifier.strip():
            raise LayoutFileError("Layout plot identifiers must not be empty.")
        plots[identifier] = _parse_plot_layout(
            _mapping(value, f'layout entry for plot "{identifier}"')
        )
    return LayoutDocument(version=version, plots=plots)


def _parse_plot_layout(raw: dict[str, Any]) -> PlotLayoutState:
    _validate_fields(raw, _PLOT_FIELDS, "plot layout")
    axes = _mapping(raw["axes"], 'layout field "axes"')
    _validate_fields(axes, _AXES_FIELDS, 'layout field "axes"')
    rendering = _mapping(
        raw["rendering"],
        'layout field "rendering"',
    )
    _validate_fields(rendering, _RENDERING_FIELDS, 'layout field "rendering"')
    interaction = _mapping(
        raw["interaction"],
        'layout field "interaction"',
    )
    _validate_fields(interaction, _INTERACTION_FIELDS, 'layout field "interaction"')
    cursors = _parse_cursors(raw["cursors"])
    pairs = _parse_pairs(raw["cursor_pairs"])
    _validate_saved_pair_members(pairs, cursors)
    return PlotLayoutState(
        restore_view_state_on_load=_boolean(raw, "restore_view_state_on_load"),
        theme=_non_empty_string(raw["theme"], 'layout field "theme"'),
        plot_style=_non_empty_string(
            raw["plot_style"],
            'layout field "plot_style"',
        ),
        x_axis=_parse_axis(
            _mapping(axes["x"], 'layout axis "x"'),
            axis="x",
        ),
        y_axis=_parse_axis(
            _mapping(axes["y"], 'layout axis "y"'),
            axis="y",
        ),
        grid_visible=_boolean(raw, "grid_visible"),
        rendering=RenderingLayoutState(
            antialiasing=_boolean(rendering, "antialiasing"),
            downsampling=_boolean(rendering, "downsampling"),
            clip_to_view=_boolean(rendering, "clip_to_view"),
            adaptive_performance=_boolean(rendering, "adaptive_performance"),
        ),
        interaction_state=_parse_interaction(interaction),
        ranges=_parse_ranges(
            _mapping(raw["ranges"], 'layout field "ranges"')
        ),
        curves=_parse_curves(
            _mapping(raw["curves"], 'layout field "curves"')
        ),
        cursors=cursors,
        cursor_pairs=pairs,
    )


def _parse_axis(raw: dict[str, Any], *, axis: str) -> AxisLayoutState:
    owner = f'layout axis "{axis}"'
    _validate_fields(raw, _AXIS_FIELDS, owner)
    mode_value = _non_empty_string(
        raw["mode"],
        f'layout axis "{axis}" mode',
    )
    try:
        mode = resolve_axis_mode(mode_value)
    except ValueError as exc:
        raise LayoutFileError(str(exc)) from exc
    log = _boolean(raw, "log")
    if log and mode is AxisMode.TIME:
        raise LayoutFileError(
            f'Layout axis "{axis}" cannot combine time mode with log scaling.'
        )
    return AxisLayoutState(
        label=_string(raw["label"], f'layout axis "{axis}" label'),
        units=_optional_string(raw["units"], f'layout axis "{axis}" units'),
        mode=mode,
        log=log,
    )


def _parse_interaction(raw: dict[str, Any]) -> InteractionState:
    tool_value = _non_empty_string(
        raw["active_tool"],
        'layout interaction field "active_tool"',
    )
    try:
        tool = InteractionTool(tool_value)
    except ValueError as exc:
        raise LayoutFileError(
            f'Layout interaction active_tool "{tool_value}" is invalid.'
        ) from exc
    try:
        return InteractionState(
            autoscale_x=_boolean(raw, "autoscale_x"),
            autoscale_y=_boolean(raw, "autoscale_y"),
            rolling_x=_boolean(raw, "rolling_x"),
            active_tool=tool,
        )
    except (TypeError, ValueError) as exc:
        raise LayoutFileError(str(exc)) from exc


def _parse_ranges(raw: dict[str, Any]) -> dict[str, tuple[float, float]]:
    _validate_fields(raw, frozenset(), 'layout field "ranges"', optional=_RANGE_FIELDS)
    result: dict[str, tuple[float, float]] = {}
    for axis in ("x", "y"):
        if axis not in raw:
            continue
        value = raw[axis]
        if not isinstance(value, list) or len(value) != 2:
            raise LayoutFileError(
                f'Layout range "{axis}" must contain two numbers.'
            )
        first = _finite_number(value[0], f'layout range "{axis}"')
        second = _finite_number(value[1], f'layout range "{axis}"')
        if first == second:
            raise LayoutFileError(
                f'Layout range "{axis}" must have a non-zero span.'
            )
        result[axis] = (min(first, second), max(first, second))
    return result


def _parse_curves(raw: dict[str, Any]) -> dict[str, CurveLayoutState]:
    result: dict[str, CurveLayoutState] = {}
    for key, value in raw.items():
        curve_key = _non_empty_string(key, "layout curve key")
        owner = f'layout curve "{curve_key}"'
        state = _mapping(value, owner)
        _validate_fields(state, _CURVE_FIELDS, owner)
        result[curve_key] = CurveLayoutState(
            visible=_boolean(state, "visible"),
            style=_parse_curve_style(
                state["style"],
                owner=f'layout curve "{curve_key}" style',
            ),
        )
    return result


def _parse_curve_style(raw: object, *, owner: str) -> CurveStyle:
    value = _mapping(raw, owner)
    _validate_fields(value, _CURVE_STYLE_FIELDS, owner)
    try:
        return CurveStyle(
            line_enabled=_boolean(value, "line_enabled"),
            line_color=_string(
                value["line_color"],
                f"{owner} line_color",
            ),
            line_width=_finite_number(
                value["line_width"],
                f"{owner} line_width",
            ),
            marker_symbol=_string(
                value["marker_symbol"],
                f"{owner} marker_symbol",
            ),
            marker_size=_integer(
                value["marker_size"],
                f"{owner} marker_size",
            ),
            marker_outline_width=_finite_number(
                value["marker_outline_width"],
                f"{owner} marker_outline_width",
            ),
            marker_enabled=_boolean(value, "marker_enabled"),
            marker_filled=_boolean(value, "marker_filled"),
        )
    except (TypeError, ValueError) as exc:
        raise LayoutFileError(str(exc)) from exc


def _parse_cursors(raw: object) -> tuple[CursorLayoutState, ...]:
    if not isinstance(raw, list):
        raise LayoutFileError('Layout field "cursors" must be a list.')
    result: list[CursorLayoutState] = []
    keys: set[str] = set()
    for index, value in enumerate(raw):
        owner = f"layout cursor at index {index}"
        state = _mapping(value, owner)
        _validate_fields(state, _CURSOR_FIELDS, owner)
        key = _non_empty_string(state["key"], f"{owner} key")
        if key in keys:
            raise LayoutFileError(f'Duplicate cursor key "{key}".')
        keys.add(key)
        type_value = _non_empty_string(
            state["type"],
            f'cursor "{key}" type',
        ).lower()
        try:
            cursor_type = CursorType(type_value)
        except ValueError as exc:
            raise LayoutFileError(
                f'Cursor "{key}" has an invalid type.'
            ) from exc
        target = _optional_string(
            state["snap_target_curve_key"],
            f'cursor "{key}" snap_target_curve_key',
        )
        if cursor_type is CursorType.Y and target is not None:
            raise LayoutFileError(
                f'Y cursor "{key}" cannot have a snap target.'
            )
        follow = _boolean(state, "follow_target_visibility")
        if follow and target is None:
            raise LayoutFileError(
                f'Cursor "{key}" visibility coupling requires a snap target.'
            )
        result.append(
            CursorLayoutState(
                key=key,
                name=_non_empty_string(
                    state["name"],
                    f'cursor "{key}" name',
                ),
                cursor_type=cursor_type,
                value=_finite_number(
                    state["value"],
                    f'cursor "{key}" value',
                ),
                visible=_boolean(state, "visible"),
                style=_parse_cursor_style(state["style"]),
                snap_target_curve_key=target,
                follow_target_visibility=follow,
                label_visible=_boolean(state, "label_visible"),
            )
        )
    return tuple(result)


def _parse_cursor_style(raw: object) -> CursorStyle:
    value = _mapping(raw, "layout cursor style")
    _validate_fields(value, _CURSOR_STYLE_FIELDS, "layout cursor style")
    line_style_value = _non_empty_string(
        value["line_style"],
        "layout cursor style line_style",
    )
    try:
        line_style = CursorLineStyle(line_style_value)
        return CursorStyle(
            line_color=_string(
                value["line_color"],
                "layout cursor style line_color",
            ),
            line_width=_finite_number(
                value["line_width"],
                "layout cursor style line_width",
            ),
            line_style=line_style,
        )
    except (TypeError, ValueError) as exc:
        raise LayoutFileError(f"Invalid cursor style: {exc}") from exc


def _parse_pairs(raw: object) -> tuple[CursorPairLayoutState, ...]:
    if not isinstance(raw, list):
        raise LayoutFileError('Layout field "cursor_pairs" must be a list.')
    result: list[CursorPairLayoutState] = []
    keys: set[str] = set()
    members: set[str] = set()
    for index, value in enumerate(raw):
        owner = f"layout cursor pair at index {index}"
        state = _mapping(value, owner)
        _validate_fields(state, _CURSOR_PAIR_FIELDS, owner)
        key = _non_empty_string(state["key"], f"{owner} key")
        raw_members = state["members"]
        if not isinstance(raw_members, list) or len(raw_members) != 2:
            raise LayoutFileError(
                f'Cursor pair "{key}" must contain exactly two members.'
            )
        first = _non_empty_string(
            raw_members[0],
            f'cursor pair "{key}" first member',
        )
        second = _non_empty_string(
            raw_members[1],
            f'cursor pair "{key}" second member',
        )
        if first == second:
            raise LayoutFileError(
                f'Cursor pair "{key}" requires two distinct members.'
            )
        if key in keys:
            raise LayoutFileError(f'Duplicate cursor pair key "{key}".')
        if first in members or second in members:
            raise LayoutFileError(
                f'Cursor pair "{key}" reuses a cursor from another saved pair.'
            )
        annotation = _finite_number(
            state["annotation_position"],
            f'cursor pair "{key}" annotation_position',
        )
        if not 0.0 <= annotation <= 1.0:
            raise LayoutFileError(
                f'Cursor pair "{key}" annotation_position must be between 0 and 1.'
            )
        keys.add(key)
        members.update((first, second))
        result.append(
            CursorPairLayoutState(
                key=key,
                first_cursor_key=first,
                second_cursor_key=second,
                measurement_visible=_boolean(
                    state,
                    "measurement_visible",
                ),
                annotation_position=annotation,
            )
        )
    return tuple(result)


def _validate_saved_pair_members(
    pairs: tuple[CursorPairLayoutState, ...],
    cursors: tuple[CursorLayoutState, ...],
) -> None:
    cursor_types = {state.key: state.cursor_type for state in cursors}
    cursor_positions = {state.key: index for index, state in enumerate(cursors)}
    for pair in pairs:
        first = cursor_types.get(pair.first_cursor_key)
        second = cursor_types.get(pair.second_cursor_key)
        if first is None or second is None:
            raise LayoutFileError(
                f'Cursor pair "{pair.key}" refers to an unknown cursor.'
            )
        if first is not second:
            raise LayoutFileError(
                f'Cursor pair "{pair.key}" members must use the same axis.'
            )
        first_position = cursor_positions[pair.first_cursor_key]
        second_position = cursor_positions[pair.second_cursor_key]
        if second_position != first_position + 1:
            raise LayoutFileError(
                f'Cursor pair "{pair.key}" members must be adjacent and ordered.'
            )


def _plot_layout_to_mapping(layout: PlotLayoutState) -> dict[str, object]:
    return {
        "restore_view_state_on_load": layout.restore_view_state_on_load,
        "theme": layout.theme,
        "plot_style": layout.plot_style,
        "axes": {
            "x": _axis_to_mapping(layout.x_axis),
            "y": _axis_to_mapping(layout.y_axis),
        },
        "grid_visible": layout.grid_visible,
        "rendering": {
            "antialiasing": layout.rendering.antialiasing,
            "downsampling": layout.rendering.downsampling,
            "clip_to_view": layout.rendering.clip_to_view,
            "adaptive_performance": layout.rendering.adaptive_performance,
        },
        "interaction": {
            "autoscale_x": layout.interaction_state.autoscale_x,
            "autoscale_y": layout.interaction_state.autoscale_y,
            "rolling_x": layout.interaction_state.rolling_x,
            "active_tool": layout.interaction_state.active_tool.value,
        },
        "ranges": {
            key: [values[0], values[1]]
            for key, values in layout.ranges.items()
        },
        "curves": {
            key: {
                "visible": state.visible,
                "style": _curve_style_to_mapping(state.style),
            }
            for key, state in layout.curves.items()
        },
        "cursors": [_cursor_to_mapping(state) for state in layout.cursors],
        "cursor_pairs": [
            _pair_to_mapping(state) for state in layout.cursor_pairs
        ],
    }


def _axis_to_mapping(state: AxisLayoutState) -> dict[str, object]:
    return {
        "label": state.label,
        "units": state.units,
        "mode": state.mode.value,
        "log": state.log,
    }


def _curve_style_to_mapping(style: CurveStyle) -> dict[str, object]:
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


def _cursor_to_mapping(state: CursorLayoutState) -> dict[str, object]:
    return {
        "key": state.key,
        "name": state.name,
        "type": state.cursor_type.value,
        "value": state.value,
        "visible": state.visible,
        "style": {
            "line_color": state.style.line_color,
            "line_width": state.style.line_width,
            "line_style": state.style.line_style.value,
        },
        "snap_target_curve_key": state.snap_target_curve_key,
        "follow_target_visibility": state.follow_target_visibility,
        "label_visible": state.label_visible,
    }


def _pair_to_mapping(state: CursorPairLayoutState) -> dict[str, object]:
    return {
        "key": state.key,
        "members": [state.first_cursor_key, state.second_cursor_key],
        "measurement_visible": state.measurement_visible,
        "annotation_position": state.annotation_position,
    }


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LayoutFileError(f'Duplicate JSON object key "{key}".')
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise LayoutFileError(f"JSON number {value} must be finite.")


def _mapping(value: object, owner: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LayoutFileError(f"{owner} must be an object.")
    return value


def _validate_fields(
    mapping: dict[str, Any],
    required: frozenset[str],
    owner: str,
    *,
    optional: frozenset[str] = frozenset(),
) -> None:
    actual = set(mapping)
    missing = required - actual
    if missing:
        fields = ", ".join(sorted(missing))
        raise LayoutFileError(f"{owner} is missing required field(s): {fields}.")
    unknown = actual - required - optional
    if unknown:
        fields = ", ".join(sorted(unknown))
        raise LayoutFileError(f"{owner} contains unknown field(s): {fields}.")


def _boolean(mapping: dict[str, Any], key: str) -> bool:
    value = mapping[key]
    if type(value) is not bool:
        raise LayoutFileError(f'Layout field "{key}" must be a Boolean.')
    return value


def _string(value: object, owner: str) -> str:
    if not isinstance(value, str):
        raise LayoutFileError(f"{owner} must be a string.")
    return value


def _non_empty_string(value: object, owner: str) -> str:
    result = _string(value, owner)
    if not result:
        raise LayoutFileError(f"{owner} must not be empty.")
    return result


def _optional_string(value: object, owner: str) -> str | None:
    if value is None:
        return None
    result = _string(value, owner)
    return result or None


def _finite_number(value: object, owner: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LayoutFileError(f"{owner} must be a number.")
    number = float(value)
    if not math.isfinite(number):
        raise LayoutFileError(f"{owner} must be finite.")
    return number


def _integer(value: object, owner: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise LayoutFileError(f"{owner} must be an integer.")
    return value
