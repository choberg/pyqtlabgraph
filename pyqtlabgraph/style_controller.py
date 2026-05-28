from __future__ import annotations

from typing import TYPE_CHECKING
import pyqtgraph as pg
from PySide6.QtGui import QColor, QPalette
from PySide6.QtCore import QEvent, QObject

from .qt_styles import plot_widget_chrome_style
from .themes import PyQtLabGraphTheme, resolve_theme
from .styles import CurveStyle, PyQtLabGraphPlotStyle, resolve_plot_style

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget
    from .models import CurveState

from .constants import (
    _GRID_LINE_WIDTH,
    _AXIS_PEN_WIDTH,
    _AXIS_LABEL_TOP_MARGIN,
    _AXIS_LABEL_RIGHT_MARGIN,
)


class StyleController(QObject):
    """Centralizes theme application, plot styles, and Qt palette event filtering."""

    def __init__(self, widget: PyQtLabGraphWidget) -> None:
        super().__init__(widget.plot_widget)
        self._widget = widget
        self.theme: PyQtLabGraphTheme = resolve_theme(None)
        self.plot_style: PyQtLabGraphPlotStyle = resolve_plot_style(None)
        self._widget.plot_widget.installEventFilter(self)

    def set_theme(self, theme: str | PyQtLabGraphTheme | None) -> None:
        self.theme = resolve_theme(theme)
        self._widget.plot_widget.setBackground(QColor(0, 0, 0, 0))
        self._widget.plot_widget.setStyleSheet(plot_widget_chrome_style())
        self._widget.view_box.setBackgroundColor(self.theme.plot_background)
        self._widget._extend_view_box_background()
        self._widget._style_rect_zoom_selection()
        self._widget.grid_item.setPen(pg.mkPen(self.theme.grid, width=_GRID_LINE_WIDTH))
        for curve_key in self._widget.curve_manager.curve_order:
            curve = self._widget.curve_manager.curves[curve_key]
            self.apply_curve_style(curve)
        self._widget._style_legend()
        self._widget._set_axis_labels(
            self._widget.x_label_text,
            self._widget.y_label_text,
            self._widget.x_label_units,
            self._widget.y_label_units,
        )
        self.apply_host_axis_style()
        if self._widget.toolbar is not None:
            self._widget.toolbar.refresh_icons()

    def set_plot_style(
        self,
        plot_style: str | PyQtLabGraphPlotStyle | None,
        *,
        apply_to_existing: bool = False,
    ) -> None:
        self.plot_style = resolve_plot_style(plot_style)
        if apply_to_existing:
            self.apply_plot_style()

    def apply_plot_style(self, plot_style: str | PyQtLabGraphPlotStyle | None = None) -> None:
        if plot_style is not None:
            self.plot_style = resolve_plot_style(plot_style)

        for index, curve_key in enumerate(self._widget.curve_manager.curve_order):
            curve = self._widget.curve_manager.curves[curve_key]
            curve.style = self.plot_style_curve_style(index)
            self.apply_curve_style(curve)
        self._widget._refresh_legend()

    def default_curve_style(self, index: int, color: str | None = None) -> CurveStyle:
        curve_style = self.plot_style_curve_style(index)
        if color is not None:
            curve_style = curve_style.with_overrides(line_color=color)
        return curve_style

    def plot_style_curve_style(self, index: int) -> CurveStyle:
        return self.plot_style.curve_style(index)

    def apply_curve_style(self, curve: CurveState) -> None:
        style = curve.style
        color = style.line_color
        line_width = style.line_width
        marker_size = style.marker_size
        marker_outline_width = style.marker_outline_width
        marker_symbol = style.marker_symbol
        line_enabled = style.line_enabled or (
            self._widget.render_optimizer.active and style.marker_enabled
        )
        marker_enabled = style.marker_enabled and not self._widget.render_optimizer.active
        marker_filled = style.marker_filled
        marker_pen_width = 0.0 if marker_filled else marker_outline_width

        curve.item.setPen(pg.mkPen(color, width=line_width) if line_enabled else None)
        curve.item.setSymbol(marker_symbol if marker_enabled else None)
        curve.item.setSymbolSize(marker_size if marker_enabled else 0)
        curve.item.setSymbolBrush(
            pg.mkBrush(color) if marker_enabled and marker_filled else pg.mkBrush(None)
        )
        curve.item.setSymbolPen(
            pg.mkPen(color, width=marker_pen_width) if marker_enabled else None
        )
        curve.item.scatter.setPen(
            pg.mkPen(color, width=marker_pen_width) if marker_enabled else None
        )
        curve.item.scatter.setBrush(
            pg.mkBrush(color) if marker_enabled and marker_filled else pg.mkBrush(None)
        )
        self._widget._update_legend_curve(curve.key)

    def apply_host_axis_style(self) -> None:
        axis_color = self.host_axis_color()
        axis_pen = pg.mkPen(axis_color, width=_AXIS_PEN_WIDTH)
        text_pen = pg.mkPen(axis_color)
        for axis_name in ("bottom", "left", "top", "right"):
            axis = self._widget.plot_item.getAxis(axis_name)
            axis.setPen(axis_pen)
            axis.setTextPen(text_pen)
            axis.setTickPen(axis_pen)
        self._widget._set_axis_labels(
            self._widget.x_label_text,
            self._widget.y_label_text,
            self._widget.x_label_units,
            self._widget.y_label_units,
        )

    def host_axis_color(self) -> QColor:
        return self._widget.plot_widget.palette().color(QPalette.ColorRole.WindowText)

    def host_axis_color_name(self) -> str:
        return self.host_axis_color().name(QColor.NameFormat.HexRgb)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        try:
            plot_widget = self._widget.plot_widget
        except AttributeError:
            return super().eventFilter(watched, event)

        watched_widgets = {plot_widget}
        if getattr(self._widget, "plot_frame", None) is not None:
            watched_widgets.add(self._widget.plot_frame)
        if watched in watched_widgets and event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self.apply_host_axis_style()
        return super().eventFilter(watched, event)
