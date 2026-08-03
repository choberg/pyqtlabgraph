from __future__ import annotations

import math
from collections.abc import Callable

import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPen

from .models import CursorPairState, CursorState, CursorStyle, CursorType

_CURSOR_Z_VALUE = 20
_CURSOR_LABEL_Z_VALUE = _CURSOR_Z_VALUE + 1
_CURSOR_PAIR_Z_VALUE = _CURSOR_LABEL_Z_VALUE + 1
_CURSOR_PAIR_LABEL_Z_VALUE = _CURSOR_PAIR_Z_VALUE + 1
_LABEL_BACKGROUND_ALPHA = 235
_PAIR_REGION_ALPHA = 14
_PAIR_DRAG_HIT_WIDTH = 10

_LINE_STYLES = {
    "solid": Qt.PenStyle.SolidLine,
    "dash": Qt.PenStyle.DashLine,
    "dot": Qt.PenStyle.DotLine,
    "dash-dot": Qt.PenStyle.DashDotLine,
}


class _CursorInfiniteLine(pg.InfiniteLine):
    def __init__(self, *args: object, movement_cursor: Qt.CursorShape, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.movement_cursor = movement_cursor

    def hoverEvent(self, event: object) -> None:
        super().hoverEvent(event)
        if self.mouseHovering:
            self.setCursor(self.movement_cursor)
        else:
            self.unsetCursor()

    def mouseDragEvent(self, event: object) -> None:
        self.setCursor(self.movement_cursor)
        super().mouseDragEvent(event)


class _DraggablePairLine(pg.PlotCurveItem):
    def __init__(self, moved: Callable[[QPointF], None]) -> None:
        super().__init__([], [], antialias=True)
        self._moved = moved
        self.mouseHovering = False
        self._normal_pen = pg.mkPen("#666666", width=1.2, style=Qt.PenStyle.DashLine)
        self._hover_pen = pg.mkPen("#666666", width=2.2, style=Qt.PenStyle.DashLine)
        self.setPen(self._normal_pen)
        self.setClickable(True, width=_PAIR_DRAG_HIT_WIDTH)
        self.setAcceptHoverEvents(True)

    def set_overlay_color(self, color: QColor) -> None:
        self._normal_pen = pg.mkPen(color, width=1.2, style=Qt.PenStyle.DashLine)
        self._hover_pen = pg.mkPen(color, width=2.2, style=Qt.PenStyle.DashLine)
        self.setPen(self._hover_pen if self.mouseHovering else self._normal_pen)

    def hoverEvent(self, event: object) -> None:
        hovering = not event.isExit()  # type: ignore[attr-defined]
        self.mouseHovering = hovering
        self.setPen(self._hover_pen if hovering else self._normal_pen)
        if hovering:
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.acceptDrags(Qt.MouseButton.LeftButton)  # type: ignore[attr-defined]
        else:
            self.unsetCursor()

    def mouseDragEvent(self, event: object) -> None:
        if event.button() != Qt.MouseButton.LeftButton:  # type: ignore[attr-defined]
            event.ignore()  # type: ignore[attr-defined]
            return
        event.accept()  # type: ignore[attr-defined]
        if event.isFinish():  # type: ignore[attr-defined]
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._moved(event.scenePos())  # type: ignore[attr-defined]


class CursorPlotItem:
    """Thin adapter between cursor state and pyqtgraph cursor graphics."""

    def __init__(self, state: CursorState) -> None:
        self.cursor_key = state.key
        self.item = _CursorInfiniteLine(
            pos=0.0,
            angle=self._angle(state.cursor_type),
            pen=self._pen(state.style),
            hoverPen=self._hover_pen(state.style),
            movable=True,
            movement_cursor=(
                Qt.CursorShape.SizeHorCursor
                if state.cursor_type is CursorType.X
                else Qt.CursorShape.SizeVerCursor
            ),
        )
        self.item.setZValue(_CURSOR_Z_VALUE)
        self.label = pg.TextItem(
            text=state.name,
            color=state.style.line_color,
            anchor=(0.0, 0.0),
        )
        self.label.setZValue(_CURSOR_LABEL_Z_VALUE)
        self.label.setVisible(False)

    def update_from_state(
        self,
        state: CursorState,
        *,
        text: str,
        effective_visible: bool,
        selected: bool = False,
        x_log: bool,
        y_log: bool,
        plot_background: str,
    ) -> None:
        display_value = self._display_value(state, x_log=x_log, y_log=y_log)
        visible = effective_visible and display_value is not None
        label_visible = visible and state.label_visible

        self.item.blockSignals(True)
        try:
            self.item.setPen(self._hover_pen(state.style) if selected else self._pen(state.style))
            self.item.setHoverPen(self._hover_pen(state.style))
            if display_value is not None:
                self.item.setValue(display_value)
            self.item.setVisible(visible)
            if not visible:
                self.item.unsetCursor()
        finally:
            self.item.blockSignals(False)

        self.label.setText(f"{state.name}: {text}")
        background = QColor(plot_background)
        background.setAlpha(_LABEL_BACKGROUND_ALPHA)
        self.label.fill = pg.mkBrush(background)
        self.label.border = pg.mkPen(state.style.line_color, width=1.0)
        self.label.setColor(_contrast_color(QColor(plot_background)))
        self.label.update()
        self.label.setVisible(label_visible)

    def raw_value_from_item(
        self,
        state: CursorState,
        *,
        x_log: bool,
        y_log: bool,
    ) -> float | None:
        display_value = float(self.item.value())
        if not math.isfinite(display_value):
            return None

        log_axis = x_log if state.cursor_type is CursorType.X else y_log
        if not log_axis:
            return display_value

        raw_value = 10**display_value
        if not math.isfinite(raw_value) or raw_value <= 0.0:
            return None
        return raw_value

    def display_value(
        self,
        state: CursorState,
        *,
        x_log: bool,
        y_log: bool,
    ) -> float | None:
        return self._display_value(state, x_log=x_log, y_log=y_log)

    @staticmethod
    def _angle(cursor_type: CursorType) -> int:
        return 90 if cursor_type is CursorType.X else 0

    @staticmethod
    def _display_value(
        state: CursorState,
        *,
        x_log: bool,
        y_log: bool,
    ) -> float | None:
        log_axis = x_log if state.cursor_type is CursorType.X else y_log
        if not log_axis:
            return state.value
        if state.value <= 0.0:
            return None
        return math.log10(state.value)

    @staticmethod
    def _pen(style: CursorStyle) -> QPen:
        return pg.mkPen(
            style.line_color,
            width=style.line_width,
            style=_LINE_STYLES[style.line_style.value],
        )

    @staticmethod
    def _hover_pen(style: CursorStyle) -> QPen:
        return pg.mkPen(
            style.line_color,
            width=max(style.line_width + 1.0, style.line_width * 1.5),
            style=_LINE_STYLES[style.line_style.value],
        )


class CursorPairPlotItem:
    """PyQtGraph overlay showing a measured distance between two cursors."""

    def __init__(
        self,
        pair_state: CursorPairState,
        cursor_type: CursorType,
        annotation_moved: Callable[[QPointF], None],
    ) -> None:
        self.pair_key = pair_state.key
        self.region = pg.LinearRegionItem(
            values=(0.0, 0.0),
            orientation=(
                pg.LinearRegionItem.Vertical
                if cursor_type is CursorType.X
                else pg.LinearRegionItem.Horizontal
            ),
            movable=False,
            pen=None,
            brush=pg.mkBrush(0, 0, 0, 0),
        )
        self.line = _DraggablePairLine(annotation_moved)
        self.first_arrow = pg.ArrowItem(
            angle=0,
            headLen=10,
            tipAngle=35,
            baseAngle=20,
            brush="#666666",
            pen="#666666",
        )
        self.second_arrow = pg.ArrowItem(
            angle=180,
            headLen=10,
            tipAngle=35,
            baseAngle=20,
            brush="#666666",
            pen="#666666",
        )
        self.label = pg.TextItem(
            text="",
            color="#666666",
            anchor=(0.5, 1.0),
        )
        for item in self.items:
            item.setZValue(_CURSOR_PAIR_Z_VALUE)
            item.setVisible(False)
        self.region.setZValue(_CURSOR_Z_VALUE - 1)
        self.label.setZValue(_CURSOR_PAIR_LABEL_Z_VALUE)

    @property
    def items(self) -> tuple[pg.GraphicsObject, ...]:
        return self.region, self.line, self.first_arrow, self.second_arrow, self.label

    def update_from_pair(
        self,
        pair_state: CursorPairState,
        first_state: CursorState,
        second_state: CursorState,
        *,
        text: str,
        effective_visible: bool,
        x_log: bool,
        y_log: bool,
        view_rect,
        plot_background: str,
    ) -> None:
        first_value = CursorPlotItem._display_value(first_state, x_log=x_log, y_log=y_log)
        second_value = CursorPlotItem._display_value(second_state, x_log=x_log, y_log=y_log)
        visible = (
            effective_visible
            and pair_state.measurement_visible
            and first_value is not None
            and second_value is not None
            and view_rect is not None
            and not view_rect.isNull()
        )
        if not visible:
            self._set_visible(False)
            return
        assert first_value is not None
        assert second_value is not None

        overlay_color = _contrast_color(QColor(plot_background))
        region_color = QColor(overlay_color)
        region_color.setAlpha(_PAIR_REGION_ALPHA)
        self.region.setBrush(pg.mkBrush(region_color))
        self.line.set_overlay_color(overlay_color)
        for arrow in (self.first_arrow, self.second_arrow):
            arrow.setStyle(brush=overlay_color, pen=overlay_color)
        self.label.fill = pg.mkBrush(None)
        self.label.border = pg.mkPen(None)
        self.label.setColor(overlay_color)
        self.label.update()

        if first_state.cursor_type is CursorType.X:
            left, right = sorted((first_value, second_value))
            self.region.setRegion((left, right))
            y_value = view_rect.top() + view_rect.height() * pair_state.annotation_position
            self.line.setData([left, right], [y_value, y_value])
            self.first_arrow.setPos(left, y_value)
            self.second_arrow.setPos(right, y_value)
            self.first_arrow.setStyle(angle=180)
            self.second_arrow.setStyle(angle=0)
            self.label.setPos((left + right) / 2.0, y_value)
        else:
            lower, upper = sorted((first_value, second_value))
            self.region.setRegion((lower, upper))
            x_value = view_rect.left() + view_rect.width() * pair_state.annotation_position
            self.line.setData([x_value, x_value], [lower, upper])
            self.first_arrow.setPos(x_value, lower)
            self.second_arrow.setPos(x_value, upper)
            self.first_arrow.setStyle(angle=90)
            self.second_arrow.setStyle(angle=270)
            self.label.setPos(x_value, (lower + upper) / 2.0)

        self.label.setText(text)
        self._set_visible(True)

    def _set_visible(self, visible: bool) -> None:
        self.region.setVisible(visible)
        self.line.setVisible(visible)
        self.first_arrow.setVisible(visible)
        self.second_arrow.setVisible(visible)
        self.label.setVisible(visible)


def _contrast_color(background: QColor) -> QColor:
    return QColor("#111111") if background.lightness() >= 128 else QColor("#f5f5f5")
