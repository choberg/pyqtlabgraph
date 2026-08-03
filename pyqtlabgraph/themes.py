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

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("PyQtLabGraph theme name must not be empty.")
        if not QColor(self.plot_background).isValid():
            raise ValueError(f"Invalid plot_background color: {self.plot_background}")
        if not self.grid.isValid():
            raise ValueError("Invalid grid color")
        if not QColor(self.border).isValid():
            raise ValueError(f"Invalid border color: {self.border}")


LIGHT_THEME = PyQtLabGraphTheme(
    name="light",
    plot_background="#ffffff",
    grid=QColor(107, 114, 128, 65),
    border="#c8ced6",
)

DARK_THEME = PyQtLabGraphTheme(
    name="dark",
    plot_background="#202a33",
    grid=QColor(214, 226, 237, 42),
    border="#526270",
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
