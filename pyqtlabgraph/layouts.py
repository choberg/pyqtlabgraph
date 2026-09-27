from __future__ import annotations

import json
import math
import os
import tempfile
import types
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union, get_args, get_origin, get_type_hints

from .axis import AxisMode
from .models import CursorPairState, CursorState, InteractionState
from .runtime_state import CurveSnapshot, PlotSnapshot

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


LAYOUT_FORMAT_VERSION = 2


class LayoutFileError(RuntimeError):
    """Raised when a PyQtLabGraph layout file is invalid or cannot be accessed."""


@dataclass(frozen=True)
class PlotLayout:
    """Persisted plot state; field names match `PlotSnapshot` where shared."""

    restore_view_state_on_load: bool
    theme: str
    curve_palette: str
    curve_palette_reverse: bool
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
    interaction_state: InteractionState
    x_range: tuple[float, float] | None
    y_range: tuple[float, float] | None
    curves: tuple[CurveSnapshot, ...]
    cursors: tuple[CursorState, ...]
    cursor_pairs: tuple[CursorPairState, ...]

    def __post_init__(self) -> None:
        if not self.theme:
            raise ValueError("Layout theme must not be empty.")
        if not self.curve_palette:
            raise ValueError("Layout curve_palette must not be empty.")
        for axis, mode, log, view_range in (
            ("x", self.x_mode, self.x_log, self.x_range),
            ("y", self.y_mode, self.y_log, self.y_range),
        ):
            if log and mode is AxisMode.TIME:
                raise ValueError(f"Layout {axis} axis cannot combine time mode with log scaling.")
            if view_range is not None and not view_range[0] < view_range[1]:
                raise ValueError(f"Layout {axis}_range must be strictly increasing.")
        _require_unique("curve", [curve.key for curve in self.curves])
        _require_unique("cursor", [cursor.key for cursor in self.cursors])
        _require_unique("cursor pair", [pair.key for pair in self.cursor_pairs])
        _validate_pairs(self.cursors, self.cursor_pairs)


_SNAPSHOT_FIELDS = frozenset(field.name for field in fields(PlotSnapshot))
_SHARED_FIELDS = tuple(
    field.name
    for field in fields(PlotLayout)
    if field.name in _SNAPSHOT_FIELDS
    and field.name not in {"theme", "curve_palette", "x_range", "y_range"}
)


def decode_layout_document(source: str) -> dict[str, PlotLayout]:
    """Decode and validate a complete layout document without a Qt application."""
    try:
        raw = json.loads(
            source,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as exc:
        raise LayoutFileError(f"Malformed PyQtLabGraph layout JSON: {exc}") from exc
    document = _mapping(raw, "layout document")
    _require_fields(document, {"version", "plots"}, "layout document")
    version = document["version"]
    if type(version) is not int or version != LAYOUT_FORMAT_VERSION:
        raise LayoutFileError(
            f"Unsupported PyQtLabGraph layout file version {version!r}; "
            f"version {LAYOUT_FORMAT_VERSION} is required."
        )
    plots = _mapping(document["plots"], "layout plots")
    for identifier in plots:
        if not identifier.strip():
            raise LayoutFileError("Layout plot identifiers must not be empty.")
    return {
        identifier: _decode(PlotLayout, value, f'plots["{identifier}"]')
        for identifier, value in plots.items()
    }


def encode_layout_document(plots: dict[str, PlotLayout]) -> str:
    raw = {
        "version": LAYOUT_FORMAT_VERSION,
        "plots": {identifier: _encode(layout) for identifier, layout in plots.items()},
    }
    return json.dumps(raw, indent=2, sort_keys=True, allow_nan=False) + "\n"


def load_plot_layout(path: str | Path, plot_identifier: str) -> PlotLayout | None:
    layout_path = Path(path)
    if not layout_path.exists():
        return None
    return _read_layout_document(layout_path).get(plot_identifier)


def save_plot_layout(path: str | Path, plot_identifier: str, plot_layout: PlotLayout) -> None:
    if not plot_identifier.strip():
        raise LayoutFileError("PyQtLabGraph plot identifier must not be empty.")
    layout_path = Path(path)
    plots = _read_layout_document(layout_path) if layout_path.exists() else {}
    plots[plot_identifier] = plot_layout
    encoded = encode_layout_document(plots)
    layout_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        descriptor, name = tempfile.mkstemp(dir=str(layout_path.parent), suffix=".tmp")
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
) -> PlotLayout:
    snapshot = PlotSnapshot.capture(plot)
    return PlotLayout(
        restore_view_state_on_load=restore_view_state_on_load,
        theme=snapshot.theme.name,
        curve_palette=snapshot.curve_palette.name,
        x_range=snapshot.x_range if include_x_range else None,
        y_range=snapshot.y_range if include_y_range else None,
        **{name: getattr(snapshot, name) for name in _SHARED_FIELDS},
    )


def apply_plot_layout(
    plot: PyQtLabGraphWidget,
    layout: PlotLayout,
    *,
    restore_view_state: bool | None = None,
) -> None:
    """Reconcile a validated layout and replace widget state atomically."""
    restore_view = (
        layout.restore_view_state_on_load if restore_view_state is None else restore_view_state
    )
    plot.restore_snapshot(_reconcile_layout(plot, layout, restore_view=restore_view))


def _reconcile_layout(
    plot: PyQtLabGraphWidget,
    layout: PlotLayout,
    *,
    restore_view: bool,
) -> PlotSnapshot:
    current = PlotSnapshot.capture(plot)
    try:
        theme = plot.style_registry.resolve_theme(layout.theme)
        curve_palette = plot.style_registry.resolve_curve_palette(layout.curve_palette)
    except ValueError as exc:
        raise LayoutFileError(str(exc)) from exc

    curve_keys = {curve.key for curve in current.curves}
    for cursor in layout.cursors:
        target = cursor.snap_target_curve_key
        if target is not None and target not in curve_keys:
            raise LayoutFileError(
                f'Cursor "{cursor.key}" refers to unknown snap target curve "{target}".'
            )
    saved_curves = {curve.key: curve for curve in layout.curves}

    interaction = layout.interaction_state if restore_view else current.interaction_state
    x_range = current.x_range
    y_range = current.y_range
    if restore_view:
        if layout.x_range is not None and not (interaction.autoscale_x or interaction.rolling_x):
            x_range = layout.x_range
        if layout.y_range is not None and not interaction.autoscale_y:
            y_range = layout.y_range

    values: dict[str, Any] = {name: getattr(layout, name) for name in _SHARED_FIELDS}
    values.update(
        theme=theme,
        curve_palette=curve_palette,
        curves=tuple(saved_curves.get(curve.key, curve) for curve in current.curves),
        selected_cursor_keys=(),
        interaction_state=interaction,
        x_range=x_range,
        y_range=y_range,
    )
    return PlotSnapshot(**values)


def _read_layout_document(path: Path) -> dict[str, PlotLayout]:
    try:
        return decode_layout_document(path.read_text(encoding="utf-8"))
    except (OSError, LayoutFileError) as exc:
        raise LayoutFileError(f"Could not read PyQtLabGraph layout file {path}: {exc}") from exc


def _require_unique(kind: str, keys: list[str]) -> None:
    seen: set[str] = set()
    for key in keys:
        if key in seen:
            raise ValueError(f'Duplicate {kind} key "{key}".')
        seen.add(key)


def _validate_pairs(
    cursors: tuple[CursorState, ...],
    pairs: tuple[CursorPairState, ...],
) -> None:
    positions = {cursor.key: index for index, cursor in enumerate(cursors)}
    members: set[str] = set()
    for pair in pairs:
        first = positions.get(pair.first_cursor_key)
        second = positions.get(pair.second_cursor_key)
        if first is None or second is None:
            raise ValueError(f'Cursor pair "{pair.key}" refers to an unknown cursor.')
        if cursors[first].cursor_type is not cursors[second].cursor_type:
            raise ValueError(f'Cursor pair "{pair.key}" members must use the same axis.')
        if second != first + 1:
            raise ValueError(f'Cursor pair "{pair.key}" members must be adjacent and ordered.')
        if members & {pair.first_cursor_key, pair.second_cursor_key}:
            raise ValueError(f'Cursor pair "{pair.key}" reuses a cursor from another pair.')
        members.update((pair.first_cursor_key, pair.second_cursor_key))


def _encode(value: object) -> object:
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _encode(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple):
        return [_encode(item) for item in value]
    return value


def _decode(annotation: Any, raw: object, owner: str) -> Any:
    """Strictly convert JSON data into the annotated type."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin in (Union, types.UnionType):
        if raw is None and type(None) in args:
            return None
        (inner,) = (arg for arg in args if arg is not type(None))
        return _decode(inner, raw, owner)
    if isinstance(annotation, type) and is_dataclass(annotation):
        mapping = _mapping(raw, owner)
        hints = get_type_hints(annotation)
        names = [field.name for field in fields(annotation) if field.init]
        _require_fields(mapping, set(names), owner)
        values = {name: _decode(hints[name], mapping[name], f"{owner}.{name}") for name in names}
        try:
            return annotation(**values)
        except (TypeError, ValueError) as exc:
            raise LayoutFileError(f"{owner}: {exc}") from exc
    if origin is tuple:
        if not isinstance(raw, list):
            raise LayoutFileError(f"{owner} must be a list.")
        if len(args) == 2 and args[1] is Ellipsis:
            item_types = [args[0]] * len(raw)
        elif len(raw) != len(args):
            raise LayoutFileError(f"{owner} must contain {len(args)} values.")
        else:
            item_types = list(args)
        return tuple(
            _decode(item_type, item, f"{owner}[{index}]")
            for index, (item_type, item) in enumerate(zip(item_types, raw))
        )
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        try:
            return annotation(raw)
        except ValueError as exc:
            raise LayoutFileError(f"{owner} value {raw!r} is invalid.") from exc
    if annotation is bool:
        if type(raw) is not bool:
            raise LayoutFileError(f"{owner} must be a Boolean.")
        return raw
    if annotation is int:
        if type(raw) is not int:
            raise LayoutFileError(f"{owner} must be an integer.")
        return raw
    if annotation is float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise LayoutFileError(f"{owner} must be a number.")
        if not math.isfinite(raw):
            raise LayoutFileError(f"{owner} must be finite.")
        return float(raw)
    if annotation is str:
        if not isinstance(raw, str):
            raise LayoutFileError(f"{owner} must be a string.")
        return raw
    raise TypeError(f"Unsupported layout field type {annotation!r} for {owner}.")


def _mapping(value: object, owner: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise LayoutFileError(f"{owner} must be an object.")
    return value


def _require_fields(mapping: dict[str, Any], required: set[str], owner: str) -> None:
    missing = required - set(mapping)
    if missing:
        raise LayoutFileError(f"{owner} is missing required field(s): {', '.join(sorted(missing))}.")
    unknown = set(mapping) - required
    if unknown:
        raise LayoutFileError(f"{owner} contains unknown field(s): {', '.join(sorted(unknown))}.")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise LayoutFileError(f'Duplicate JSON object key "{key}".')
        result[key] = value
    return result


def _reject_json_constant(value: str) -> object:
    raise LayoutFileError(f"JSON number {value} must be finite.")
