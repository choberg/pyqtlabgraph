from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Mapping

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class CurveStyle:
    line_enabled: bool = True
    line_color: str = "#0072B2"
    line_width: float = 1.0
    marker_symbol: str = "s"
    marker_size: int = 5
    marker_outline_width: float = 1.0
    marker_enabled: bool = True
    marker_filled: bool = False

    def __post_init__(self) -> None:
        if not QColor(self.line_color).isValid():
            raise ValueError(f"Invalid line_color color: {self.line_color}")
        if self.line_width <= 0.0:
            raise ValueError("Curve line_width must be greater than zero.")
        if self.marker_size <= 0:
            raise ValueError("Curve marker_size must be greater than zero.")
        if self.marker_outline_width < 0.0:
            raise ValueError("Curve marker_outline_width must not be negative.")

    def with_overrides(self, **overrides: object) -> "CurveStyle":
        return replace(self, **overrides)  # type: ignore[arg-type]


@dataclass(frozen=True)
class PyQtLabGraphPlotStyle:
    name: str
    curve_styles: tuple[CurveStyle, ...]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("PyQtLabGraph plot style name must not be empty.")
        if not self.curve_styles:
            raise ValueError(
                "PyQtLabGraph plot style must contain at least one curve style."
            )

    def curve_style(self, index: int) -> CurveStyle:
        return self.curve_styles[index % len(self.curve_styles)]


def _curve_style(color: str) -> CurveStyle:
    return CurveStyle(line_color=color)


LIGHT_PLOT_STYLE = PyQtLabGraphPlotStyle(
    name="light",
    curve_styles=tuple(
        _curve_style(color)
        for color in (
            "#0072B2",
            "#D55E00",
            "#009E73",
            "#CC79A7",
            "#E69F00",
            "#56B4E9",
        )
    ),
)

DARK_PLOT_STYLE = PyQtLabGraphPlotStyle(
    name="dark",
    curve_styles=tuple(
        _curve_style(color)
        for color in (
            "#56B4E9",
            "#FFB000",
            "#00C2A8",
            "#FF6B6B",
            "#C77DFF",
            "#9AE66E",
        )
    ),
)

SOLARIZED_PLOT_STYLE = PyQtLabGraphPlotStyle(
    name="solarized",
    curve_styles=tuple(
        _curve_style(color)
        for color in (
            "#268BD2",
            "#CB4B16",
            "#859900",
            "#DC322F",
            "#6C71C4",
            "#2AA198",
        )
    ),
)

BUILTIN_PLOT_STYLES: Mapping[str, PyQtLabGraphPlotStyle] = {
    LIGHT_PLOT_STYLE.name: LIGHT_PLOT_STYLE,
    DARK_PLOT_STYLE.name: DARK_PLOT_STYLE,
    SOLARIZED_PLOT_STYLE.name: SOLARIZED_PLOT_STYLE,
}
