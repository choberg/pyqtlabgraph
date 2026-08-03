from __future__ import annotations

import math

from PySide6.QtCore import QAbstractListModel, QModelIndex, QPointF, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLineEdit, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QWidget

from .cursor_ui import (
    _CURSOR_CARD_INSET_X,
    _CURSOR_DISPLAY_ROLE,
    _CURSOR_EDIT_FIELD_NAME,
    _CURSOR_EDIT_FIELD_VALUE,
    _CURSOR_ROW_GAP,
    _CURSOR_ROW_HEIGHT,
    _cursor_band_rects,
    _cursor_color_rect,
    _cursor_detail_rect,
    _cursor_item_height,
    _cursor_menu_rect,
    _cursor_name_rect,
    _cursor_pair_footer_rect,
    _cursor_pair_measurement_rects,
    _cursor_pair_member_rect,
    _cursor_pair_visibility_rect,
    _cursor_value_rect,
    _cursor_visibility_rect,
    _CursorDisplayRecord,
    _CursorListItemRecord,
)

_CURSOR_CARD_INSET_Y = 2
_CURSOR_CARD_RADIUS = 4.0
_CURSOR_PAIR_CARD_RADIUS = 4.0
_CURSOR_CARD_BORDER_WIDTH = 1.0
_CURSOR_PAIR_CARD_BORDER_WIDTH = 1.2
_CURSOR_PAIR_MEMBER_RADIUS = 3.0
_CURSOR_SELECTION_ALPHA = 28
_CURSOR_HOVER_ALPHA = 14
_CURSOR_GLYPH_BORDER_WIDTH = 1.4
_CURSOR_GLYPH_AXIS_WIDTH = 3.2
_CURSOR_GLYPH_INSET = 2.0
_CURSOR_GLYPH_AXIS_INSET = 4.5
_CURSOR_COLOR_SWATCH_SIZE = 16
_CURSOR_DETAIL_TEXT_LIGHTNESS_THRESHOLD = 130
_CURSOR_COLOR_BUTTON_BORDER = "#888888"
_CURSOR_COLOR_BUTTON_LIGHT_TEXT = "#ffffff"
_CURSOR_COLOR_BUTTON_DARK_TEXT = "#000000"
_CURSOR_COLOR_BUTTON_LIGHTNESS_THRESHOLD = 128
_CURSOR_LINE_STYLE_LABELS = {
    "solid": "Solid",
    "dash": "Dash",
    "dot": "Dot",
    "dash-dot": "Dash-dot",
}
class _CursorListDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        record = index.data(_CURSOR_DISPLAY_ROLE)
        if not isinstance(record, _CursorListItemRecord):
            super().paint(painter, option, index)
            return

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        hovered = bool(option.state & QStyle.StateFlag.State_MouseOver)
        _draw_cursor_item_background(painter, option, record, selected=selected, hovered=hovered)
        for cursor_record, cursor_rect in zip(record.cursor_records, _cursor_band_rects(option.rect, record)):
            paired = record.pair_key is not None
            _draw_cursor_band(
                painter,
                option,
                cursor_record,
                _cursor_pair_member_rect(cursor_rect) if paired else cursor_rect,
                active=cursor_record.selected,
                hovered=hovered and paired,
                framed=paired,
            )
        if record.pair_key is not None:
            _draw_pair_footer(painter, option, record)

        painter.restore()

    def sizeHint(self, option: QStyleOptionViewItem, index: QModelIndex) -> QSize:
        record = index.data(_CURSOR_DISPLAY_ROLE)
        height = _cursor_item_height(record) if isinstance(record, _CursorListItemRecord) else _CURSOR_ROW_HEIGHT
        return QSize(option.rect.width(), height)

    def createEditor(self, parent: QWidget, _option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        editor = QLineEdit(parent)
        model = index.model()
        edit_field = getattr(model, "edit_field", _CURSOR_EDIT_FIELD_VALUE)
        editor.setObjectName(
            "pyqtLabGraphCursorNameEditor"
            if edit_field == _CURSOR_EDIT_FIELD_NAME
            else "pyqtLabGraphCursorValueEditor"
        )
        editor.setFrame(False)
        return editor

    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        if isinstance(editor, QLineEdit):
            editor.setText(str(index.data(Qt.ItemDataRole.EditRole) or ""))
            editor.selectAll()

    def setModelData(self, editor: QWidget, model: QAbstractListModel, index: QModelIndex) -> None:
        if isinstance(editor, QLineEdit):
            model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

    def updateEditorGeometry(self, editor: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        model = index.model()
        edit_field = getattr(model, "edit_field", _CURSOR_EDIT_FIELD_VALUE)
        cursor_rect = (
            model.cursor_rect(index.row(), getattr(model, "edit_cursor_key", None), option.rect)
            if hasattr(model, "cursor_rect")
            else option.rect
        )
        editor.setGeometry(
            _cursor_name_rect(cursor_rect)
            if edit_field == _CURSOR_EDIT_FIELD_NAME
            else _cursor_value_rect(cursor_rect)
        )


def _draw_cursor_item_background(
    painter: QPainter,
    option: QStyleOptionViewItem,
    record: _CursorListItemRecord,
    *,
    selected: bool,
    hovered: bool,
) -> None:
    rect = QRectF(option.rect).adjusted(
        _CURSOR_CARD_INSET_X,
        _CURSOR_CARD_INSET_Y,
        -_CURSOR_CARD_INSET_X,
        -_CURSOR_CARD_INSET_Y,
    )
    highlight = option.palette.highlight().color()
    text_color = option.palette.text().color()
    base_color = option.palette.base().color()
    paired = record.pair_key is not None
    border_color = _card_border_color(text_color, base_color, selected=selected, strong=paired)
    if paired:
        background = _pair_card_background_color(base_color, highlight, selected=selected, hovered=hovered)
    else:
        background = _card_background_color(base_color, highlight, selected=selected, hovered=hovered)
    _draw_round_rect(
        painter,
        rect,
        background,
        border_color,
        _CURSOR_PAIR_CARD_RADIUS if paired else _CURSOR_CARD_RADIUS,
        _CURSOR_PAIR_CARD_BORDER_WIDTH if paired else _CURSOR_CARD_BORDER_WIDTH,
    )

    if selected:
        accent_rect = QRectF(
            rect.left() + 1.0,
            rect.top() + 5.0,
            2.0,
            max(8.0, rect.height() - 10.0),
        )
        accent = QColor(highlight)
        accent.setAlpha(170)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(accent)
        painter.drawRoundedRect(accent_rect, 1.0, 1.0)


def _draw_cursor_band(
    painter: QPainter,
    option: QStyleOptionViewItem,
    record: _CursorDisplayRecord,
    rect: QRect,
    *,
    active: bool,
    hovered: bool,
    framed: bool,
) -> None:
    if framed:
        inner_border = _card_border_color(
            option.palette.text().color(),
            option.palette.base().color(),
            selected=active,
            strong=False,
        )
        member_background = _card_background_color(
            option.palette.base().color(),
            option.palette.highlight().color(),
            selected=active,
            hovered=hovered,
        )
        _draw_round_rect(
            painter,
            QRectF(rect).adjusted(0.5, 0.5, -0.5, -0.5),
            member_background,
            inner_border,
            _CURSOR_PAIR_MEMBER_RADIUS,
            _CURSOR_CARD_BORDER_WIDTH,
        )

    color_rect = _cursor_color_rect(rect)
    glyph_color = record.color if record.visible else option.palette.mid().color()
    _draw_cursor_glyph(painter, color_rect, glyph_color, record.type_label)

    menu_rect = _cursor_menu_rect(rect)
    visibility_rect = _cursor_visibility_rect(rect)
    value_rect = _cursor_value_rect(rect)
    name_rect = _cursor_name_rect(rect)
    text_color = option.palette.text().color() if record.visible else option.palette.mid().color()
    painter.setPen(text_color)
    painter.drawText(
        name_rect,
        Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine,
        option.fontMetrics.elidedText(record.name, Qt.TextElideMode.ElideRight, name_rect.width()),
    )
    painter.drawText(value_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, record.value_text)
    _draw_visibility_glyph(
        painter,
        visibility_rect,
        option.palette.text().color() if record.visible else option.palette.mid().color(),
        visible=record.visible,
    )
    painter.setPen(option.palette.mid().color())
    painter.drawText(menu_rect, Qt.AlignmentFlag.AlignCenter, "⋯")

    detail_rect = _cursor_detail_rect(rect)
    if detail_rect.isValid() and record.detail_text:
        painter.setPen(_readable_secondary_color(option.palette.text().color(), option.palette.base().color()))
        detail_text_rect = QRect(
            name_rect.left(),
            detail_rect.top(),
            menu_rect.left() - name_rect.left() - _CURSOR_ROW_GAP,
            detail_rect.height(),
        )
        painter.drawText(
            detail_text_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine,
            option.fontMetrics.elidedText(record.detail_text, Qt.TextElideMode.ElideRight, detail_text_rect.width()),
        )


def _draw_pair_footer(
    painter: QPainter,
    option: QStyleOptionViewItem,
    record: _CursorListItemRecord,
) -> None:
    footer_rect = _cursor_pair_footer_rect(option.rect, record)
    result_text = f"{record.pair_measurement_label} {record.pair_measurement_value}"
    result_width = option.fontMetrics.horizontalAdvance(result_text) + _CURSOR_ROW_GAP
    arrow_rect, result_rect, secondary_rect = _cursor_pair_measurement_rects(
        footer_rect,
        result_width,
    )
    secondary_color = _readable_secondary_color(option.palette.text().color(), option.palette.base().color())
    painter.setPen(secondary_color)
    painter.drawText(
        arrow_rect,
        Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextSingleLine,
        "→",
    )

    painter.setPen(option.palette.text().color())
    painter.drawText(
        result_rect,
        Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine,
        option.fontMetrics.elidedText(result_text, Qt.TextElideMode.ElideRight, result_rect.width()),
    )
    if secondary_rect.width() > 0 and record.pair_measurement_secondary:
        painter.setPen(secondary_color)
        painter.drawText(
            secondary_rect,
            Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine,
            option.fontMetrics.elidedText(
                record.pair_measurement_secondary,
                Qt.TextElideMode.ElideRight,
                secondary_rect.width(),
            ),
        )

    _draw_visibility_glyph(
        painter,
        _cursor_pair_visibility_rect(footer_rect),
        option.palette.text().color() if record.pair_distance_visible else option.palette.mid().color(),
        visible=record.pair_distance_visible,
    )


def _draw_round_rect(
    painter: QPainter,
    rect: QRectF,
    background: QColor,
    border_color: QColor,
    radius: float,
    border_width: float,
) -> None:
    painter.setPen(
        QPen(
            border_color,
            border_width,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.setBrush(background)
    painter.drawRoundedRect(rect, radius, radius)


def _card_background_color(base_color: QColor, highlight: QColor, *, selected: bool, hovered: bool) -> QColor:
    color = QColor(base_color)
    if selected:
        return _blend_color(color, highlight, _CURSOR_SELECTION_ALPHA)
    if hovered:
        return _blend_color(color, highlight, _CURSOR_HOVER_ALPHA)
    return color


def _pair_card_background_color(base_color: QColor, highlight: QColor, *, selected: bool, hovered: bool) -> QColor:
    color = QColor(base_color)
    if selected:
        return _blend_color(color, highlight, _CURSOR_SELECTION_ALPHA)
    if hovered:
        return _blend_color(color, highlight, _CURSOR_HOVER_ALPHA)
    return color


def _card_border_color(text_color: QColor, base_color: QColor, *, selected: bool, strong: bool) -> QColor:
    color = QColor(text_color)
    if selected:
        color.setAlpha(95 if strong else 75)
    else:
        color.setAlpha(70 if strong else 42)
    if abs(text_color.lightness() - base_color.lightness()) < 45:
        color = base_color.darker(135) if base_color.lightness() > 127 else base_color.lighter(145)
        color.setAlpha(90 if strong else 60)
    return color


def _blend_color(base_color: QColor, overlay_color: QColor, alpha: int) -> QColor:
    ratio = max(0, min(alpha, 255)) / 255.0
    return QColor(
        round(base_color.red() * (1.0 - ratio) + overlay_color.red() * ratio),
        round(base_color.green() * (1.0 - ratio) + overlay_color.green() * ratio),
        round(base_color.blue() * (1.0 - ratio) + overlay_color.blue() * ratio),
    )


def _draw_cursor_glyph(painter: QPainter, rect: QRect, color: QColor, type_label: str) -> None:
    glyph_rect = QRectF(rect).adjusted(
        _CURSOR_GLYPH_INSET,
        _CURSOR_GLYPH_INSET,
        -_CURSOR_GLYPH_INSET,
        -_CURSOR_GLYPH_INSET,
    )
    fill_color = QColor(color)
    fill_color.setAlpha(44 if color.alpha() > 80 else color.alpha())

    painter.setBrush(fill_color)
    painter.setPen(
        QPen(
            color,
            _CURSOR_GLYPH_BORDER_WIDTH,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
            Qt.PenJoinStyle.RoundJoin,
        )
    )
    painter.drawEllipse(glyph_rect)

    center = glyph_rect.center()
    painter.setPen(
        QPen(
            color,
            _CURSOR_GLYPH_AXIS_WIDTH,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    if type_label == "X":
        painter.drawLine(
            QPointF(center.x(), glyph_rect.top() + _CURSOR_GLYPH_AXIS_INSET),
            QPointF(center.x(), glyph_rect.bottom() - _CURSOR_GLYPH_AXIS_INSET),
        )
    else:
        painter.drawLine(
            QPointF(glyph_rect.left() + _CURSOR_GLYPH_AXIS_INSET, center.y()),
            QPointF(glyph_rect.right() - _CURSOR_GLYPH_AXIS_INSET, center.y()),
        )


def _draw_visibility_glyph(
    painter: QPainter,
    rect: QRect,
    color: QColor,
    *,
    visible: bool,
) -> None:
    center = QPointF(rect.center())
    eye_rect = QRectF(center.x() - 7.0, center.y() - 4.5, 14.0, 9.0)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    eye_pen = QPen(color, 1.2)
    eye_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(eye_pen)
    painter.drawEllipse(eye_rect)
    if visible:
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, 2.2, 2.2)
    else:
        hidden_pen = QPen(color, 1.4)
        hidden_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(hidden_pen)
        painter.drawLine(
            QPointF(eye_rect.left() + 1.0, eye_rect.bottom() + 1.0),
            QPointF(eye_rect.right() - 1.0, eye_rect.top() - 1.0),
        )


def _readable_secondary_color(text_color: QColor, base_color: QColor) -> QColor:
    if abs(text_color.lightness() - base_color.lightness()) < _CURSOR_DETAIL_TEXT_LIGHTNESS_THRESHOLD:
        return text_color
    return text_color.lighter(135) if text_color.lightness() < base_color.lightness() else text_color.darker(135)


def _color_swatch_icon(color: QColor) -> QIcon:
    pixmap = QPixmap(_CURSOR_COLOR_SWATCH_SIZE, _CURSOR_COLOR_SWATCH_SIZE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setPen(QPen(QColor(_CURSOR_COLOR_BUTTON_BORDER), 1))
    painter.setBrush(color)
    painter.drawRoundedRect(1, 1, _CURSOR_COLOR_SWATCH_SIZE - 2, _CURSOR_COLOR_SWATCH_SIZE - 2, 3, 3)
    painter.end()
    return QIcon(pixmap)


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return ""
    return f"{value:.6g}"
