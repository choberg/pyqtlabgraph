from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from PySide6.QtGui import QColor


ZOOM_SELECTION_COLOR = "#1f77b4"
ZOOM_SELECTION_FILL_ALPHA = 85
ZOOM_SELECTION_BORDER_ALPHA = 180


@dataclass(frozen=True)
class PyQtLabGraphTheme:
    name: str
    plot_background: str
    grid: QColor
    border: str


LIGHT_THEME = PyQtLabGraphTheme(
    name="light",
    plot_background="#ffffff",
    grid=QColor(107, 114, 128, 65),
    border="#c8ced6",
)

DARK_THEME = PyQtLabGraphTheme(
    name="dark",
    plot_background="#181c20",
    grid=QColor(216, 222, 233, 38),
    border="#3a4048",
)

LIGHT_SOLARIZED_THEME = PyQtLabGraphTheme(
    name="light-solarized",
    plot_background="#fdf6e3",
    grid=QColor(101, 123, 131, 60),
    border="#d6cda9",
)

DARK_SOLARIZED_THEME = PyQtLabGraphTheme(
    name="dark-solarized",
    plot_background="#002b36",
    grid=QColor(131, 148, 150, 52),
    border="#073642",
)

BUILTIN_THEMES: Mapping[str, PyQtLabGraphTheme] = {
    LIGHT_THEME.name: LIGHT_THEME,
    DARK_THEME.name: DARK_THEME,
    LIGHT_SOLARIZED_THEME.name: LIGHT_SOLARIZED_THEME,
    DARK_SOLARIZED_THEME.name: DARK_SOLARIZED_THEME,
}


def resolve_theme(theme: str | PyQtLabGraphTheme | None) -> PyQtLabGraphTheme:
    if theme is None:
        return LIGHT_THEME
    if isinstance(theme, PyQtLabGraphTheme):
        return theme

    key = theme.lower()
    try:
        return BUILTIN_THEMES[key]
    except KeyError as exc:
        available = ", ".join(sorted(BUILTIN_THEMES))
        raise ValueError(f'Unknown PyQtLabGraph theme "{theme}". Available themes: {available}.') from exc
