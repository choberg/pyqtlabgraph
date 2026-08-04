from __future__ import annotations

from .colormaps import (
    BUILTIN_COLOR_GRADIENTS,
    BUILTIN_CURVE_PALETTES,
    PyQtLabGraphColorGradient,
    PyQtLabGraphCurvePalette,
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
        self._themes = {_normalized_name(name): theme for name, theme in BUILTIN_THEMES.items()}
        self._curve_palettes = {
            _normalized_name(name): value for name, value in BUILTIN_CURVE_PALETTES.items()
        }
        self._color_gradients = {
            _normalized_name(name): value for name, value in BUILTIN_COLOR_GRADIENTS.items()
        }

    @property
    def themes(self) -> tuple[PyQtLabGraphTheme, ...]:
        return tuple(self._themes.values())

    @property
    def curve_palettes(self) -> tuple[PyQtLabGraphCurvePalette, ...]:
        return tuple(self._curve_palettes.values())

    @property
    def color_gradients(self) -> tuple[PyQtLabGraphColorGradient, ...]:
        return tuple(self._color_gradients.values())

    def register_theme(self, theme: PyQtLabGraphTheme) -> None:
        key = _normalized_name(theme.name)
        if key in self._themes:
            raise ValueError(f'PyQtLabGraph theme name "{theme.name}" is already registered.')
        self._themes[key] = theme

    def register_curve_palette(self, palette: PyQtLabGraphCurvePalette) -> None:
        if not isinstance(palette, PyQtLabGraphCurvePalette):
            raise TypeError("palette must be a PyQtLabGraphCurvePalette.")
        key = _normalized_name(palette.name)
        if key in self._curve_palettes:
            raise ValueError(
                f'PyQtLabGraph curve palette name "{palette.name}" is already registered.'
            )
        self._curve_palettes[key] = palette

    def register_color_gradient(self, gradient: PyQtLabGraphColorGradient) -> None:
        if not isinstance(gradient, PyQtLabGraphColorGradient):
            raise TypeError("gradient must be a PyQtLabGraphColorGradient.")
        key = _normalized_name(gradient.name)
        if key in self._color_gradients:
            raise ValueError(
                f'PyQtLabGraph color gradient name "{gradient.name}" is already registered.'
            )
        self._color_gradients[key] = gradient

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

    def resolve_curve_palette(
        self, palette: str | PyQtLabGraphCurvePalette
    ) -> PyQtLabGraphCurvePalette:
        if not isinstance(palette, (str, PyQtLabGraphCurvePalette)):
            raise TypeError("palette must be a string or PyQtLabGraphCurvePalette.")
        return self._resolve_named_value(palette, self._curve_palettes, "curve palette", "palettes")

    def resolve_color_gradient(
        self, gradient: str | PyQtLabGraphColorGradient
    ) -> PyQtLabGraphColorGradient:
        return self._resolve_named_value(
            gradient, self._color_gradients, "color gradient", "gradients"
        )

    @staticmethod
    def _resolve_named_value(value, values, kind: str, plural: str):
        key = _normalized_name(value.name if hasattr(value, "name") else value)
        registered = values.get(key)
        if registered is None:
            if hasattr(value, "name"):
                raise ValueError(
                    f'PyQtLabGraph {kind} "{value.name}" is not registered in this registry.'
                )
            available = ", ".join(item.name for item in values.values())
            raise ValueError(
                f'Unknown PyQtLabGraph {kind} "{value}". Available {plural}: {available}.'
            )
        if hasattr(value, "name") and registered != value:
            raise ValueError(
                f'PyQtLabGraph {kind} "{value.name}" does not match the registered value.'
            )
        return registered

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
