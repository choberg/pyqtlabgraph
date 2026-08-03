# PyQtLabGraph

[![PyPI version](https://img.shields.io/pypi/v/pyqtlabgraph.svg)](https://pypi.org/project/pyqtlabgraph/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/pyqtlabgraph.svg)](https://pypi.org/project/pyqtlabgraph/)
[![CI](https://github.com/choberg/pyqtlabgraph/actions/workflows/ci.yml/badge.svg)](https://github.com/choberg/pyqtlabgraph/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful, interactive, and polished live plotting library for **PySide6/Qt6**, based on **PyQtGraph**.

`PyQtLabGraph` is built for both interactive scientific data analysis and high-performance real-time visualization, providing an embeddable plot widget, dedicated toolbars, external legend layouts, smart axis formatting, layout persistence, and modern, explicit visual themes.

**Development status:** PyQtLabGraph is an alpha-stage 0.x project. Public APIs
and saved layout formats may change between minor releases before 1.0.

### Previews

| Light Theme (Default) | Dark Theme |
| :---: | :---: |
| ![PyQtLabGraph Light Theme](https://raw.githubusercontent.com/choberg/pyqtlabgraph/main/docs/screenshot_light.png) | ![PyQtLabGraph Dark Theme](https://raw.githubusercontent.com/choberg/pyqtlabgraph/main/docs/screenshot_dark.png) |

| Modeless Customize Dialog | Modular Widget Layout |
| :---: | :---: |
| ![PyQtLabGraph Customize Dialog](https://raw.githubusercontent.com/choberg/pyqtlabgraph/main/docs/screenshot_customize_dialog.png) | ![PyQtLabGraph Modular Layout Diagram](https://raw.githubusercontent.com/choberg/pyqtlabgraph/main/docs/screenshot_layout_labeled.png) <br> **[1]** Plot Widget &bull; **[2]** External Legend Widget &bull; **[3]** Plot Toolbar Widget |

| Cursor Inspector and Measurements |
| :---: |
| ![PyQtLabGraph Cursor Inspector](https://raw.githubusercontent.com/choberg/pyqtlabgraph/main/docs/screenshot_cursor_widget.png) |

---

## Why PyQtLabGraph? (Aesthetic & Usability Philosophy)

The Python plotting ecosystem is broad, ranging from publication-focused libraries to high-performance interactive toolkits. Two useful reference points are:
- **Matplotlib**: Excellent for static, publication-quality figures, but often heavy or sluggish when handling interactive real-time telemetry or rapid live data streams.
- **PyQtGraph**: An exceptionally fast Qt-based plotting library built for high-performance visualization, while deliberately leaving application-level UI chrome such as toolbars, legends, customize dialogs, and layout persistence to the developer.

`PyQtLabGraph` builds on the interactive-performance side of this landscape and adds the application-level workflow pieces that PyQtGraph intentionally leaves to host applications. It is designed as a **high-productivity, instrument-grade plotting interface** that brings the ease of use of traditional graphical programming environments to Python.

Many scientists, laboratory engineers, and researchers are familiar with the instant, out-of-the-box utility of instruments and classic engineering software platforms (such as LabVIEW), where plotting components come pre-packaged with zoom controls, custom legends, scaling tools, and runtime style editors. PyQtLabGraph brings this workflow to a clean, pythonic PySide6 package:

* **Familiar, Hardware-Like Controls**: The interface mimics the look, feel, and rapid utility of physical lab instruments (e.g., oscilloscopes, analyzers) and classic instrumentation software.
* **Instant Interactive Zooming & Panning**: Features intuitive mouse bindings (wheel zoom, key-constrained zooms) and double-click axis inputs out-of-the-box.
* **Rich Quality-of-Life (QoL) Features**: Includes a dedicated toolbar (X/Y locked zoom, autoscaling, live rolling window), a modeless live-preview Customize dialog, and complete JSON layout persistence.
* **Modern Aesthetic Themes**: Built-in themes (light, dark, solarized) independent of OS-level dark-mode checks, adapting naturally to the host application's active Qt style and palette.
* **Modular Widget Architecture & Qt Designer Support**: The plot, toolbar, legend, and cursor panel are independent Qt widgets. Host applications can lay them out freely or embed them in borderless layouts installed on **Qt Designer** placeholder widgets.


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
- **Cursor Widget**:
  - Adds movable X/Y cursors with a compact, host-styled inspector for cursor color, type, name, value, visibility, and optional snap target values.
  - Remains an optional standalone component that the host can place beside or below a plot, in a dock, or in any other Qt layout.
  - Supports direct cursor value editing, context-menu creation, deletion, and pairing, copyable rows, and a cursor settings dialog for name, visibility, labels, snapping, and line style.
  - X cursors can snap to a target curve and report the matching Y target value.
  - Cursor rows can be reordered by dragging between rows or dragged onto another cursor of the same axis to form a measurement pair. A pair is displayed as one draggable group containing two independently selectable cursor rows and a dedicated delta measurement bar. The group background selects both cursors for synchronous movement; the result eye controls the annotation, and its plot position can be dragged and persisted with the layout.
- **Integrated Toolbar**:
  - Action buttons for Show All, rectangle zoom, X-zoom, and Y-zoom.
  - Quick autoscale toggle for X and Y axes individually.
  - Rolling X-range display with custom size configuration.
  - Live PNG export and instant Customize dialog access.
- **Modeless Customize Dialog**:
  - Adjust titles, labels, units, axis formatting modes, and logarithmic scaling from grouped axis sections.
  - Toggle grids, global anti-aliasing, downsampling, clip-to-view, and adaptive performance.
  - Manage individual curves in per-curve tabs with grouped curve, line, and marker controls.
  - Edit line width, line colors, marker styles (circle, square, cross, diamond, etc.), size, and borders.
  - **Live Preview**: Axes, appearance, rendering, and curve edits preview immediately. View ranges preview explicitly through *Preview Range* or Enter so partially typed values do not move the plot.
  - **Clear Commit Actions**: *Apply & Close* keeps the current preview, *Save Layout* saves it without closing, and *Cancel* restores the state from when the dialog was opened or last saved.
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

PyQtLabGraph requires Python 3.11 or newer.

Install PyQtLabGraph from PyPI:

```bash
pip install pyqtlabgraph
```

Or install it directly from the repository source:

```bash
pip install .
```

For an editable development installation including the test, lint, type-check,
and build tools:

```bash
python3 -m pip install -e ".[dev]"
```

---

## Quick Start

Here is a minimal working example of embedding the `PyQtLabGraphWidget` inside a basic Qt window:

```python
import sys
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget
from pyqtlabgraph import (
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)

app = QApplication(sys.argv)
window = QMainWindow()
central = QWidget()
layout = QHBoxLayout(central)
window.setCentralWidget(central)
plot = PyQtLabGraphWidget(
    plot_identifier="quickstart_plot",
)
toolbar = PyQtLabGraphToolbar(plot)
legend = PyQtLabGraphLegend(plot, orientation=Qt.Orientation.Horizontal)
cursors = PyQtLabGraphCursorWidget(plot)

plot_column = QVBoxLayout()
plot_column.addWidget(toolbar)
plot_column.addWidget(plot, stretch=1)
plot_column.addWidget(legend)
layout.addLayout(plot_column, stretch=1)
layout.addWidget(cursors)

# Plot a simple sensor temperature curve
plot.plot(
    key="temp_sensor",
    x=[0, 1, 2, 3, 4, 5],
    y=[22.1, 22.4, 23.0, 22.8, 23.5, 24.1],
    label="Temperature",
)

# Set axis labels and units
plot.set_axis_labels(
    x_label="Time", x_units="s",
    y_label="Temperature", y_units="°C"
)

# Add editable cursors; every cursor panel follows plot signals.
plot.add_cursor("x", key="time_cursor", name="Time Cursor", value=2.0)
plot.add_cursor("y", key="temperature_cursor", name="Temperature Cursor", value=23.0)

window.resize(800, 600)
window.show()
sys.exit(app.exec())
```

Run the bundled examples directly from a source checkout:

* **Minimal Demo**:
  ```bash
  python examples/demo_minimal.py
  ```
* **Thermostat Simulation Demo**:
  ```bash
  python examples/demo_thermostat.py
  ```
* **Time Domain & FFT Demo**:
  ```bash
  python examples/demo_time_fft.py
  ```
* **Cursor Demo**:
  ```bash
  python examples/demo_cursor.py
  ```
  Shows the freely embeddable cursor widget as a right-hand inspector, including direct value editing, snapping to a target curve, cursor settings, deletion, pairing, and layout persistence.

Every demo starts in Light mode. Use **View → Dark mode** to switch the host
application, plot background, and curve palette together. The demos use Qt
Fusion with explicit Light and Dark palettes so interactive theme changes remain
consistent across supported platforms.

---

## Detailed Documentation

- 📖 [API Reference](https://github.com/choberg/pyqtlabgraph/blob/main/docs/api_reference.md): Complete details on classes, parameters, and methods.
- 🧭 [Architecture](https://github.com/choberg/pyqtlabgraph/blob/main/docs/architecture.md): Ownership, component boundaries, update flow, and regression guardrails.
- 🎨 [Visual Styling & Themes](https://github.com/choberg/pyqtlabgraph/blob/main/docs/styling_themes.md): Built-in themes, plot styles, and integrating with host stylesheets.
- ⚡ [Performance Optimization](https://github.com/choberg/pyqtlabgraph/blob/main/docs/performance.md): Downsampling, clip-to-view, and adaptive rendering mechanics.

---

## Project Structure

```
├── pyqtlabgraph/            # Main library package
│   ├── __init__.py          # Public exports & versioning
│   ├── widget.py            # Main PyQtLabGraphWidget and API wrapping
│   ├── dispatch.py          # Ordered updates, coalescing, and atomic resets
│   ├── runtime_state.py     # Exact runtime snapshots for rollback
│   ├── curve_manager.py     # Curve metadata, data, and PlotDataItem lifecycle
│   ├── range_controller.py  # Autoscale, rolling, and manual range policy
│   ├── render_optimizer.py  # Rendering flags and Adaptive Performance
│   ├── style_controller.py  # Plot-owned theme and curve appearance
│   ├── cursor_controller.py # Cursor commands, selection, batching, and signals
│   ├── cursor_manager.py    # Cursor state, snapping, pairs, and data caches
│   ├── cursor_presenter.py  # Plot graphics, annotations, and label layout
│   ├── cursor_plot_items.py # PyQtGraph InfiniteLine cursor adapters
│   ├── cursor_widget.py     # Public cursor panel and user-intent handling
│   ├── cursor_list_model.py # Read projection plus typed edit/drop intents
│   ├── cursor_ui.py         # Shared cursor UI records, roles, and geometry
│   ├── cursor_delegate.py   # Host-styled cursor row painting and editors
│   ├── cursor_actions.py    # Cursor context-menu and action construction
│   ├── cursor_settings.py   # Cursor settings dialog
│   ├── dialogs.py           # Modeless Customize dialog composition
│   ├── customize_controls.py # Customize controls and curve editors
│   ├── customize_session.py # Customize preview, save, and rollback session
│   ├── layouts.py           # Layout DTOs, strict codec, storage, and reconciliation
│   ├── toolbar.py           # Toolbar buttons, export, and mode controllers
│   ├── legend.py            # External interactive PyQtLabGraphLegend
│   ├── axis.py              # SmartAxisItem tick formatting implementation
│   ├── models.py            # Core dataclasses (CurveState, InteractionState)
│   ├── styles.py            # Curve style configurations and palettes
│   ├── themes.py            # Background themes and color registries
│   ├── style_registry.py     # Explicit built-in and custom style resolution
│   ├── qt_styles.py         # Palette-aware native frame painting
│   └── assets/              # PNG icon assets used by the toolbar
├── docs/                    # Detailed user-facing documentation
├── tests/                   # Pytest, smoke, architecture, and wheel checks
├── examples/                # Source-checkout demos and examples
├── .github/workflows/       # CI and release workflows
└── pyproject.toml           # Build system and package metadata
```

---

## Development & Verification

Install the project in editable mode with its development tools:

```bash
python3 -m pip install -e ".[dev]"
```

Run the complete local verification suite after changes:

```bash
python3 -m pytest -q
python3 tests/run_smoke_checks.py
ruff check pyqtlabgraph tests examples
mypy pyqtlabgraph
python3 -m build
```

CI runs the same checks on Python 3.11, 3.12, and 3.13. It also installs the
built wheel into a clean virtual environment and verifies public exports,
version metadata, typing metadata, and runtime PNG assets.

---

## License

This project is licensed under the MIT License - see the `LICENSE` file for details.
