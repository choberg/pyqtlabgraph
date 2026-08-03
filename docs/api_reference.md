# API Reference

`PyQtLabGraph` provides a high-level, developer-friendly API for embedding and interacting with live plots, while keeping the underlying `pyqtgraph` objects accessible for advanced use cases.

---

## PyQtLabGraphWidget Constructor

Initialize the widget, typically inside a host `QMainWindow` or custom container layout.

```python
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout
from pyqtlabgraph import (
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphStyleRegistry,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
    PlotSnapshot,
)

style_registry = PyQtLabGraphStyleRegistry()
self.plot = PyQtLabGraphWidget(
    plot_identifier="my-unique-plot-id",        # Identifier key for layout persistence
    layout_path=Path("plot_layouts.json"),       # Target layout file (optional)
    rolling_window_size=300.0,                   # Initial rolling X window size (default: 300.0)
    theme="dark",                                # Initial theme (default: light)
    plot_style="dark",                           # Initial curve style palette (default: light)
    style_registry=style_registry,               # Optional explicit style registry
    show_frame=True,                             # Draw the component frame
)
self.toolbar = PyQtLabGraphToolbar(self.plot)
self.legend = PyQtLabGraphLegend(
    self.plot, orientation=Qt.Orientation.Horizontal
)
self.cursors = PyQtLabGraphCursorWidget(self.plot)

for placeholder, component in (
    (self.ui.plotContainer, self.plot),
    (self.ui.toolbarContainer, self.toolbar),
    (self.ui.legendContainer, self.legend),
    (self.ui.cursorContainer, self.cursors),
):
    layout = QVBoxLayout(placeholder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(component)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `plot_identifier` | `str` | *Required* | Stable, unique key for the plot. Crucial for JSON layout file mapping. |
| `layout_path` | `str` \| `Path` | `None` | Path to the layout save file. Activates auto layout features. |
| `rolling_window_size` | `float` | `300.0` | Initial width of the rolling X-window. |
| `theme` | `str` \| `PyQtLabGraphTheme` | `None` | Active background/grid theme name (`"light"`, `"dark"`, `"light-solarized"`, `"dark-solarized"`). |
| `plot_style` | `str` \| `PyQtLabGraphPlotStyle` | `None` | Active curve styling palette name (`"light"`, `"dark"`, `"solarized"`). |
| `style_registry` | `PyQtLabGraphStyleRegistry` | `None` | Registry for built-in and host-registered themes and plot styles. A widget-owned built-in registry is created when omitted. |
| `parent` | `QWidget` | `None` | Optional Qt parent. |
| `show_frame` | `bool` | `True` | Draw the component-owned palette-aware frame. |

`PyQtLabGraphToolbar`, `PyQtLabGraphLegend`, and `PyQtLabGraphCursorWidget`
take the plot as their first argument and independently support `parent` and
`show_frame`. The plot never stores references to these companion widgets.

---

## Core Plotting Methods

Use these methods to manage curves and feed data into the widget:

* **`plot(key: str, y: ArrayLike, *, label: str = None, style: CurveStyle = None)`**
  Creates a curve from Y-data and generates X coordinates as indices.
* **`plot(key: str, x: ArrayLike, y: ArrayLike, *, label: str = None, style: CurveStyle = None)`**
  Creates a curve from explicit X/Y data. X and Y lengths are validated before
  the curve is committed.
* **`add_curve(key: str, label: str = None, style: CurveStyle = None)`**
  Registers a new curve key without passing data. Used to initialize legend entries early.
* **`set_data(key: str, y: ArrayLike)`**
  Replaces an existing curve with Y-data and generated index coordinates.
* **`set_data(key: str, x: ArrayLike, y: ArrayLike)`**
  Replaces an existing curve with explicit X/Y data. Length validation happens
  before the underlying `PlotDataItem` is mutated.

Explicit X/Y calls may use the named `x=` and `y=` parameters.
* **`add_point(key: str, x: float, y: float)`**
  Appends a single data point to the curve. Extremely useful for real-time live sensor updates.
* **`curve_data(key: str) -> tuple[np.ndarray, np.ndarray]`**
  Retrieves current coordinates stored in the underlying PyQtGraph `PlotDataItem` for the curve.
* **`curve_style(key: str) -> CurveStyle`**
  Returns the current curve style object.
* **`curve_visible(key: str) -> bool`**
  Returns the curve's effective visibility state.
* **`set_curve_style(key: str, style: CurveStyle)`**
  Applies a new `CurveStyle` to the given curve.
* **`set_curve_visible(key: str, visible: bool)`**
  Toggles rendering of the curve in the canvas and marks its checkbox state in the legend.

The high-level data API deliberately accepts no arbitrary PyQtGraph keyword
arguments. Configure native options through `curve_item(key)` or the
`native_plot_widget`, `native_plot_item`, and `native_view_box` escape hatches.

### Curve Signals

Curve notifications are published by `PyQtLabGraphWidget` after a command
finishes successfully:

* **`curve_added(str)`**: Emitted once after `add_curve()` or `plot()` has
  completed. Initial data supplied to `plot()` is covered by this creation
  signal and does not also emit `curve_data_changed`.
* **`curve_removed(str)`**: Emitted once after a curve has been removed.
* **`curve_changed(str)`**: Emitted once when a curve's effective style,
  label, or visibility changes.
* **`curve_data_changed(str)`**: Emitted once after `set_data()`,
  `add_point()`, or `clear_curve()` succeeds.

Failed commands and style or visibility no-ops emit no curve signal. Theme and
Adaptive Performance repaints do not report a curve-domain change.

* **`state_reset()`**: Emitted once after an atomic layout or runtime snapshot
  replacement. Granular curve, cursor, interaction, and presentation signals
  are suppressed during the replacement. Failed replacements restore the
  previous runtime snapshot and emit no public signal.

Data commands update the plot in a fixed order: mutate data, refresh snapped
cursors, apply automatic ranges, evaluate Adaptive Performance against the
final range, reapply appearance only when the adaptive mode changes, refresh
cursor presentation, and finally emit coalesced public signals.

Read-only rendering state is exposed through `grid_visible`,
`antialiasing_enabled`, `downsampling_enabled`, `clip_to_view_enabled`, and
`adaptive_performance_enabled`.

---

## Cursor Methods

Use cursor methods to add movable X/Y reference lines and keep cursor state synchronized with the optional `PyQtLabGraphCursorWidget`.

* **`add_cursor(cursor_type: CursorType | str, key: str = None, name: str = None, value: float = None, style: CursorStyle = None, snap_target_curve_key: str = None, follow_target_visibility: bool = False, label_visible: bool = False) -> str`**
  Adds an X or Y cursor and returns its stable key. X cursors may snap to a target curve.
* **`remove_cursor(cursor_key: str)`**
  Removes the cursor, its plot line, and its cursor widget row.
* **`set_cursor_value(cursor_key: str, value: float)`**
  Moves a cursor in raw data coordinates. Snapped X cursors normalize to the nearest real X value of their target curve.
* **`set_cursor_name(cursor_key: str, name: str)`**
  Updates the displayed cursor name. Empty names are rejected.
* **`set_cursor_style(cursor_key: str, style: CursorStyle)`**
  Applies cursor line color, width, and line style.
* **`set_cursor_visible(cursor_key: str, visible: bool)`**
  Shows or hides the cursor line without removing the cursor state.
* **`set_cursor_label_visible(cursor_key: str, visible: bool)`**
  Stores whether a cursor label should be shown.
* **`set_cursor_snap_target(cursor_key: str, target_curve_key: str | None)`**
  Sets the snap curve explicitly; `None` makes the cursor free.
* **`set_cursor_follow_target_visibility(cursor_key: str, enabled: bool)`**
  Makes a cursor effectively hidden when its target curve is hidden.
* **`cursor_state(cursor_key: str) -> CursorState`** / **`cursor_states() -> tuple[CursorState, ...]`**
  Returns immutable cursor state objects in display order.
* **`set_cursor_order(cursor_keys: Sequence[str])`**
  Sets the display order. Every current cursor key must occur exactly once, and cursor pairs must remain adjacent in pair order.
* **`cursor_target_value(cursor_key: str) -> float | None`**
  Returns the target curve's Y value at a snapped X cursor position, or `None` when unavailable.
* **`cursor_effective_visible(cursor_key: str) -> bool`**
  Returns the cursor's actual visibility after follow-target visibility is applied.
* **`add_cursor_pair(first_cursor_key: str, second_cursor_key: str, key: str = None, measurement_visible: bool = True, annotation_position: float = 0.08) -> str`**
  Groups two cursors on the same axis into a measurement pair and returns its stable key.
* **`remove_cursor_pair(pair_key: str)`**
  Removes a cursor pair without removing either cursor.
* **`set_cursor_pair_measurement_visible(pair_key: str, visible: bool)`**
  Shows or hides the pair's distance annotation in the plot.
* **`set_cursor_pair_annotation_position(pair_key: str, position: float)`**
  Sets the distance annotation's normalized orthogonal position within the plot area.
* **`cursor_pair_state(pair_key: str) -> CursorPairState`** / **`cursor_pair_states() -> tuple[CursorPairState, ...]`**
  Returns immutable cursor pair state objects in display order.
* **`cursor_pair_measurement_text(pair_key: str) -> str`**
  Returns the formatted pair measurement text. X pairs on time axes also include the corresponding frequency.

Cursor data models:

* **`CursorType`**: `CursorType.X` or `CursorType.Y`.
* **`CursorStyle`**: immutable style object with `line_color`, `line_width`, and a `CursorLineStyle` enum value.
* **`CursorState`**: immutable state object containing key, name, type, value, visibility, style, snapping, target curve, target-visibility following, and label visibility.
* **`CursorPairState`**: immutable state object containing key, the two cursor keys, distance-label visibility, and normalized annotation position.

Example:

```python
from pyqtlabgraph import CursorLineStyle, CursorStyle

plot.plot("sensor", [0, 1, 2, 3], [10, 12, 11, 14], label="Sensor")

free_x = plot.add_cursor("x", name="Free X", value=1.5)
plot.add_cursor("y", name="Threshold", value=12.0)

snap_x = plot.add_cursor(
    "x",
    name="Sensor Sample",
    value=1.6,
    style=CursorStyle(
        line_color="#009E73",
        line_width=2.0,
        line_style=CursorLineStyle.DOT,
    ),
    snap_target_curve_key="sensor",
    follow_target_visibility=True,
)

plot.set_cursor_value(free_x, 2.25)
plot.set_cursor_snap_target(snap_x, "sensor")
```

If a cursor widget is embedded, users can edit cursor values directly and use its context menu to create, delete, or pair cursors, copy selected rows, and open a settings dialog for cursor name, visibility, labels, snapping, target curve, and line style. Two selected, unpaired cursors on the same axis can be paired from the context menu. Dragging between rows reorders the selected cursor blocks, while dragging one unpaired cursor onto another unpaired cursor of the same axis provides the same pairing operation. Each pair is rendered as one draggable group with two independently selectable cursor rows and a delta measurement bar. Clicking the group background selects both cursors for synchronous movement. The result eye and pair context menu control the distance annotation, whose orthogonal plot position can be dragged and is persisted in layouts.

Cursor selection belongs to the plot. `selected_cursor_keys()` and
`set_selected_cursor_keys(...)` expose that canonical state, while every
attached cursor panel projects it through its Qt selection model. Selection
changes made in one panel or on a plot cursor therefore synchronize all panels.

---

## Layout & Customization Methods

Configure views, axes, limits, and serialize settings:

* **`set_axis_labels(x_label: str, y_label: str, x_units: str = None, y_units: str = None, x_mode: AxisMode = None, y_mode: AxisMode = None)`**
  Updates axis titles, units, and tick representation modes (`AxisMode.AUTO`, `AxisMode.LINEAR`, `AxisMode.TIME`).
  `AxisMode.TIME` is mutually exclusive with logarithmic scaling on the same axis. Enabling time mode disables that axis' logarithmic scaling, and enabling logarithmic scaling switches a time axis back to linear numeric formatting.
* **`get_x_range() -> tuple[float, float]`** / **`get_y_range() -> tuple[float, float]`**
  Gets active viewport limits.
* **`apply_manual_x_limits(xmin: float, xmax: float)`** / **`apply_manual_y_limits(ymin: float, ymax: float)`**
  Manually sets limits, deactivating automatic scaling or rolling window modes.
* **`request_rolling_x(enabled: bool)`**
  Enables/disables the rolling X-window.
* **`set_rolling_window_size(size: float)`**
  Updates the rolling window size.
* **`request_autoscale_x(enabled: bool)`** / **`request_autoscale_y(enabled: bool)`**
  Enables or disables automatic scaling for the corresponding axis.
* **`request_show_all()`**
  Rescales both axes to fit all data.
* **`set_theme(theme: str | PyQtLabGraphTheme)`**
  Applies a background/grid theme.
* **`set_plot_style(style: str | PyQtLabGraphPlotStyle)`**
  Applies the plot style palette to all existing curves and uses it for new curves.
* **`save_layout()`** / **`load_layout()`**
  Manually writes/restores layout state to/from the file set in `layout_path`.
  Layout format version 1 requires the complete current field set and rejects
  unknown fields before the widget changes. Booleans are not coerced, numeric
  values must be finite, and invalid enums, styles, interaction combinations,
  duplicate keys, cursor targets, and cursor pairs are rejected. Application
  is atomic and resolves theme and plot-style names through the widget's
  `style_registry`.
  Host applications must create curves before calling `load_layout()` so saved
  cursor snap targets and curve-matched styling can be resolved by key. Unknown
  saved curves are ignored and current curves absent from the layout retain
  their state. Saved cursors and pairs replace the current cursor state, and
  cursor selection is cleared. Saving one plot keeps the other plot identifiers
  in the same file.
* **`restore_snapshot(snapshot: PlotSnapshot)`**
  Atomically restores an exact layout-relevant runtime state. Use
  `PlotSnapshot.capture(plot)` to capture a rollback point. Runtime snapshots
  are separate from persisted layout DTOs and include cursor order
  and selection.
* **`show_customize_dialog(curve_key: str = None)`**
  Launches the modeless Customize dialog. If `curve_key` is supplied, it opens directly on the tab editing that curve. Most edits preview immediately, while ranges preview explicitly. *Apply & Close* keeps the preview, *Save Layout* saves it without closing, and *Cancel* restores the opening or last-saved state.

`interaction_state` returns an immutable `InteractionState`. Autoscale X and
rolling X cannot be active together. Enabling a zoom tool disables both
autoscales and rolling X, while enabling either autoscale or rolling X ends the
active zoom tool. Invalid combinations raise before widget state changes.

---

## Advanced pyqtgraph Access

PyQtLabGraph stays out of the way when advanced customization is required. You can bypass our high-level wrappers and talk directly to the underlying PyQtGraph library components:

```python
# Access native pyqtgraph objects
native_widget = self.plot.native_plot_widget  # pg.PlotWidget
native_item = self.plot.native_plot_item      # pg.PlotItem
native_view = self.plot.native_view_box       # pg.ViewBox

# Add native items to the canvas
native_item.addItem(my_custom_infinite_line)

# Retrieve raw PlotDataItem references
raw_curve_item = self.plot.curve_item("sensor_1") # pg.PlotDataItem
raw_curve_item.setClickable(True)
```
