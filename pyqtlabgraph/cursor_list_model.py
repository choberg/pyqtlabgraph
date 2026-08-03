from __future__ import annotations

import json
import math
from typing import TYPE_CHECKING
from uuid import uuid4

from PySide6.QtCore import (
    QAbstractListModel,
    QMimeData,
    QModelIndex,
    QObject,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor

from .cursor_ui import (
    _CURSOR_DISPLAY_ROLE,
    _CURSOR_EDIT_FIELD_NAME,
    _CURSOR_EDIT_FIELD_VALUE,
    _CURSOR_MIME_TYPE,
    _cursor_band_rects,
    _cursor_item_height,
    _cursor_pair_member_rect,
    _CursorDisplayRecord,
    _CursorDropOperation,
    _CursorListItemRecord,
    _format_number,
    _row_text,
)
from .models import CursorState, CursorType

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


class _CursorListModel(QAbstractListModel):
    cursor_name_edit_requested = Signal(str, str)
    cursor_value_edit_requested = Signal(str, float)
    pair_requested = Signal(str, str)
    cursor_order_requested = Signal(object)

    def __init__(self, plot: "PyQtLabGraphWidget", parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.plot = plot
        self.edit_field = _CURSOR_EDIT_FIELD_VALUE
        self.edit_cursor_key: str | None = None
        self._model_token = uuid4().hex
        self._row_blocks = self._current_blocks()
        self._active_cursor_by_item = {
            self._item_key(block): block[0]
            for block in self._row_blocks
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._row_blocks)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid():
            return None

        if not 0 <= index.row() < len(self._row_blocks):
            return None
        record = self._display_item(self._row_blocks[index.row()])

        if role == _CURSOR_DISPLAY_ROLE:
            return record
        if role == Qt.ItemDataRole.DisplayRole:
            text = "\n".join(_row_text(cursor_record) for cursor_record in record.cursor_records)
            return f"{text}\n{record.pair_detail_text}" if record.pair_detail_text else text
        if role == Qt.ItemDataRole.EditRole:
            cursor_record = self._cursor_record(record, self.edit_cursor_key)
            if self.edit_field == _CURSOR_EDIT_FIELD_NAME:
                return cursor_record.name
            return cursor_record.edit_value_text
        if role == Qt.ItemDataRole.ToolTipRole:
            return self._tooltip_text(record)
        if role == Qt.ItemDataRole.SizeHintRole:
            return QSize(160, _cursor_item_height(record))
        return None

    def supportedDropActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def supportedDragActions(self) -> Qt.DropAction:
        return Qt.DropAction.MoveAction

    def mimeTypes(self) -> list[str]:
        return [_CURSOR_MIME_TYPE]

    def mimeData(self, indexes: list[QModelIndex]) -> QMimeData:
        mime_data = QMimeData()
        rows = sorted({index.row() for index in indexes if index.isValid()})
        cursor_keys = [
            cursor_key
            for row in rows
            if 0 <= row < len(self._row_blocks)
            for cursor_key in self._row_blocks[row]
        ]
        if not cursor_keys:
            return mime_data
        payload = {
            "model_token": self._model_token,
            "cursor_keys": cursor_keys,
        }
        mime_data.setData(_CURSOR_MIME_TYPE, json.dumps(payload).encode("utf-8"))
        return mime_data

    def canDropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        return self._drop_operation(data, action, row, column, parent) is not None

    def dropMimeData(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> bool:
        operation = self._drop_operation(data, action, row, column, parent)
        if operation is None:
            return False
        if operation.pair_keys is not None:
            self.pair_requested.emit(*operation.pair_keys)
        elif operation.cursor_order is not None:
            self.cursor_order_requested.emit(operation.cursor_order)
        else:
            return False
        return True

    def setData(
        self,
        index: QModelIndex,
        value: object,
        role: int = Qt.ItemDataRole.EditRole,
    ) -> bool:
        if role != Qt.ItemDataRole.EditRole or not index.isValid():
            return False

        if not 0 <= index.row() < len(self._row_blocks):
            return False
        block = self._row_blocks[index.row()]
        cursor_key = (
            self.edit_cursor_key
            if self.edit_cursor_key in block
            else self.active_cursor_key(index.row())
        )
        if cursor_key is None:
            return False
        if self.edit_field == _CURSOR_EDIT_FIELD_NAME:
            name = str(value).strip()
            if not name:
                return False
            self.cursor_name_edit_requested.emit(cursor_key, name)
        else:
            try:
                numeric_value = float(str(value))
            except (TypeError, ValueError):
                return False
            if not math.isfinite(numeric_value):
                return False
            self.cursor_value_edit_requested.emit(cursor_key, numeric_value)

        row_index = self.index(index.row(), 0)
        self.dataChanged.emit(row_index, row_index, [Qt.ItemDataRole.DisplayRole, _CURSOR_DISPLAY_ROLE])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.ItemIsDropEnabled
        return (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsDragEnabled
            | Qt.ItemFlag.ItemIsDropEnabled
        )

    def refresh(self) -> None:
        active_cursor_keys = set(self._active_cursor_by_item.values())
        self.beginResetModel()
        self._row_blocks = self._current_blocks()
        self._active_cursor_by_item = {}
        for block in self._row_blocks:
            item_key = self._item_key(block)
            self._active_cursor_by_item[item_key] = next(
                (key for key in block if key in active_cursor_keys),
                block[0],
            )
        self.endResetModel()

    def refresh_cursor(self, cursor_key: str) -> None:
        row = self.row_for_cursor(cursor_key)
        if row is None:
            return
        index = self.index(row, 0)
        self.dataChanged.emit(
            index,
            index,
            [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.EditRole,
                Qt.ItemDataRole.ToolTipRole,
                Qt.ItemDataRole.SizeHintRole,
                _CURSOR_DISPLAY_ROLE,
            ],
        )

    def refresh_pair(self, pair_key: str) -> None:
        for row in range(len(self._row_blocks)):
            if self._display_item(self._row_blocks[row]).pair_key != pair_key:
                continue
            index = self.index(row, 0)
            self.dataChanged.emit(
                index,
                index,
                [
                    Qt.ItemDataRole.DisplayRole,
                    Qt.ItemDataRole.ToolTipRole,
                    Qt.ItemDataRole.SizeHintRole,
                    _CURSOR_DISPLAY_ROLE,
                ],
            )
            return

    def display_record(self, row: int) -> _CursorDisplayRecord:
        cursor_key = self.active_cursor_key(row)
        if cursor_key is None:
            raise IndexError(row)
        return self._display_record(self.plot.cursor_state(cursor_key))

    def display_item(self, row: int) -> _CursorListItemRecord:
        if not 0 <= row < len(self._row_blocks):
            raise IndexError(row)
        return self._display_item(self._row_blocks[row])

    def cursor_keys(self) -> tuple[str, ...]:
        return tuple(key for block in self._row_blocks for key in block)

    def cursor_key(self, row: int) -> str | None:
        return self.active_cursor_key(row)

    def block_cursor_keys(self, row: int) -> tuple[str, ...]:
        if 0 <= row < len(self._row_blocks):
            return self._row_blocks[row]
        return ()

    def row_for_cursor(self, cursor_key: str) -> int | None:
        return next(
            (row for row, block in enumerate(self._row_blocks) if cursor_key in block),
            None,
        )

    def active_cursor_key(self, row: int) -> str | None:
        if not 0 <= row < len(self._row_blocks):
            return None
        block = self._row_blocks[row]
        return self._active_cursor_by_item.get(self._item_key(block), block[0])

    def set_active_cursor(self, row: int, cursor_key: str) -> None:
        if not 0 <= row < len(self._row_blocks) or cursor_key not in self._row_blocks[row]:
            raise ValueError(f'Cursor "{cursor_key}" does not belong to row {row}.')
        self._active_cursor_by_item[self._item_key(self._row_blocks[row])] = cursor_key

    def cursor_rect(self, row: int, cursor_key: str | None, item_rect: QRect) -> QRect:
        record = self.display_item(row)
        resolved_key = cursor_key or self.active_cursor_key(row)
        for cursor_record, cursor_rect in zip(record.cursor_records, _cursor_band_rects(item_rect, record)):
            if cursor_record.key == resolved_key:
                return _cursor_pair_member_rect(cursor_rect) if record.pair_key is not None else cursor_rect
        return item_rect

    def _drop_operation(
        self,
        data: QMimeData,
        action: Qt.DropAction,
        row: int,
        column: int,
        parent: QModelIndex,
    ) -> _CursorDropOperation | None:
        source_keys = self._dragged_cursor_keys(data, action)
        if source_keys is None or column not in {-1, 0}:
            return None

        if parent.isValid():
            if len(source_keys) != 1:
                return None
            target_block = self.block_cursor_keys(parent.row())
            if len(target_block) != 1 or not self._can_pair(source_keys[0], target_block[0]):
                return None
            return _CursorDropOperation(pair_keys=(source_keys[0], target_block[0]))

        destination_row = len(self._row_blocks) if row < 0 else row
        cursor_order = self._reordered_cursor_keys(source_keys, destination_row)
        if cursor_order is None or cursor_order == self.cursor_keys():
            return None
        return _CursorDropOperation(cursor_order=cursor_order)

    def _dragged_cursor_keys(
        self,
        data: QMimeData,
        action: Qt.DropAction,
    ) -> tuple[str, ...] | None:
        if action != Qt.DropAction.MoveAction or not data.hasFormat(_CURSOR_MIME_TYPE):
            return None
        try:
            payload = json.loads(bytes(data.data(_CURSOR_MIME_TYPE)).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or payload.get("model_token") != self._model_token:
            return None
        raw_keys = payload.get("cursor_keys")
        if not isinstance(raw_keys, list) or not raw_keys:
            return None
        if any(not isinstance(key, str) for key in raw_keys) or len(set(raw_keys)) != len(raw_keys):
            return None
        if any(key not in self.cursor_keys() for key in raw_keys):
            return None
        return tuple(raw_keys)

    def _can_pair(self, source_key: str, target_key: str) -> bool:
        if source_key == target_key:
            return False
        source_state = self.plot.cursor_state(source_key)
        target_state = self.plot.cursor_state(target_key)
        return (
            source_state.cursor_type is target_state.cursor_type
            and self.plot.cursor_pair_for_cursor(source_key) is None
            and self.plot.cursor_pair_for_cursor(target_key) is None
        )

    def _reordered_cursor_keys(
        self,
        source_keys: tuple[str, ...],
        destination_row: int,
    ) -> tuple[str, ...] | None:
        if not 0 <= destination_row <= len(self._row_blocks):
            return None

        source_set = set(source_keys)
        selected_indexes = [
            index
            for index, block in enumerate(self._row_blocks)
            if source_set.intersection(block)
        ]
        if not selected_indexes:
            return None

        destination_index = destination_row
        selected_blocks = [self._row_blocks[index] for index in selected_indexes]
        remaining_blocks = [
            block
            for index, block in enumerate(self._row_blocks)
            if index not in selected_indexes
        ]
        adjusted_destination = destination_index - sum(
            index < destination_index for index in selected_indexes
        )
        reordered_blocks = (
            remaining_blocks[:adjusted_destination]
            + selected_blocks
            + remaining_blocks[adjusted_destination:]
        )
        return tuple(cursor_key for block in reordered_blocks for cursor_key in block)

    def _current_blocks(self) -> list[tuple[str, ...]]:
        blocks: list[tuple[str, ...]] = []
        consumed: set[str] = set()
        for state in self.plot.cursor_states():
            cursor_key = state.key
            if cursor_key in consumed:
                continue
            pair_state = self.plot.cursor_pair_for_cursor(cursor_key)
            block: tuple[str, ...]
            if pair_state is None:
                block = (cursor_key,)
            else:
                block = (pair_state.first_cursor_key, pair_state.second_cursor_key)
            blocks.append(block)
            consumed.update(block)
        return blocks

    @staticmethod
    def _item_key(block: tuple[str, ...]) -> tuple[str, ...]:
        return block

    def _display_item(self, block: tuple[str, ...]) -> _CursorListItemRecord:
        cursor_records = tuple(
            self._display_record(self.plot.cursor_state(cursor_key))
            for cursor_key in block
        )
        pair_state = self.plot.cursor_pair_for_cursor(block[0]) if len(block) == 2 else None
        if pair_state is None:
            pair_detail_text = ""
            measurement_label, measurement_value, measurement_secondary = "", "", ""
        else:
            pair_detail_text = self.plot.cursor_pair_measurement_text(pair_state.key)
            measurement_label, measurement_value, measurement_secondary = self.plot.cursor_pair_measurement_parts(
                pair_state.key
            )
        return _CursorListItemRecord(
            item_key=self._item_key(block),
            cursor_records=cursor_records,
            pair_key=None if pair_state is None else pair_state.key,
            pair_detail_text=pair_detail_text,
            pair_measurement_label=measurement_label,
            pair_measurement_value=measurement_value,
            pair_measurement_secondary=measurement_secondary,
            pair_distance_visible=True if pair_state is None else pair_state.measurement_visible,
        )

    @staticmethod
    def _cursor_record(
        item_record: _CursorListItemRecord,
        cursor_key: str | None,
    ) -> _CursorDisplayRecord:
        return next(
            (record for record in item_record.cursor_records if record.key == cursor_key),
            item_record.cursor_records[0],
        )

    def _display_record(self, state: CursorState) -> _CursorDisplayRecord:
        target_value = self.plot.cursor_target_value(state.key)
        return _CursorDisplayRecord(
            key=state.key,
            name=state.name,
            type_label=state.cursor_type.value.upper(),
            value_text=self.plot.format_cursor_value(state.cursor_type, state.value),
            edit_value_text=_format_number(state.value),
            target_curve_text=state.snap_target_curve_key or "",
            target_value_text=(
                ""
                if target_value is None
                else self.plot.format_cursor_value(CursorType.Y, target_value)
            ),
            color=QColor(state.style.line_color),
            visible=state.visible,
            show_label=state.label_visible,
            snap_enabled=state.snap_target_curve_key is not None,
            selected=state.key in self.plot.selected_cursor_keys(),
        )

    def _tooltip_text(self, record: _CursorListItemRecord) -> str:
        parts: list[str] = []
        for cursor_record in record.cursor_records:
            parts.extend(
                [
                    f"{cursor_record.name} ({cursor_record.type_label})",
                    f"Value: {cursor_record.value_text}",
                ]
            )
            if cursor_record.target_curve_text:
                parts.append(f"Target curve: {cursor_record.target_curve_text}")
                if cursor_record.target_value_text:
                    parts.append(f"Target value: {cursor_record.target_value_text}")
        if record.pair_detail_text:
            parts.append(record.pair_detail_text)
        return "\n".join(parts)
