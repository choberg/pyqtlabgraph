# PyQtLabGraph

[![PyPI version](https://img.shields.io/pypi/v/pyqtlabgraph.svg)](https://pypi.org/project/pyqtlabgraph/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pyqtlabgraph.svg)](https://pypi.org/project/pyqtlabgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful, interactive, and premium live plotting library for **PySide6/Qt6**, based on **PyQtGraph**.

`PyQtLabGraph` is built specifically for real-time scientific data visualization, providing an embeddable plot widget, dedicated toolbars, external legend layouts, smart axis formatting, layout persistence, and modern, explicit visual themes.

---

## Table of Contents

- [Features](#features)
- [Interactive Controls](#interactive-controls)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [PyQtLabGraphWidget Constructor](#pyqtlabgraphwidget-constructor)
  - [Core Plotting Methods](#core-plotting-methods)
  - [Layout & Customization Methods](#layout--customization-methods)
- [Advanced pyqtgraph Access](#advanced-pyqtgraph-access)
- [Visual Styling & Themes](#visual-styling--themes)
  - [Themes](#themes)
  - [Plot Styles](#plot-styles)
  - [Host Application Styling](#host-application-styling)
- [Performance Optimization](#performance-optimization)
- [Project Structure](#project-structure)
- [Development & Verification](#development--verification)
- [License](#license)

---

## Features

- **Real-Time Plotting**: High-performance rendering optimized for rapid updates, live sensor streams, or fast oscilloscope-style displays.
- **Smart Axis Formatting (`SmartAxisItem`)**:
  - `AUTO`: Automatic SI-prefix scaling (e.g., scaling raw Hertz to `kHz` / `MHz` / `GHz`).
  - `LINEAR`: Explicit raw values with user-defined units, bypassing auto-scaling.
  - `TIME`: Adaptive relative time formatting displaying seconds formatted elegantly as `d h min s` depending on zoom level.
- **Dedicated External Legend (`PyQtLabGraphLegend`)**:
  - Displays curve symbols, colors, and labels.
  - Interactive: Double-click a curve's legend item to open the Customize dialog immediately focused on that curve. Single-click to toggle curve visibility.
  - Configurable orientation: Can be placed **vertically** (default) or **horizontally**.
- **Integrated Toolbar**:
  - Action buttons for Show All, rectangle zoom, X-zoom, and Y-zoom.
  - Quick autoscale toggle for X and Y axes individually.
  - Rolling X-range display with custom size configuration.
  - Live PNG export and instant Customize dialog access.
- **Modeless Customize Dialog**:
  - Adjust titles, labels, units, and axis formatting modes.
  - Toggle grids, global anti-aliasing, downsampling, clip-to-view, and adaptive performance.
  - Manage individual curves: toggling visibility, line width, line colors, marker styles (circle, square, cross, diamond, etc.), size, and borders.
  - **Live Preview**: All configuration edits preview immediately in the plot in real-time, and revert instantly if the user clicks *Cancel*.
- **Layout Persistence**: Save/Load all layout configurations (visual properties, themes, active ranges, curve states) to a shared versioned JSON file.
- **Adaptive Performance**: Automatic visual simplification when rendering very dense datasets to avoid UI lag.

---

## Interactive Controls

PyQtLabGraph introduces advanced viewport mouse controls on top of the standard PyQtGraph mouse interactions:

- **Mouse Drag (Left Click)**: Pans the view in the selected tool mode.
- **Mouse Drag (Right Click)**: Zooms X and Y scale dynamically (drag left/right for X, up/down for Y).
- **Mouse Wheel**: Zooms both X and Y axes centered on the cursor position.
- **Shift + Mouse Wheel**: Zooms **X-axis only**, preserving the Y-axis range.
- **Ctrl + Mouse Wheel**: Zooms **Y-axis only**, preserving the X-axis range.
- **Double Click Axis**: Opens a quick manual range pop-up directly underneath the cursor for entering exact values.

---

## Installation

Install PyQtLabGraph from PyPI:

```bash
pip install pyqtlabgraph
```

Or install it directly from the repository source:

```bash
pip install .
```

For development installations, make sure you have the runtime dependencies installed:

```bash
pip install PySide6 pyqtgraph
```

---

## Quick Start

You can check out how to use the library using the packaged demo files:

1. **Minimal Example** (One random walk curve, basic legend, and toolbar):
   ```bash
   python demo_minimal.py
   ```

2. **Thermostat Simulation Demo** (Realistic simulated heating/cooling loop, horizontal legend, showing toolbar states and custom styling integration):
   ```bash
   python demo_thermostat.py
   ```

3. **Time Domain & FFT Demo** (Two independent synchronized plots with separate controls):
   ```bash
   python demo_time_fft.py
   ```

4. **Host Application Styling Comparison** (Integrates with dark mode styling packages like `qdarktheme`):
   ```bash
   python demo_thermostat_qdarktheme.py
   ```

---

## API Reference

### PyQtLabGraphWidget Constructor

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

#### Constructor Parameters:
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

### Core Plotting Methods

Use these methods to manage curves and feed data into the widget:

- **`plot(key: str, x: ArrayLike, y: ArrayLike = None, label: str = None, style: CurveStyle = None)`**  
  Primary entry point. Creates or updates a curve identified by `key`. If `x` is the only array passed, it's treated as Y-data with X generated as indices.
- **`add_curve(key: str, label: str = None, style: CurveStyle = None)`**  
  Registers a new curve key without passing data. Used to initialize legend entries early.
- **`set_data(key: str, x: ArrayLike = None, y: ArrayLike = None, **kwargs)`**  
  Updates coordinates of an existing curve `key`. Safe to pass `x` and `y` separately. Supports keyword parameters mapping to `pyqtgraph.PlotDataItem.setData(...)`.
- **`add_point(key: str, x: float, y: float)`**  
  Appends a single data point to the curve. Extremely useful for real-time live sensor updates.
- **`curve_data(key: str) -> tuple[np.ndarray, np.ndarray]`**  
  Retrieves current coordinates stored in the underlying PyQtGraph `PlotDataItem` for the curve.
- **`curve_style(key: str) -> CurveStyle`**  
  Returns the current curve style object.
- **`set_curve_style(key: str, style: CurveStyle)`**  
  Applies a new `CurveStyle` to the given curve.
- **`set_curve_visible(key: str, visible: bool)`**  
  Toggles rendering of the curve in the canvas and marks its checkbox state in the legend.

---

### Layout & Customization Methods

Configure views, axes, limits, and serialize settings:

- **`set_axis_labels(x_label: str, y_label: str, x_units: str = None, y_units: str = None, x_mode: AxisMode = None, y_mode: AxisMode = None)`**  
  Updates axis titles, units, and tick representation modes (`AxisMode.AUTO`, `AxisMode.LINEAR`, `AxisMode.TIME`).
- **`get_x_range() -> tuple[float, float]`** / **`get_y_range() -> tuple[float, float]`**  
  Gets active viewport limits.
- **`apply_manual_x_limits(xmin: float, xmax: float)`** / **`apply_manual_y_limits(ymin: float, ymax: float)`**  
  Manually sets limits, deactivating automatic scaling or rolling window modes.
- **`request_rolling_x(enabled: bool)`**  
  Enables/disables the rolling X-window.
- **`set_rolling_window_size(size: float)`**  
  Updates the rolling window size.
- **`request_autoscale_x()`** / **`request_autoscale_y()`**  
  Instantly scales the corresponding axis to fit the current visible data bounds.
- **`request_show_all()`**  
  Rescales both axes to fit all data.
- **`set_theme(theme: str | PyQtLabGraphTheme)`**  
  Applies a background/grid theme.
- **`set_plot_style(style: str | PyQtLabGraphPlotStyle)`**  
  Sets the active plot style palette for new curves.
- **`apply_plot_style(style: str | PyQtLabGraphPlotStyle)`**  
  Updates all existing curves to use the color palette of the target plot style.
- **`save_layout()`** / **`load_layout()`**  
  Manually writes/restores layout state to/from the file set in `layout_path`.
- **`show_customize_dialog(curve_key: str = None)`**  
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

---

## Visual Styling & Themes

### Themes
A theme governs the plot data canvas, background, and gridlines:
- `light`: Neutral light background with grey gridlines.
- `dark`: High-contrast dark grey/black background.
- `light-solarized`: Classic solarized-cream aesthetic.
- `dark-solarized`: Deep blue-green solarized aesthetic.

```python
self.plot.set_theme("dark-solarized")
```

### Plot Styles
A plot style determines the palette (line colors, markers, widths) mapped to curves:
- `light`: Highly visible color cycle optimized for light background themes.
- `dark`: Vibrant color cycle optimized for dark background themes.
- `solarized`: Palette adhering to the solarized styling standard.

```python
self.plot.set_plot_style("solarized")
```

### Host Application Styling
PyQtLabGraph widgets are transparent outside the `ViewBox` canvas. All surrounding chrome (toolbar buttons, external legend container, customize dialog, pop-up menus) inherits the host Qt application's styling. You can apply modern styling frameworks to your host application (like `qdarktheme` or `QCommonStyle`), and PyQtLabGraph's chrome will adapt automatically:

```python
# Example: Recoloring toolbar icons based on host application style change
import qdarktheme
app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
```
The toolbar's packaged PNG masks will automatically adapt to match light/dark icon palettes of the active Qt window style.

---

## Performance Optimization

For dense, high-frequency datasets, PyQtLabGraph provides several levels of performance optimization:

1. **Downsampling**: Dynamically reduces the number of points drawn by grouping dense data points (activated via customize dialog).
2. **Clip to View**: Cuts off calculations for data coordinates lying outside the current visible X range (activated via customize dialog).
3. **Adaptive Rendering (Adaptive Performance)**:  
   When the number of visible points on the screen exceeds a high threshold (e.g., 20,000 points), PyQtLabGraph temporarily disables antialiasing and markers to maintain smooth panning and zooming. When you zoom back in and the point count falls below a lower threshold (e.g., 10,000 points), these detailed styling properties are automatically restored.

---

## Project Structure

```
├── pyqtlabgraph/            # Main library package
│   ├── __init__.py          # Public exports & versioning
│   ├── widget.py            # Main PyQtLabGraphWidget and API wrapping
│   ├── dialogs.py           # Modeless Customize dialog & popups
│   ├── layouts.py           # JSON Layout save/load mechanics
│   ├── toolbar.py           # Toolbar buttons, export, and mode controllers
│   ├── legend.py            # External interactive PyQtLabGraphLegend
│   ├── axis.py              # SmartAxisItem tick formatting implementation
│   ├── models.py            # Core dataclasses (CurveState, InteractionState)
│   ├── styles.py            # Curve style configurations and palettes
│   ├── themes.py            # Background themes and color registries
│   ├── qt_styles.py         # Standard fallback borders and QSS wrappers
│   └── assets/              # PNG icon assets used by the toolbar
├── tests/                   # Standalone smoke test suite
├── demo_minimal.py          # Getting started minimal walkthrough
├── demo_thermostat.py       # Main thermostat feature demo
├── demo_time_fft.py         # Grid/dual plot designer layout demo
└── pyproject.toml           # Build system and package metadata
```

---

## Development & Verification

Tests are located in the `tests/` directory and can be executed via a unified test runner. Run this command after any code changes to verify syntax, assets, and UI state:

```bash
python3 tests/run_smoke_checks.py
```

To run a specific smoke check, execute it directly with Qt configured in offscreen mode (useful for headless CI environments):

```bash
QT_QPA_PLATFORM=offscreen python3 tests/smoke_customize_dialog.py
```

---

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
