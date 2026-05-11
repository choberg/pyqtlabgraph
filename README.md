# PyQtLabGraph

A powerful interactive live plotting widget for PySide6/Qt6, based on PyQtGraph.

`PyQtLabGraph` is designed for real-time scientific data visualization, with a focus on usability, performance, and smart axis formatting.

## Features

- **Real-time plotting**: Optimized for live data streams such as sensor data.
- **Smart axes (`SmartAxisItem`)**:
  - **Auto**: Standard SI-prefix scaling (`k`, `M`, `m`).
  - **Linear**: Raw values with units, useful for quantities such as wavenumbers or temperatures.
  - **Time**: Adaptive formatting of seconds as `d h min s` while zooming.
- **Interactive legend**: Click curves to show or hide them, or double-click to edit curve styles directly.
- **Integrated toolbar**:
  - Mouse panning as the default interaction, plus rectangle zoom, X-zoom, and Y-zoom tools.
  - Rolling window support using the current X range, fixed X units, or a custom width.
  - Show All button and PNG export.
- **Fully configurable**: Modeless customize dialog for plot background, plot style, colors, line styles, markers, ranges, rendering flags, grid, and axis settings. Most changes are previewed immediately and restored on Cancel.
- **Layout persistence**: Save and load customize dialog settings from an explicit JSON layout file, with one entry per code-defined plot identifier and optional restoration of saved view state such as zoom, autoscale, and rolling mode.
- **Adaptive rendering**: Optional automatic simplification for dense views; when many points are visible, PyQtLabGraph temporarily disables markers and antialiasing, then restores them when fewer points are visible again.
- **Configurable themes**: Built-in `light`, `dark`, `light-solarized`, and `dark-solarized` themes for PyQtLabGraph-owned plot data area and grid.
- **Configurable plot styles**: Built-in `light`, `dark`, and `solarized` plot styles for curve colors, line widths, and markers.

## Installation

Install directly from this repository:

```bash
pip install .
```

For local development, dependencies can also be installed directly:

```bash
pip install PySide6 pyqtgraph
```

## Quick Start

Run the minimal working example with one plot, toolbar, legend, and 100 random points:

```bash
python demo_minimal.py
```

Run the larger thermostat demo from the repository root to explore more features:

```bash
python demo_thermostat.py
```

This demo loads `demo_thermostat.ui` and uses the `plotContainer`,
`toolbarContainer`, and `legendContainer` widgets as anchors for the plot,
toolbar, and legend. PyQtLabGraph themes are scoped to the plot content;
dialogs, plot frame chrome, toolbar chrome, legend chrome, and the rest of the
demo UI keep the normal Qt/platform styling.

Run the time-domain and FFT demo to see two independent plots with their own
toolbars and legends:

```bash
python demo_time_fft.py
```

This demo loads `demo_time_fft.ui` and shows a Qt Designer layout with two
framed plot sections. Each section provides normal Qt mountpoint widgets for
the plot, legend, and toolbar while PyQtLabGraph's internal component frames
are disabled.

Plot background and plot style selection live in the customize dialog rather
than in the demo main window. The dialog is modeless, so the main window remains
usable while it is open.

An optional qdarktheme comparison demo is also available when PyQtDarkTheme is
installed in the environment:

```bash
python demo_thermostat_qdarktheme.py
```

## Library Usage

```python
from pathlib import Path

from pyqt_lab_graph import AxisMode, CurveStyle, PyQtLabGraphWidget

# Initialize the widget, for example inside a QMainWindow.
self.plot = PyQtLabGraphWidget(
    plot_container=self.ui.plotContainer,
    toolbar_container=self.ui.toolbarContainer,
    legend_container=self.ui.legendContainer,
    plot_identifier="main-plot",
    layout_path=Path("my_app_plot_layout.json"),
    rolling_window_size=300.0,
    theme="light",
    plot_style="light",
    show_component_frames=True,
)

# Configure axes.
# PyQtLabGraph starts with neutral X/Y labels; set domain labels explicitly.
self.plot.set_axis_labels("Time", "Voltage", "s", "V", x_mode=AxisMode.TIME)

# Plot data using pyqtgraph-style data arguments.
self.plot.plot("sensor_1", x_values, y_values, label="Temperature sensor")
self.plot.plot("sensor_2", y_values, label="Reference", style=CurveStyle(line_color="#D55E00"))
self.plot.load_layout()

# Replace data on an existing curve using the same argument forms as
# pyqtgraph.PlotDataItem.setData(...).
self.plot.set_data("sensor_1", x=new_x_values, y=new_y_values)

# Update a curve style.
self.plot.set_curve_style(
    "sensor_1",
    CurveStyle(line_color="#0072B2", line_width=1.5, marker_symbol="o"),
)

# Add data.
self.plot.add_point("sensor_1", x_value, y_value)

# Read original curve data from the underlying pyqtgraph PlotDataItem.
x_values, y_values = self.plot.curve_data("sensor_1")

# Advanced pyqtgraph access remains available when needed.
self.plot.native_plot_item.addItem(custom_item)
sensor_item = self.plot.curve_item("sensor_1")

# Change the plot theme.
self.plot.set_theme("dark")

# Change the plot style for new curves or explicitly apply it to existing curves.
self.plot.set_plot_style("dark")
self.plot.apply_plot_style("dark")

# Save or reload the current plot layout explicitly.
self.plot.save_layout()
self.plot.load_layout()
```

The top-level package exports the main public embedding API: `PyQtLabGraphWidget`,
`CurveStyle`, plot/theme data types, built-in plot styles/themes, `AxisMode`,
and `LayoutFileError`.
Advanced implementation components such as the toolbar, legend, axis item, and
style/theme resolvers remain available from their specific submodules when
needed.
Application code should use the widget methods such as `add_curve`,
`plot`, `set_data`, `curve_data`, `add_point`, `curve_item`, `curve_style`, and
`set_curve_style`; direct access to widget internals such as `.curves` is not
part of the recommended API. Curve data is owned by the underlying pyqtgraph
`PlotDataItem`; PyQtLabGraph reads it back when autoscale, rolling ranges, or
adaptive rendering need it.
Each `PyQtLabGraphWidget` needs a stable `plot_identifier` set by application
code. When `layout_path` is provided, the Customize dialog's `Apply + Save`
button writes this plot's layout into that shared JSON file without touching
other plot identifiers in the same file. Call `load_layout()` after adding the
curves that should receive saved visibility and style settings.
Axis modes can be passed as `AxisMode` values or as the strings `"auto"`,
`"linear"`, and `"time"`.

## Advanced pyqtgraph Access

PyQtLabGraph intentionally keeps escape hatches for advanced pyqtgraph users.
Use `native_plot_widget`, `native_plot_item`, and `native_view_box` when a
configuration is not covered by the PyQtLabGraph API. Use `curve_item(key)` when
you need the underlying `pyqtgraph.PlotDataItem` for a registered curve.

```python
graph.native_view_box.setLimits(xMin=0.0)
graph.native_plot_item.addItem(custom_item)
graph.curve_item("sensor_1").setClickable(True)
```

PyQtLabGraph still owns plot content theme application, plot-style application,
axis label text, grid styling, autoscale/rolling range behavior, and adaptive rendering.
Axis label color, tick label color, axis lines, and tick marks follow the host
Qt palette.
Direct pyqtgraph changes in those areas may be overwritten when PyQtLabGraph
reapplies its state.

## Host Application Styling

The customize dialog, plot frame chrome, toolbar chrome, legend chrome, and
toolbar menus use the active Qt application style instead of PyQtLabGraph-specific
color stylesheets. Host applications can style them through normal Qt mechanisms
such as an application stylesheet, qdarktheme, or qt-material. When no host
stylesheet is present, PyQtLabGraph applies a small palette-based fallback frame
around the plot, toolbar, and legend containers.
Pass `show_component_frames=False` when the host application should provide one
shared outer frame around a custom layout containing plot, toolbar, and legend.

Only the pyqtgraph `ViewBox` data area receives the selected plot background.
The surrounding plot widget stays transparent so the host-styled outer frame
remains visible. PyQtLabGraph slightly extends the `ViewBox` background to cover
pyqtgraph's right and bottom edge pixels without painting the full widget.

Toolbar icons are packaged PNG masks that PyQtLabGraph recolors from the
toolbar's current Qt palette. When the application style or palette changes,
the toolbar regenerates its icons so they match the host application's dark or
light mode. Legend curve samples remain PyQtLabGraph-owned because they show
the configured curve styles.

## Rendering Performance

PyQtLabGraph uses PyQtGraph's built-in rendering features such as downsampling
and clip-to-view. These can be toggled in the customize dialog.

Adaptive rendering is a PyQtLabGraph layer on top of that. It is enabled by
default and watches the number of visible points. When a dense view crosses the
internal activation threshold, PyQtLabGraph temporarily disables markers and
antialiasing because those are expensive visual details. When the visible point
count drops below the restore threshold, the configured marker and antialiasing
settings are applied again.

This feature does not require sorted X values and does not change curve data.
Scatter-style data with arbitrary X ordering remains supported.

## Development

Run the development smoke checks:

```bash
python3 tests/run_smoke_checks.py
```

The runner performs the package/demo/test syntax check without writing bytecode
cache files and executes the standalone smoke tests. Individual smoke tests
remain directly executable, for example:

```bash
QT_QPA_PLATFORM=offscreen python3 tests/smoke_adaptive_performance.py
```

Install the package locally in editable mode:

```bash
pip install -e .
```

## Project Structure

- `pyqt_lab_graph/`: Installable Python package.
- `pyqt_lab_graph/widget.py`: Main widget and public plotting API.
- `pyqt_lab_graph/dialogs.py`: Modeless customize dialog for plot background, plot style, axes, grid, ranges, rendering flags, and curve styles.
- `pyqt_lab_graph/layouts.py`: Versioned JSON layout helpers and internal plot state snapshots.
- `pyqt_lab_graph/toolbar.py`: Toolbar, navigation, export, and rolling-window controls.
- `pyqt_lab_graph/legend.py`: External Qt legend with curve visibility and style access.
- `pyqt_lab_graph/axis.py`: `SmartAxisItem` and axis modes.
- `pyqt_lab_graph/models.py`: Internal data models.
- `pyqt_lab_graph/themes.py`: Theme data model, built-in themes, and theme registry.
- `pyqt_lab_graph/qt_styles.py`: Minimal Qt stylesheet helpers for fallback frames and transparent plot-widget chrome.
- `pyqt_lab_graph/styles.py`: Plot style data model, built-in plot styles, and curve-related style constants.
- `pyqt_lab_graph/assets/`: Runtime PNG toolbar icons shipped with the package.
- `original_icons/`: Source/original icon assets that are not packaged as runtime assets.
- `tests/`: Standalone smoke tests and the lightweight development smoke runner.
- `demo_minimal.py`: Minimal working example with one random plot.
- `demo_thermostat.py`: Demo application with simulated thermostat data.
- `demo_time_fft.py`: Demo application with a time-domain signal and its FFT in two plots.
- `demo_time_fft.ui`: Qt Designer file for the time-domain and FFT demo layout.
- `demo_thermostat_qdarktheme.py`: Demo application variant using qdarktheme as the host application style.
- `demo_thermostat.ui`: Qt Designer file for the thermostat demo.
- `bak/`: Backups of replaced or moved files.
- `pyproject.toml`: Package metadata and explicit runtime asset package data.

## License

This project is licensed under the MIT License. It permits use, modification, and redistribution as long as the copyright and license notice are preserved.
