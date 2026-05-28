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

    def with_overrides(self, **overrides: object) -> "CurveStyle":
        return replace(self, **overrides)


@dataclass(frozen=True)
class PyQtLabGraphPlotStyle:
    name: str
    curve_styles: tuple[CurveStyle, ...]

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


def resolve_plot_style(
    plot_style: str | PyQtLabGraphPlotStyle | None,
) -> PyQtLabGraphPlotStyle:
    if plot_style is None:
        return LIGHT_PLOT_STYLE
    if isinstance(plot_style, PyQtLabGraphPlotStyle):
        return plot_style

    key = plot_style.lower()
    try:
        return BUILTIN_PLOT_STYLES[key]
    except KeyError as exc:
        available = ", ".join(sorted(BUILTIN_PLOT_STYLES))
        raise ValueError(
            f'Unknown PyQtLabGraph plot style "{plot_style}". '
            f"Available plot styles: {available}."
        ) from exc


def default_curve_style(color: str) -> CurveStyle:
    return LIGHT_PLOT_STYLE.curve_style(0).with_overrides(line_color=color)
