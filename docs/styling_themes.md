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

## Curve Palettes and Continuous Gradients

Curve palettes change only line colors. They are independent of the plot theme
and cycle when there are more curves than colors. `default-light` is active
unless the host selects another palette:

```python
plot.set_curve_palette("okabe-ito")
plot.set_curve_palette("default-light")
```

Built-ins include Default Light/Dark, Solarized, Okabe–Ito, Matplotlib Tab10
and Petroff10, Seaborn Colorblind, Paul Tol Bright/Muted, and Plotly Safe.
The Customize dialog combines palettes and gradients in one grouped dropdown:
categorical palettes appear under a `Categorical palettes` heading and
continuous gradients under `Continuous gradients`. The shared Reverse control
updates either kind of selection; for a categorical palette, the direction is
persistent for current and new curves. Palette entries show the first six
categorical colors as discrete swatches directly beside each name.
Their published values come from the
[Matplotlib](https://matplotlib.org/stable/gallery/color/color_sequences.html),
[Seaborn](https://seaborn.pydata.org/tutorial/color_palettes.html),
[Paul Tol](https://sronpersonalpages.nl/~pault/),
[Plotly](https://plotly.com/python/discrete-color/), and
[Okabe–Ito](https://jfly.uni-koeln.de/color/) references.

Continuous gradients are one-shot color assignments rather than live bindings:

```python
plot.apply_curve_gradient(
    "viridis",
    values={"20C": 20.0, "35C": 35.0, "80C": 80.0},
    value_range=(20.0, 80.0),
)
```

Without `values`, current curves are distributed evenly by curve order.
Viridis, Cividis, Plasma, Inferno, Magma, Turbo, Coolwarm, RdBu, BrBG, and the
cyclic Twilight gradient are built in. The Customize dropdown shows each
continuous gradient directly and can reverse both its preview and assignment.
Hosts can also use a gradient's `color_at()` and `sample()` methods directly.

---

## Custom Themes and Curve Palettes

Host-defined appearance values use an explicit registry. Every registry starts
with the built-ins and remains independent from other registries:

```python
from PySide6.QtGui import QColor
from pyqtlabgraph import (
    PyQtLabGraphCurvePalette,
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
registry.register_curve_palette(
    PyQtLabGraphCurvePalette(name="laboratory-curves", colors=("#abcdef", "#fedcba"))
)

plot = PyQtLabGraphWidget(
    plot_identifier="custom-style",
    style_registry=registry,
    theme="LABORATORY",
    curve_palette="laboratory-curves",
)
```

Names resolve case-insensitively. Duplicate names are rejected, and an object
passed directly to a widget must equal the registered value under its name.
Registered values appear in the Customize dialog.

Layout restoration resolves saved theme and curve-palette names through the
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
