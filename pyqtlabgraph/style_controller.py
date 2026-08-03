from __future__ import annotations

from collections.abc import Callable, Sequence

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

from .constants import _AXIS_PEN_WIDTH, _GRID_LINE_WIDTH
from .interaction import _ZOOM_SELECTION_BORDER_WIDTH
from .models import CurveState
from .style_registry import PyQtLabGraphStyleRegistry
from .styles import CurveStyle, PyQtLabGraphPlotStyle
from .themes import (
    ZOOM_SELECTION_BORDER_ALPHA,
    ZOOM_SELECTION_COLOR,
    ZOOM_SELECTION_FILL_ALPHA,
    PyQtLabGraphTheme,
)

_VIEW_BOX_BACKGROUND_OVERDRAW = 1.0


class StyleController(QObject):
    """Applies plot-owned appearance from explicit plot primitives."""

    def __init__(
        self,
        *,
        plot_widget: pg.PlotWidget,
        plot_item: pg.PlotItem,
        view_box: pg.ViewBox,
        grid_item: pg.GridItem,
        registry: PyQtLabGraphStyleRegistry,
        curves_provider: Callable[[], Sequence[CurveState]],
        adaptive_mode_provider: Callable[[], bool],
    ) -> None:
        super().__init__(plot_widget)
        self._plot_widget = plot_widget
        self._plot_item = plot_item
        self._view_box = view_box
        self._grid_item = grid_item
        self._registry = registry
        self._curves_provider = curves_provider
        self._adaptive_mode_provider = adaptive_mode_provider
        self._palette_widgets: set[QWidget] = {plot_widget}
        self.theme = registry.resolve_theme(None)
        self.plot_style = registry.resolve_plot_style(None)
        plot_widget.installEventFilter(self)

    def watch_palette_widget(self, widget: QWidget) -> None:
        self._palette_widgets.add(widget)
        widget.installEventFilter(self)

    def set_theme(self, theme: str | PyQtLabGraphTheme | None) -> None:
        resolved_theme = self._registry.resolve_theme(theme)
        self.theme = resolved_theme
        self._plot_widget.setBackground(QColor(0, 0, 0, 0))
        self._view_box.setBackgroundColor(resolved_theme.plot_background)
        self.extend_view_box_background()
        self.style_rect_zoom_selection()
        self._grid_item.setPen(pg.mkPen(resolved_theme.grid, width=_GRID_LINE_WIDTH))
        for curve in self._curves_provider():
            self.apply_curve_style(curve)
        self.apply_host_axis_style()

    def set_plot_style(
        self,
        plot_style: str | PyQtLabGraphPlotStyle | None,
    ) -> tuple[bool, tuple[str, ...]]:
        resolved = self._registry.resolve_plot_style(plot_style)
        plot_style_changed = resolved != self.plot_style
        self.plot_style = resolved

        changed_keys: list[str] = []
        for index, curve in enumerate(self._curves_provider()):
            style = self.plot_style_curve_style(index)
            if curve.style == style:
                continue
            curve.style = style
            self.apply_curve_style(curve)
            changed_keys.append(curve.key)
        return plot_style_changed, tuple(changed_keys)

    def default_curve_style(self, index: int) -> CurveStyle:
        return self.plot_style_curve_style(index)

    def plot_style_curve_style(self, index: int) -> CurveStyle:
        return self.plot_style.curve_style(index)

    def apply_curve_style(self, curve: CurveState) -> None:
        style = curve.style
        color = style.line_color
        marker_enabled = style.marker_enabled and not self._adaptive_mode_provider()
        line_enabled = style.line_enabled or (
            self._adaptive_mode_provider() and style.marker_enabled
        )
        marker_pen_width = 0.0 if style.marker_filled else style.marker_outline_width

        curve.item.setPen(
            pg.mkPen(color, width=style.line_width) if line_enabled else None
        )
        curve.item.setSymbol(style.marker_symbol if marker_enabled else None)
        curve.item.setSymbolSize(style.marker_size if marker_enabled else 0)
        curve.item.setSymbolBrush(
            pg.mkBrush(color)
            if marker_enabled and style.marker_filled
            else pg.mkBrush(None)
        )
        curve.item.setSymbolPen(
            pg.mkPen(color, width=marker_pen_width) if marker_enabled else None
        )
        curve.item.scatter.setPen(
            pg.mkPen(color, width=marker_pen_width) if marker_enabled else None
        )
        curve.item.scatter.setBrush(
            pg.mkBrush(color)
            if marker_enabled and style.marker_filled
            else pg.mkBrush(None)
        )

    def apply_host_axis_style(self) -> None:
        axis_color = self.host_axis_color()
        axis_pen = pg.mkPen(axis_color, width=_AXIS_PEN_WIDTH)
        text_pen = pg.mkPen(axis_color)
        for axis_name in ("bottom", "left", "top", "right"):
            axis = self._plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setTickPen(axis_pen)

    def host_axis_color(self) -> QColor:
        return self._plot_widget.palette().color(QPalette.ColorRole.WindowText)

    def host_axis_color_name(self) -> str:
        return self.host_axis_color().name(QColor.NameFormat.HexRgb)

    def style_rect_zoom_selection(self) -> None:
        selection_color = pg.mkColor(ZOOM_SELECTION_COLOR)
        selection_color.setAlpha(ZOOM_SELECTION_FILL_ALPHA)
        border_color = pg.mkColor(ZOOM_SELECTION_COLOR)
        border_color.setAlpha(ZOOM_SELECTION_BORDER_ALPHA)
        self._view_box.rbScaleBox.setPen(
            pg.mkPen(border_color, width=_ZOOM_SELECTION_BORDER_WIDTH)
        )
        self._view_box.rbScaleBox.setBrush(pg.mkBrush(selection_color))

    def extend_view_box_background(self) -> None:
        self._view_box.background.setRect(
            self._view_box.rect().adjusted(
                0.0,
                0.0,
                _VIEW_BOX_BACKGROUND_OVERDRAW,
                _VIEW_BOX_BACKGROUND_OVERDRAW,
            )
        )

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        palette_widgets = getattr(self, "_palette_widgets", ())
        if watched in palette_widgets and event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self.apply_host_axis_style()
        return super().eventFilter(watched, event)
