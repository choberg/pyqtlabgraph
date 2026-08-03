# Visual Styling & Themes

PyQtLabGraph separates plot canvas styling (backgrounds, gridlines) from curve styling (colors, markers, line widths).

---

## Themes

A theme governs the plot data canvas, background, and gridlines:
* `light`: Neutral light background with grey gridlines.
* `dark`: Cool blue-grey background with restrained high-contrast gridlines.
* `light-solarized`: Classic solarized-cream aesthetic.
* `dark-solarized`: Deep blue-green solarized aesthetic.

To apply a theme in your code:
```python
self.plot.set_theme("dark-solarized")
```

---

## Plot Styles

A plot style determines the palette (line colors, markers, widths) mapped to curves:
* `light`: Highly visible color cycle optimized for light background themes.
* `dark`: Vibrant color cycle optimized for dark background themes.
* `solarized`: Palette adhering to the solarized styling standard.

To apply a plot style to all current curves and use it for new curves:
```python
self.plot.set_plot_style("solarized")
```

---

## Custom Themes and Plot Styles

Host-defined appearance values use an explicit registry. Every registry starts
with the built-ins and remains independent from other registries:

```python
from PySide6.QtGui import QColor
from pyqtlabgraph import (
    CurveStyle,
    PyQtLabGraphPlotStyle,
    PyQtLabGraphStyleRegistry,
    PyQtLabGraphTheme,
    PyQtLabGraphWidget,
)

registry = PyQtLabGraphStyleRegistry()
registry.register_theme(
    PyQtLabGraphTheme(
        name="laboratory",
        plot_background="#102030",
        grid=QColor(200, 210, 220, 60),
        border="#405060",
    )
)
registry.register_plot_style(
    PyQtLabGraphPlotStyle(
        name="laboratory",
        curve_styles=(CurveStyle(line_color="#abcdef"),),
    )
)

plot = PyQtLabGraphWidget(
    plot_identifier="custom-style",
    style_registry=registry,
    theme="LABORATORY",
    plot_style="laboratory",
)
```

Names resolve case-insensitively. Duplicate names are rejected, and an object
passed directly to a widget must equal the registered value under its name.
Registered values appear in the Customize dialog.

Layout restoration resolves saved theme and plot-style names through the
target widget's registry. A custom registered appearance therefore round-trips
when the host supplies the same registry configuration before loading.

---

## Host Application Styling

PyQtLabGraph widgets are transparent outside the `ViewBox` canvas. All surrounding chrome (toolbar buttons, external legend container, cursor widget, customize dialog, pop-up menus) inherits the host Qt application's active style and palette.

The Customize dialog is organized around plot-owned settings, but it remains a normal host-styled Qt dialog. Plot themes affect only the plot data area and grid; they do not restyle dialog controls, toolbar chrome, legend chrome, menus, or application windows.

On Qt 6.8 and newer, a host can explicitly request Qt's native Dark or Light
color scheme:

```python
from PySide6.QtCore import Qt

app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
```

The request is a platform hint, so its result depends on the active Qt platform
and desktop style. The repository demos instead use Qt Fusion with explicit
Light and Dark QPalettes for deterministic interactive switching, without
adding an application-theme dependency. Each demo exposes the same
**View → Dark mode** action.

The toolbar's packaged PNG masks automatically adapt to the active
`ButtonText` palette color. PyQtLabGraph does not detect the operating-system
theme or impose an application-wide stylesheet.
