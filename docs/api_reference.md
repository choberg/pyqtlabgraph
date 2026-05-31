# API Reference

`PyQtLabGraph` provides a high-level, developer-friendly API for embedding and interacting with live plots, while keeping the underlying `pyqtgraph` objects accessible for advanced use cases.

---

## PyQtLabGraphWidget Constructor

Initialize the widget, typically inside a host `QMainWindow` or custom container layout.

```python
from pathlib import Path
from PySide6.QtCore import Qt
from pyqtlabgraph import PyQtLabGraphWidget

self.plot = PyQtLabGraphWidget(
    plot_container=self.ui.plotContainer,       # Anchor QWidget for the main plot
    toolbar_container=self.ui.toolbarContainer, # Anchor QWidget for the toolbar (optional)
    legend_container=self.ui.legendContainer,   # Anchor QWidget for the legend (optional)
    plot_identifier="my-unique-plot-id",        # Identifier key for layout persistence
    layout_path=Path("plot_layouts.json"),       # Target layout file (optional)
    show_toolbar=True,                           # Show toolbar (default: True)
    show_legend=True,                            # Show legend (default: True if container present)
    legend_orientation=Qt.Orientation.Horizontal,# Horizontal or Vertical legend
    rolling_window_size=300.0,                   # Initial rolling X window size (default: 300.0)
    theme="dark",                                # Initial theme (default: neutral/light)
    plot_style="dark",                           # Initial curve style palette (default: light)
    show_component_frames=True,                  # Draw fallback border frames if no stylesheet exists
)
```

### Constructor Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `plot_container` | `QWidget` | *Required* | Host widget that will contain the embedded Pyqtgraph canvas. |
| `toolbar_container` | `QWidget` | `None` | Host widget where the custom toolbar will be injected. |
| `legend_container` | `QWidget` | `None` | Host widget where the legend will be injected. |
| `plot_identifier` | `str` | *Required* | Stable, unique key for the plot. Crucial for JSON layout file mapping. |
| `layout_path` | `str` \| `Path` | `None` | Path to the layout save file. Activates auto layout features. |
| `show_toolbar` | `bool` | `True` | If `False`, disables creation of the toolbar even if a container is supplied. |
| `show_legend` | `bool` | `None` | Overrides legend display. Defaults to `True` if `legend_container` is given. |
| `legend_orientation` | `Qt.Orientation` | `Qt.Orientation.Vertical` | Orientation of legend items: `Qt.Orientation.Vertical` or `Qt.Orientation.Horizontal`. |
| `rolling_window_size` | `float` | `300.0` | Initial width of the rolling X-window. |
| `theme` | `str` \| `PyQtLabGraphTheme` | `None` | Active background/grid theme name (`"light"`, `"dark"`, `"light-solarized"`, `"dark-solarized"`). |
| `plot_style` | `str` \| `PyQtLabGraphPlotStyle` | `None` | Active curve styling palette name (`"light"`, `"dark"`, `"solarized"`). |
| `show_component_frames` | `bool` | `True` | Draw palette-aware layout frames around containers in the absence of a global stylesheet. |

---

## Core Plotting Methods

Use these methods to manage curves and feed data into the widget:

* **`plot(key: str, x: ArrayLike, y: ArrayLike = None, label: str = None, style: CurveStyle = None)`**  
  Primary entry point. Creates or updates a curve identified by `key`. If `x` is the only array passed, it's treated as Y-data with X generated as indices.
* **`add_curve(key: str, label: str = None, style: CurveStyle = None)`**  
  Registers a new curve key without passing data. Used to initialize legend entries early.
* **`set_data(key: str, x: ArrayLike = None, y: ArrayLike = None, **kwargs)`**  
  Updates coordinates of an existing curve `key`. Safe to pass `x` and `y` separately. Supports keyword parameters mapping to `pyqtgraph.PlotDataItem.setData(...)`.
* **`add_point(key: str, x: float, y: float)`**  
  Appends a single data point to the curve. Extremely useful for real-time live sensor updates.
* **`curve_data(key: str) -> tuple[np.ndarray, np.ndarray]`**  
  Retrieves current coordinates stored in the underlying PyQtGraph `PlotDataItem` for the curve.
* **`curve_style(key: str) -> CurveStyle`**  
  Returns the current curve style object.
* **`set_curve_style(key: str, style: CurveStyle)`**  
  Applies a new `CurveStyle` to the given curve.
* **`set_curve_visible(key: str, visible: bool)`**  
  Toggles rendering of the curve in the canvas and marks its checkbox state in the legend.

---

## Layout & Customization Methods

Configure views, axes, limits, and serialize settings:

* **`set_axis_labels(x_label: str, y_label: str, x_units: str = None, y_units: str = None, x_mode: AxisMode = None, y_mode: AxisMode = None)`**  
  Updates axis titles, units, and tick representation modes (`AxisMode.AUTO`, `AxisMode.LINEAR`, `AxisMode.TIME`).
* **`get_x_range() -> tuple[float, float]`** / **`get_y_range() -> tuple[float, float]`**  
  Gets active viewport limits.
* **`apply_manual_x_limits(xmin: float, xmax: float)`** / **`apply_manual_y_limits(ymin: float, ymax: float)`**  
  Manually sets limits, deactivating automatic scaling or rolling window modes.
* **`request_rolling_x(enabled: bool)`**  
  Enables/disables the rolling X-window.
* **`set_rolling_window_size(size: float)`**  
  Updates the rolling window size.
* **`request_autoscale_x()`** / **`request_autoscale_y()`**  
  Instantly scales the corresponding axis to fit the current visible data bounds.
* **`request_show_all()`**  
  Rescales both axes to fit all data.
* **`set_theme(theme: str | PyQtLabGraphTheme)`**  
  Applies a background/grid theme.
* **`set_plot_style(style: str | PyQtLabGraphPlotStyle)`**  
  Sets the active plot style palette for new curves.
* **`apply_plot_style(style: str | PyQtLabGraphPlotStyle)`**  
  Updates all existing curves to use the color palette of the target plot style.
* **`save_layout()`** / **`load_layout()`**  
  Manually writes/restores layout state to/from the file set in `layout_path`.
* **`show_customize_dialog(curve_key: str = None)`**  
  Launches the modeless Customize dialog. If `curve_key` is supplied, it opens directly on the tab editing that curve.

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
