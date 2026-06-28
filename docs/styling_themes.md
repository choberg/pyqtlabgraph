# Visual Styling & Themes

PyQtLabGraph separates plot canvas styling (backgrounds, gridlines) from curve styling (colors, markers, line widths).

---

## Themes

A theme governs the plot data canvas, background, and gridlines:
* `light`: Neutral light background with grey gridlines.
* `dark`: High-contrast dark grey/black background.
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

To set the default plot style for new curves:
```python
self.plot.set_plot_style("solarized")
```

---

## Host Application Styling

PyQtLabGraph widgets are transparent outside the `ViewBox` canvas. All surrounding chrome (toolbar buttons, external legend container, customize dialog, pop-up menus) inherits the host Qt application's active style.

The Customize dialog is organized around plot-owned settings, but it remains a normal host-styled Qt dialog. Plot themes affect only the plot data area and grid; they do not restyle dialog controls, toolbar chrome, legend chrome, menus, or application windows.

You can apply modern styling frameworks to your host application (like `qdarktheme` or `QCommonStyle`), and PyQtLabGraph's chrome will adapt automatically:

```python
# Example: Using qdarktheme for the main host application
import qdarktheme

app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
```

The toolbar's packaged PNG masks will automatically adapt to match light/dark icon palettes of the active Qt window style.
