from __future__ import annotations

from typing import Any, TYPE_CHECKING
import numpy as np
import pyqtgraph as pg

from .models import CurveState
from .styles import CurveStyle

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


class CurveManager:
    """Manages the dictionary of curves and handles data mutation."""

    def __init__(self, widget: PyQtLabGraphWidget) -> None:
        self._widget = widget
        self.curves: dict[str, CurveState] = {}
        self.curve_order: list[str] = []

    def add_curve(
        self,
        key: str,
        *,
        label: str | None = None,
        color: str | None = None,
        style: CurveStyle | None = None,
    ) -> pg.PlotDataItem:
        if key in self.curves:
            raise ValueError(f'Curve "{key}" already exists.')
        curve_style = self._widget.style_controller.default_curve_style(len(self.curve_order), color)
        if style is not None:
            curve_style = style

        try:
            item = pg.PlotDataItem(
                [],
                [],
                name=label or key,
                antialias=self._widget.render_optimizer.effective_antialiasing_enabled(),
                useCache=self._widget.render_optimizer.marker_cache_enabled(),
            )
            self._widget.plot_item.addItem(item)
        except Exception as exc:
            raise RuntimeError(f"Failed to create plot curve '{key}': {exc}") from exc

        curve = CurveState(key=key, label=label or key, item=item, style=curve_style)
        
        try:
            self._widget.render_optimizer._apply_curve_rendering_options(curve)
            self._widget.style_controller.apply_curve_style(curve)
            
            self.curves[key] = curve
            self.curve_order.append(key)
            self._widget._refresh_legend()
        except Exception:
            self._widget.plot_item.removeItem(item)
            raise
            
        return item

    def add_point(self, key: str, x_value: float, y_value: float) -> None:
        curve = self.get_curve(key)
        x_values, y_values = self.get_curve_data(curve)
        curve.item.setData(
            np.append(x_values, x_value),
            np.append(y_values, y_value),
        )
        self._widget.apply_axis_scaling()

    def set_data(self, key: str, *args: Any, **kwargs: Any) -> None:
        x_val = None
        y_val = None
        if len(args) >= 2:
            x_val = args[0]
            y_val = args[1]
        elif len(args) == 1:
            y_val = args[0]
        
        if "x" in kwargs:
            x_val = kwargs["x"]
        if "y" in kwargs:
            y_val = kwargs["y"]

        if x_val is not None and y_val is not None:
            try:
                len_x = len(x_val)
                len_y = len(y_val)
                if len_x != len_y:
                    raise ValueError(f"x and y must have the same length, got {len_x} and {len_y}")
            except TypeError:
                pass

        curve = self.get_curve(key)
        curve.item.setData(*args, **kwargs)
        self._widget.render_optimizer._apply_curve_rendering_options(curve)
        self._widget.style_controller.apply_curve_style(curve)
        self._widget.apply_axis_scaling()

    def plot(
        self,
        key: str,
        *args: Any,
        label: str | None = None,
        color: str | None = None,
        style: CurveStyle | None = None,
        **kwargs: Any,
    ) -> pg.PlotDataItem:
        item = self.add_curve(key, label=label, color=color, style=style)
        self.set_data(key, *args, **kwargs)
        return item

    def curve_data(self, key: str) -> tuple[np.ndarray, np.ndarray]:
        return self.get_curve_data(self.get_curve(key))

    def curve_item(self, key: str) -> pg.PlotDataItem:
        return self.get_curve(key).item

    def clear_curve(self, key: str) -> None:
        curve = self.get_curve(key)
        curve.item.setData([], [])
        self._widget.apply_axis_scaling()

    def remove_curve(self, key: str) -> None:
        curve = self.get_curve(key)
        self._widget.plot_item.removeItem(curve.item)
        del self.curves[key]
        self.curve_order.remove(key)
        self._widget._refresh_legend()
        self._widget.apply_axis_scaling()

    def set_curve_style(self, key: str, style: CurveStyle) -> None:
        curve = self.get_curve(key)
        curve.style = style
        self._widget.style_controller.apply_curve_style(curve)

    def curve_style(self, key: str) -> CurveStyle:
        return self.get_curve(key).style

    def set_curve_visible(self, key: str, visible: bool) -> None:
        curve = self.get_curve(key)
        curve.visible = visible
        curve.item.setVisible(visible)
        self._widget._update_legend_curve(key)
        self._widget.apply_axis_scaling()

    def get_curve(self, key: str) -> CurveState:
        try:
            return self.curves[key]
        except KeyError as exc:
            raise KeyError(f'Curve "{key}" does not exist.') from exc

    def get_curve_data(self, curve: CurveState) -> tuple[np.ndarray, np.ndarray]:
        x_values, y_values = curve.item.getOriginalDataset()
        if x_values is None or y_values is None:
            return np.array([]), np.array([])
        return x_values, y_values
