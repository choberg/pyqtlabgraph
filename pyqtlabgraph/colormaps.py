from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping

from PySide6.QtGui import QColor


def _validated_colors(colors: tuple[str | QColor, ...], owner: str) -> tuple[QColor, ...]:
    if not colors:
        raise ValueError(f"{owner} must contain at least one color.")
    normalized: list[QColor] = []
    for value in colors:
        if not isinstance(value, (str, QColor)) or not QColor(value).isValid():
            raise ValueError(f"Invalid color in {owner}: {value!r}")
        normalized.append(QColor(value))
    return tuple(normalized)


@dataclass(frozen=True)
class PyQtLabGraphCurvePalette:
    """An immutable categorical sequence used to color independent curves."""

    name: str
    colors: tuple[str | QColor, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PyQtLabGraph curve palette name must not be empty.")
        object.__setattr__(self, "colors", _validated_colors(self.colors, "curve palette"))

    def color(self, index: int) -> QColor:
        if not isinstance(index, int) or isinstance(index, bool):
            raise TypeError("Palette index must be an integer.")
        return QColor(self.colors[index % len(self.colors)])


@dataclass(frozen=True)
class PyQtLabGraphColorGradient:
    """An immutable piecewise-linear continuous color gradient."""

    name: str
    positions: tuple[float, ...]
    colors: tuple[str | QColor, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PyQtLabGraph color gradient name must not be empty.")
        colors = _validated_colors(self.colors, "color gradient")
        if len(self.positions) != len(colors):
            raise ValueError("Gradient positions and colors must have the same length.")
        if len(colors) < 2:
            raise ValueError("A color gradient must contain at least two colors.")
        previous = -math.inf
        for position in self.positions:
            if isinstance(position, bool) or not isinstance(position, (int, float)):
                raise TypeError("Gradient positions must be real numbers.")
            value = float(position)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("Gradient positions must be finite and between 0.0 and 1.0.")
            if value <= previous:
                raise ValueError("Gradient positions must be strictly increasing.")
            previous = value
        object.__setattr__(self, "positions", tuple(float(p) for p in self.positions))
        object.__setattr__(self, "colors", colors)

    def color_at(self, position: float, *, reverse: bool = False) -> QColor:
        if isinstance(position, bool) or not isinstance(position, (int, float)):
            raise TypeError("Gradient position must be a real number.")
        value = float(position)
        if not math.isfinite(value):
            raise ValueError("Gradient position must be finite.")
        value = min(1.0, max(0.0, value))
        if reverse:
            value = 1.0 - value
        if value <= self.positions[0]:
            return QColor(self.colors[0])
        if value >= self.positions[-1]:
            return QColor(self.colors[-1])
        for index in range(1, len(self.positions)):
            upper = self.positions[index]
            if value <= upper:
                lower = self.positions[index - 1]
                fraction = (value - lower) / (upper - lower)
                first = QColor(self.colors[index - 1])
                second = QColor(self.colors[index])
                return QColor.fromRgbF(
                    first.redF() + (second.redF() - first.redF()) * fraction,
                    first.greenF() + (second.greenF() - first.greenF()) * fraction,
                    first.blueF() + (second.blueF() - first.blueF()) * fraction,
                )
        raise AssertionError("unreachable")

    def sample(self, count: int, *, reverse: bool = False) -> tuple[QColor, ...]:
        if not isinstance(count, int) or isinstance(count, bool):
            raise TypeError("Gradient sample count must be an integer.")
        if count <= 0:
            raise ValueError("Gradient sample count must be greater than zero.")
        if count == 1:
            return (self.color_at(0.5, reverse=reverse),)
        return tuple(self.color_at(i / (count - 1), reverse=reverse) for i in range(count))


def _palette(name: str, *colors: str) -> PyQtLabGraphCurvePalette:
    return PyQtLabGraphCurvePalette(name, colors)


BUILTIN_CURVE_PALETTES: Mapping[str, PyQtLabGraphCurvePalette] = {
    value.name: value
    for value in (
        _palette("default-light", "#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9"),
        _palette("default-dark", "#56B4E9", "#FFB000", "#00C2A8", "#FF6B6B", "#C77DFF", "#9AE66E"),
        _palette("solarized", "#268BD2", "#CB4B16", "#859900", "#DC322F", "#6C71C4", "#2AA198"),
        _palette(
            "okabe-ito",
            "#E69F00",
            "#56B4E9",
            "#009E73",
            "#F0E442",
            "#0072B2",
            "#D55E00",
            "#CC79A7",
            "#000000",
        ),
        _palette(
            "matplotlib-tab10",
            "#1F77B4",
            "#FF7F0E",
            "#2CA02C",
            "#D62728",
            "#9467BD",
            "#8C564B",
            "#E377C2",
            "#7F7F7F",
            "#BCBD22",
            "#17BECF",
        ),
        _palette(
            "petroff10",
            "#3F90DA",
            "#FFA90E",
            "#BD1F01",
            "#94A4A2",
            "#832DB6",
            "#A96B59",
            "#E76300",
            "#B9AC70",
            "#717581",
            "#92DADD",
        ),
        _palette(
            "seaborn-colorblind",
            "#0173B2",
            "#DE8F05",
            "#029E73",
            "#D55E00",
            "#CC78BC",
            "#CA9161",
            "#FBAFE4",
            "#949494",
            "#ECE133",
            "#56B4E9",
        ),
        _palette(
            "tol-bright",
            "#4477AA",
            "#EE6677",
            "#228833",
            "#CCBB44",
            "#66CCEE",
            "#AA3377",
            "#BBBBBB",
        ),
        _palette(
            "tol-muted",
            "#332288",
            "#88CCEE",
            "#44AA99",
            "#117733",
            "#999933",
            "#DDCC77",
            "#CC6677",
            "#882255",
            "#AA4499",
            "#DDDDDD",
        ),
        _palette(
            "plotly-safe",
            "#88CCEE",
            "#CC6677",
            "#DDCC77",
            "#117733",
            "#332288",
            "#AA4499",
            "#44AA99",
            "#999933",
            "#882255",
            "#661100",
            "#6699CC",
            "#888888",
        ),
    )
}


def _gradient(name: str, *colors: str) -> PyQtLabGraphColorGradient:
    return PyQtLabGraphColorGradient(
        name, tuple(i / (len(colors) - 1) for i in range(len(colors))), colors
    )


# Compact control-point samples from the named Matplotlib color maps.
BUILTIN_COLOR_GRADIENTS: Mapping[str, PyQtLabGraphColorGradient] = {
    value.name: value
    for value in (
        _gradient("viridis", "#440154", "#3B528B", "#21918C", "#5EC962", "#FDE725"),
        _gradient("cividis", "#00224E", "#434E6C", "#7D7C78", "#BCAF6F", "#FEE838"),
        _gradient("plasma", "#0D0887", "#7E03A8", "#CC4778", "#F89540", "#F0F921"),
        _gradient("inferno", "#000004", "#57106E", "#BC3754", "#F98E09", "#FCFFA4"),
        _gradient("magma", "#000004", "#51127C", "#B73779", "#FC8961", "#FCFDBF"),
        _gradient(
            "turbo",
            "#30123B",
            "#466BE3",
            "#28BBEC",
            "#32F298",
            "#A4FC3C",
            "#F9BA38",
            "#E95B0C",
            "#7A0403",
        ),
        _gradient("coolwarm", "#3B4CC0", "#8DB0FE", "#DDDDDD", "#F4987A", "#B40426"),
        _gradient("rdbu", "#67001F", "#D6604D", "#F7F7F7", "#4393C3", "#053061"),
        _gradient("brbg", "#543005", "#BF812D", "#F5F5F5", "#35978F", "#003C30"),
        _gradient("twilight", "#E2D9E2", "#6276BA", "#18204C", "#6F123F", "#C75D5D", "#E2D9E2"),
    )
}
