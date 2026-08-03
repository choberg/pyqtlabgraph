from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from numpy.typing import ArrayLike

from .models import CurveState
from .styles import CurveStyle


class CurveManager:
    """Owns curve metadata and the PlotDataItem lifecycle."""

    def __init__(self, plot_item: pg.PlotItem) -> None:
        self._plot_item = plot_item
        self.curves: dict[str, CurveState] = {}
        self.curve_order: list[str] = []

    def add_curve(
        self,
        key: str,
        *,
        label: str | None = None,
        style: CurveStyle,
    ) -> pg.PlotDataItem:
        if key in self.curves:
            raise ValueError(f'Curve "{key}" already exists.')

        try:
            item = pg.PlotDataItem([], [], name=label or key)
            self._plot_item.addItem(item)
        except Exception as exc:
            raise RuntimeError(f"Failed to create plot curve '{key}': {exc}") from exc

        curve = CurveState(key=key, label=label or key, item=item, style=style)
        self.curves[key] = curve
        self.curve_order.append(key)
        return item

    def add_point(self, key: str, x_value: float, y_value: float) -> None:
        curve = self.get_curve(key)
        x_values, y_values = self.get_curve_data(curve)
        curve.item.setData(
            np.append(x_values, x_value),
            np.append(y_values, y_value),
        )

    def set_data(
        self,
        key: str,
        x: ArrayLike,
        y: ArrayLike | None = None,
    ) -> None:
        curve = self.get_curve(key)
        if y is None:
            curve.item.setData(x)
            return
        self._validate_xy_lengths(x, y)
        curve.item.setData(x, y)

    def plot(
        self,
        key: str,
        x: ArrayLike,
        y: ArrayLike | None = None,
        *,
        label: str | None = None,
        style: CurveStyle,
    ) -> pg.PlotDataItem:
        curve_created = False
        try:
            item = self.add_curve(key, label=label, style=style)
            curve_created = True
            self.set_data(key, x, y)
            return item
        except Exception:
            if curve_created:
                self._discard_curve(key)
            raise

    def curve_data(self, key: str) -> tuple[np.ndarray, np.ndarray]:
        return self.get_curve_data(self.get_curve(key))

    def curve_item(self, key: str) -> pg.PlotDataItem:
        return self.get_curve(key).item

    def clear_curve(self, key: str) -> None:
        self.get_curve(key).item.setData([], [])

    def remove_curve(self, key: str) -> None:
        curve = self.get_curve(key)
        self._plot_item.removeItem(curve.item)
        del self.curves[key]
        self.curve_order.remove(key)

    def set_curve_style(self, key: str, style: CurveStyle) -> bool:
        curve = self.get_curve(key)
        if curve.style == style:
            return False
        curve.style = style
        return True

    def curve_style(self, key: str) -> CurveStyle:
        return self.get_curve(key).style

    def curve_choices(self) -> tuple[tuple[str, str], ...]:
        return tuple((key, self.curves[key].label) for key in self.curve_order)

    def curve_visible(self, key: str) -> bool:
        return self.get_curve(key).visible

    def set_curve_visible(self, key: str, visible: bool) -> bool:
        curve = self.get_curve(key)
        if curve.visible == visible:
            return False
        curve.visible = visible
        curve.item.setVisible(visible)
        return True

    def _discard_curve(self, key: str) -> None:
        curve = self.curves[key]
        self._plot_item.removeItem(curve.item)
        del self.curves[key]
        self.curve_order.remove(key)

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

    def ordered_curves(self) -> tuple[CurveState, ...]:
        return tuple(self.curves[key] for key in self.curve_order)

    @staticmethod
    def _validate_xy_lengths(x_values: ArrayLike, y_values: ArrayLike) -> None:
        try:
            x_length = len(x_values)  # type: ignore[arg-type]
            y_length = len(y_values)  # type: ignore[arg-type]
        except TypeError as exc:
            raise TypeError("x and y must be array-like values.") from exc
        if x_length != y_length:
            raise ValueError(
                f"x and y must have the same length, got {x_length} and {y_length}"
            )
