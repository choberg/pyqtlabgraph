from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pyqtgraph as pg
from PySide6.QtGui import QColor

from .styles import CurveStyle


@dataclass(frozen=True)
class TracePersistenceConfig:
    history_length: int = 16
    oldest_opacity: float = 0.04
    newest_opacity: float = 0.65
    decay: float = 3.0

    def __post_init__(self) -> None:
        if isinstance(self.history_length, bool) or not isinstance(self.history_length, int):
            raise TypeError("Persistence history_length must be an integer.")
        if not 1 <= self.history_length <= 128:
            raise ValueError("Persistence history_length must be between 1 and 128.")
        for name, value in (
            ("oldest_opacity", self.oldest_opacity),
            ("newest_opacity", self.newest_opacity),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"Persistence {name} must be a finite real number.")
            if not math.isfinite(value) or not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"Persistence {name} must be finite and between 0.0 and 1.0.")
        if self.oldest_opacity > self.newest_opacity:
            raise ValueError("Persistence oldest_opacity must not exceed newest_opacity.")
        if isinstance(self.decay, bool) or not isinstance(self.decay, (int, float)):
            raise TypeError("Persistence decay must be a finite real number.")
        if not math.isfinite(self.decay) or self.decay <= 0.0:
            raise ValueError("Persistence decay must be finite and greater than zero.")


class TracePersistenceManager:
    """Owns bounded, reusable historical PlotDataItems for source curves."""

    def __init__(self, plot_item: pg.PlotItem) -> None:
        self._plot_item = plot_item
        self._configs: dict[str, TracePersistenceConfig] = {}
        self._items: dict[str, list[pg.PlotDataItem]] = {}

    def config(self, key: str) -> TracePersistenceConfig | None:
        return self._configs.get(key)

    def set_config(self, key: str, config: TracePersistenceConfig | None) -> None:
        if config is not None and not isinstance(config, TracePersistenceConfig):
            raise TypeError("config must be a TracePersistenceConfig or None.")
        if config is None:
            self.remove(key)
            return
        self._configs[key] = config
        items = self._items.setdefault(key, [])
        for item in items[config.history_length :]:
            self._plot_item.removeItem(item)
        del items[config.history_length :]

    def capture(
        self,
        key: str,
        x: np.ndarray,
        y: np.ndarray,
        style: CurveStyle,
        visible: bool,
    ) -> None:
        config = self._configs.get(key)
        if config is None or len(x) == 0 or len(y) == 0:
            return
        items = self._items.setdefault(key, [])
        if len(items) < config.history_length:
            item = pg.PlotDataItem([], [])
            item.setZValue(-1)
            self._plot_item.addItem(item, ignoreBounds=True)
        else:
            item = items.pop()
        item.setData(np.array(x, copy=True), np.array(y, copy=True))
        items.insert(0, item)
        self.update_curve(key, style, visible)

    def clear(self, key: str) -> None:
        for item in self._items.get(key, ()):
            item.setData([], [])

    def remove(self, key: str) -> None:
        for item in self._items.pop(key, ()):
            self._plot_item.removeItem(item)
        self._configs.pop(key, None)

    def clear_all(self) -> None:
        for key in tuple(self._items):
            self.clear(key)

    def update_curve(self, key: str, style: CurveStyle, visible: bool) -> None:
        items = self._items.get(key, [])
        config = self._configs.get(key)
        if config is None:
            return
        for index, item in enumerate(items):
            color = QColor(style.line_color)
            color.setAlphaF(self._opacity(index, len(items), config))
            item.setPen(pg.mkPen(color, width=style.line_width) if style.line_enabled else None)
            item.setSymbol(None)
            item.setVisible(visible)

    def apply_rendering(self, *, clip_to_view: bool, downsampling: bool, antialias: bool) -> None:
        for items in self._items.values():
            for item in items:
                item.setClipToView(clip_to_view)
                item.setDownsampling(auto=downsampling, method="peak")
                item.opts["antialias"] = antialias
                item.updateItems(styleUpdate=True)

    def items(self, key: str) -> tuple[pg.PlotDataItem, ...]:
        return tuple(self._items.get(key, ()))

    @staticmethod
    def _opacity(index: int, count: int, config: TracePersistenceConfig) -> float:
        if count <= 1:
            return config.newest_opacity
        age = index / (count - 1)
        numerator = math.exp(config.decay * (1.0 - age)) - 1.0
        weight = numerator / (math.exp(config.decay) - 1.0)
        return config.oldest_opacity + (config.newest_opacity - config.oldest_opacity) * weight
