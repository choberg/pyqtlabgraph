from __future__ import annotations

from .styles import (
    BUILTIN_PLOT_STYLES,
    LIGHT_PLOT_STYLE,
    PyQtLabGraphPlotStyle,
)
from .themes import BUILTIN_THEMES, LIGHT_THEME, PyQtLabGraphTheme


def _normalized_name(name: str) -> str:
    normalized = name.strip().casefold()
    if not normalized:
        raise ValueError("Style registry names must not be empty.")
    return normalized


class PyQtLabGraphStyleRegistry:
    """Resolves the built-in and host-registered plot appearance values."""

    def __init__(self) -> None:
        self._themes = {
            _normalized_name(name): theme for name, theme in BUILTIN_THEMES.items()
        }
        self._plot_styles = {
            _normalized_name(name): plot_style
            for name, plot_style in BUILTIN_PLOT_STYLES.items()
        }

    @property
    def themes(self) -> tuple[PyQtLabGraphTheme, ...]:
        return tuple(self._themes.values())

    @property
    def plot_styles(self) -> tuple[PyQtLabGraphPlotStyle, ...]:
        return tuple(self._plot_styles.values())

    def register_theme(self, theme: PyQtLabGraphTheme) -> None:
        key = _normalized_name(theme.name)
        if key in self._themes:
            raise ValueError(
                f'PyQtLabGraph theme name "{theme.name}" is already registered.'
            )
        self._themes[key] = theme

    def register_plot_style(self, plot_style: PyQtLabGraphPlotStyle) -> None:
        key = _normalized_name(plot_style.name)
        if key in self._plot_styles:
            raise ValueError(
                f'PyQtLabGraph plot style name "{plot_style.name}" is already registered.'
            )
        self._plot_styles[key] = plot_style

    def resolve_theme(
        self,
        theme: str | PyQtLabGraphTheme | None,
    ) -> PyQtLabGraphTheme:
        if theme is None:
            return self._themes[_normalized_name(LIGHT_THEME.name)]
        if isinstance(theme, PyQtLabGraphTheme):
            return self._resolve_theme_object(theme)
        key = _normalized_name(theme)
        try:
            return self._themes[key]
        except KeyError as exc:
            available = ", ".join(value.name for value in self.themes)
            raise ValueError(
                f'Unknown PyQtLabGraph theme "{theme}". Available themes: {available}.'
            ) from exc

    def resolve_plot_style(
        self,
        plot_style: str | PyQtLabGraphPlotStyle | None,
    ) -> PyQtLabGraphPlotStyle:
        if plot_style is None:
            return self._plot_styles[_normalized_name(LIGHT_PLOT_STYLE.name)]
        if isinstance(plot_style, PyQtLabGraphPlotStyle):
            return self._resolve_plot_style_object(plot_style)
        key = _normalized_name(plot_style)
        try:
            return self._plot_styles[key]
        except KeyError as exc:
            available = ", ".join(value.name for value in self.plot_styles)
            raise ValueError(
                f'Unknown PyQtLabGraph plot style "{plot_style}". '
                f"Available plot styles: {available}."
            ) from exc

    def _resolve_theme_object(self, theme: PyQtLabGraphTheme) -> PyQtLabGraphTheme:
        registered = self._themes.get(_normalized_name(theme.name))
        if registered is None:
            raise ValueError(
                f'PyQtLabGraph theme "{theme.name}" is not registered in this registry.'
            )
        if registered != theme:
            raise ValueError(
                f'PyQtLabGraph theme "{theme.name}" does not match the registered value.'
            )
        return registered

    def _resolve_plot_style_object(
        self,
        plot_style: PyQtLabGraphPlotStyle,
    ) -> PyQtLabGraphPlotStyle:
        registered = self._plot_styles.get(_normalized_name(plot_style.name))
        if registered is None:
            raise ValueError(
                f'PyQtLabGraph plot style "{plot_style.name}" is not registered '
                "in this registry."
            )
        if registered != plot_style:
            raise ValueError(
                f'PyQtLabGraph plot style "{plot_style.name}" does not match '
                "the registered value."
            )
        return registered
