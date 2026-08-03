from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor

_CURSOR_WIDGET_MARGINS = (2, 2, 2, 2)
_CURSOR_WIDGET_SPACING = 2
_CURSOR_PREFERRED_SIZE = QSize(280, 240)
_CURSOR_MINIMUM_SIZE = QSize(220, 120)
_CURSOR_HEADER_MARGINS = (6, 3, 4, 3)
_CURSOR_HEADER_SPACING = 4
_CURSOR_ROW_HEIGHT = 34
_CURSOR_ROW_HEIGHT_WITH_DETAIL = 48
_CURSOR_PAIR_FOOTER_HEIGHT = 32
_CURSOR_ROW_MARGIN = 6
_CURSOR_CARD_INSET_X = 3
_CURSOR_PAIR_MEMBER_INSET_X = 8
_CURSOR_PAIR_MEMBER_INSET_Y = 2
_CURSOR_PAIR_CONTENT_MARGIN_Y = 6
_CURSOR_ROW_GAP = 6
_CURSOR_GLYPH_SIZE = 18
_CURSOR_VALUE_WIDTH = 86
_CURSOR_VISIBILITY_WIDTH = 28
_CURSOR_MENU_WIDTH = 28
_CURSOR_PAIR_RESULT_ARROW_WIDTH = 18
_CURSOR_PAIR_RESULT_MIN_WIDTH = 52
_CURSOR_KEYBOARD_FINE_STEP_RATIO = 0.001
_CURSOR_KEYBOARD_STEP_RATIO = 0.01
_CURSOR_KEYBOARD_COARSE_STEP_RATIO = 0.1
_CURSOR_DISPLAY_ROLE = int(Qt.ItemDataRole.UserRole) + 1
_CURSOR_MIME_TYPE = "application/x-pyqtlabgraph-cursor-key"
_CURSOR_EDIT_FIELD_NAME = "name"
_CURSOR_EDIT_FIELD_VALUE = "value"
_CURSOR_QUICK_COLORS = (
    ("Blue", "#0072B2"),
    ("Orange", "#D55E00"),
    ("Green", "#009E73"),
    ("Pink", "#CC79A7"),
    ("Yellow", "#E69F00"),
    ("Sky", "#56B4E9"),
    ("Black", "#000000"),
    ("Gray", "#666666"),
)


@dataclass(frozen=True)
class _CursorDisplayRecord:
    key: str
    name: str
    type_label: str
    value_text: str
    edit_value_text: str
    target_curve_text: str
    target_value_text: str
    color: QColor
    visible: bool
    show_label: bool
    snap_enabled: bool
    selected: bool

    @property
    def detail_text(self) -> str:
        if self.target_curve_text and self.target_value_text:
            return f"{self.target_curve_text}  {self.target_value_text}"
        if self.target_curve_text:
            return f"{self.target_curve_text}  no value"
        return ""


@dataclass(frozen=True)
class _CursorListItemRecord:
    item_key: tuple[str, ...]
    cursor_records: tuple[_CursorDisplayRecord, ...]
    pair_key: str | None = None
    pair_detail_text: str = ""
    pair_measurement_label: str = ""
    pair_measurement_value: str = ""
    pair_measurement_secondary: str = ""
    pair_distance_visible: bool = True


@dataclass(frozen=True)
class _CursorDropOperation:
    pair_keys: tuple[str, str] | None = None
    cursor_order: tuple[str, ...] | None = None


def _row_text(record: _CursorDisplayRecord) -> str:
    values = [record.type_label, record.name, record.value_text]
    if record.target_curve_text:
        values.extend([record.target_curve_text, record.target_value_text])
    return "\t".join(values)


def _cursor_primary_rect(rect: QRect) -> QRect:
    return QRect(rect.left(), rect.top(), rect.width(), min(_CURSOR_ROW_HEIGHT, rect.height()))


def _cursor_detail_rect(rect: QRect) -> QRect:
    if rect.height() <= _CURSOR_ROW_HEIGHT:
        return QRect()
    return QRect(
        rect.left(),
        rect.top() + _CURSOR_ROW_HEIGHT - 4,
        rect.width(),
        rect.height() - _CURSOR_ROW_HEIGHT + 2,
    )


def _cursor_menu_rect(rect: QRect) -> QRect:
    return QRect(
        rect.right() - _CURSOR_MENU_WIDTH + 1,
        rect.top(),
        _CURSOR_MENU_WIDTH,
        min(_CURSOR_ROW_HEIGHT, rect.height()),
    )


def _cursor_visibility_rect(rect: QRect) -> QRect:
    menu_rect = _cursor_menu_rect(rect)
    return QRect(
        menu_rect.left() - _CURSOR_VISIBILITY_WIDTH,
        rect.top(),
        _CURSOR_VISIBILITY_WIDTH,
        min(_CURSOR_ROW_HEIGHT, rect.height()),
    )


def _cursor_pair_measurement_rects(
    footer_rect: QRect,
    result_width: int,
) -> tuple[QRect, QRect, QRect]:
    content_left = footer_rect.left() + _CURSOR_CARD_INSET_X + _CURSOR_ROW_MARGIN
    content_right = _cursor_pair_visibility_rect(footer_rect).left() - _CURSOR_ROW_GAP
    available_width = max(0, content_right - content_left)
    arrow_width = min(
        _CURSOR_PAIR_RESULT_ARROW_WIDTH,
        max(0, available_width - _CURSOR_PAIR_RESULT_MIN_WIDTH),
    )
    arrow_rect = QRect(content_left, footer_rect.top(), arrow_width, footer_rect.height())
    result_left = arrow_rect.right() + _CURSOR_ROW_GAP + 1
    available_result_width = max(0, content_right - result_left)
    result_width = min(max(_CURSOR_PAIR_RESULT_MIN_WIDTH, result_width), available_result_width)
    result_rect = QRect(result_left, footer_rect.top(), result_width, footer_rect.height())
    secondary_left = result_rect.right() + _CURSOR_ROW_GAP + 1
    secondary_rect = QRect(
        secondary_left,
        footer_rect.top(),
        max(0, content_right - secondary_left),
        footer_rect.height(),
    )
    return arrow_rect, result_rect, secondary_rect


def _cursor_value_rect(rect: QRect) -> QRect:
    visibility_rect = _cursor_visibility_rect(rect)
    return QRect(
        visibility_rect.left() - _CURSOR_VALUE_WIDTH - _CURSOR_ROW_GAP,
        rect.top() + 3,
        _CURSOR_VALUE_WIDTH,
        min(_CURSOR_ROW_HEIGHT - 6, rect.height() - 6),
    )


def _cursor_color_rect(rect: QRect) -> QRect:
    primary_rect = _cursor_primary_rect(
        rect.adjusted(_CURSOR_ROW_MARGIN, 0, -_CURSOR_ROW_MARGIN, 0)
    )
    return QRect(
        primary_rect.left(),
        primary_rect.top() + (primary_rect.height() - _CURSOR_GLYPH_SIZE) // 2,
        _CURSOR_GLYPH_SIZE,
        _CURSOR_GLYPH_SIZE,
    )


def _cursor_name_rect(rect: QRect) -> QRect:
    primary_rect = _cursor_primary_rect(
        rect.adjusted(_CURSOR_ROW_MARGIN, 0, -_CURSOR_ROW_MARGIN, 0)
    )
    color_rect = _cursor_color_rect(rect)
    value_rect = _cursor_value_rect(rect)
    name_left = color_rect.right() + _CURSOR_ROW_GAP + 1
    return QRect(
        name_left,
        primary_rect.top(),
        max(20, value_rect.left() - name_left - _CURSOR_ROW_GAP),
        primary_rect.height(),
    )


def _cursor_band_height(record: _CursorDisplayRecord) -> int:
    return _CURSOR_ROW_HEIGHT_WITH_DETAIL if record.detail_text else _CURSOR_ROW_HEIGHT


def _cursor_item_height(record: _CursorListItemRecord) -> int:
    cursor_height = sum(_cursor_band_height(item) for item in record.cursor_records)
    if record.pair_key is None:
        return cursor_height
    return cursor_height + _CURSOR_PAIR_FOOTER_HEIGHT + 2 * _CURSOR_PAIR_CONTENT_MARGIN_Y


def _cursor_band_rects(
    rect: QRect,
    record: _CursorListItemRecord,
) -> tuple[QRect, ...]:
    top = rect.top() + (_CURSOR_PAIR_CONTENT_MARGIN_Y if record.pair_key is not None else 0)
    bands: list[QRect] = []
    for cursor_record in record.cursor_records:
        height = _cursor_band_height(cursor_record)
        bands.append(QRect(rect.left(), top, rect.width(), height))
        top += height
    return tuple(bands)


def _cursor_pair_footer_rect(rect: QRect, record: _CursorListItemRecord) -> QRect:
    if record.pair_key is None:
        return QRect()
    top = (
        rect.top()
        + _CURSOR_PAIR_CONTENT_MARGIN_Y
        + sum(_cursor_band_height(item) for item in record.cursor_records)
    )
    return QRect(rect.left(), top, rect.width(), _CURSOR_PAIR_FOOTER_HEIGHT)


def _cursor_pair_visibility_rect(footer_rect: QRect) -> QRect:
    return QRect(
        footer_rect.right() - _CURSOR_VISIBILITY_WIDTH - _CURSOR_CARD_INSET_X + 1,
        footer_rect.top(),
        _CURSOR_VISIBILITY_WIDTH,
        footer_rect.height(),
    )


def _cursor_pair_member_rect(rect: QRect) -> QRect:
    return rect.adjusted(
        _CURSOR_PAIR_MEMBER_INSET_X,
        _CURSOR_PAIR_MEMBER_INSET_Y,
        -_CURSOR_PAIR_MEMBER_INSET_X,
        -_CURSOR_PAIR_MEMBER_INSET_Y,
    )


def _format_number(value: float) -> str:
    return "" if not math.isfinite(value) else f"{value:.6g}"
