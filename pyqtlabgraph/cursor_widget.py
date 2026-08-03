from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import (
    QItemSelectionModel,
    QModelIndex,
    QPoint,
    QRect,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QAction, QColor, QKeyEvent, QPaintEvent
from PySide6.QtWidgets import (
    QApplication,
    QColorDialog,
    QHBoxLayout,
    QLabel,
    QListView,
    QMenu,
    QMessageBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .cursor_actions import _CursorActionController
from .cursor_delegate import _color_swatch_icon, _CursorListDelegate
from .cursor_list_model import _CursorListModel
from .cursor_settings import _CursorSettingsDialog
from .cursor_ui import (
    _CURSOR_DISPLAY_ROLE,
    _CURSOR_EDIT_FIELD_NAME,
    _CURSOR_EDIT_FIELD_VALUE,
    _CURSOR_HEADER_MARGINS,
    _CURSOR_HEADER_SPACING,
    _CURSOR_KEYBOARD_COARSE_STEP_RATIO,
    _CURSOR_KEYBOARD_FINE_STEP_RATIO,
    _CURSOR_KEYBOARD_STEP_RATIO,
    _CURSOR_MINIMUM_SIZE,
    _CURSOR_PREFERRED_SIZE,
    _CURSOR_WIDGET_MARGINS,
    _CURSOR_WIDGET_SPACING,
    _cursor_band_rects,
    _cursor_color_rect,
    _cursor_menu_rect,
    _cursor_name_rect,
    _cursor_pair_footer_rect,
    _cursor_pair_member_rect,
    _cursor_pair_visibility_rect,
    _cursor_value_rect,
    _cursor_visibility_rect,
    _CursorListItemRecord,
)
from .models import CursorStyle, CursorType
from .qt_styles import paint_host_frame

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


class _CursorListView(QListView):
    delete_requested = Signal()
    cursor_pressed = Signal(QModelIndex, str, object)
    pair_group_pressed = Signal(QModelIndex, object)
    edit_requested = Signal(QModelIndex, str, str)
    nudge_requested = Signal(int, object)
    row_menu_requested = Signal(QModelIndex, QPoint)
    color_menu_requested = Signal(QModelIndex, QPoint)
    visibility_requested = Signal(QModelIndex)
    pair_visibility_requested = Signal(str)
    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Delete, Qt.Key.Key_Backspace}:
            self.delete_requested.emit()
            event.accept()
            return
        if event.key() in {
            Qt.Key.Key_Left,
            Qt.Key.Key_Right,
            Qt.Key.Key_Up,
            Qt.Key.Key_Down,
        }:
            self.nudge_requested.emit(event.key(), event.modifiers())
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            position = event.position().toPoint()
            cursor_key = self._cursor_key_at(index, position)
            record = index.data(_CURSOR_DISPLAY_ROLE)
            if (
                isinstance(record, _CursorListItemRecord)
                and record.pair_key is not None
                and cursor_key is None
            ):
                self.pair_group_pressed.emit(index, event.modifiers())
                event.accept()
                return
            if cursor_key is not None:
                self.cursor_pressed.emit(index, cursor_key, event.modifiers())
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        position = event.position().toPoint()
        if index.isValid():
            record = index.data(_CURSOR_DISPLAY_ROLE)
            if isinstance(record, _CursorListItemRecord) and record.pair_key is not None:
                footer_rect = _cursor_pair_footer_rect(self.visualRect(index), record)
                if _cursor_pair_visibility_rect(footer_rect).contains(position):
                    self.pair_visibility_requested.emit(record.pair_key)
                    event.accept()
                    return
            cursor_key = self._cursor_key_at(index, position)
            cursor_rect = self._cursor_rect_for_key(index, cursor_key)
            if cursor_rect is not None and _cursor_color_rect(cursor_rect).contains(position):
                self.color_menu_requested.emit(index, self.viewport().mapToGlobal(position))
                event.accept()
                return
            if cursor_rect is not None and _cursor_visibility_rect(cursor_rect).contains(position):
                self.visibility_requested.emit(index)
                event.accept()
                return
            if cursor_rect is not None and _cursor_menu_rect(cursor_rect).contains(position):
                self.row_menu_requested.emit(index, self.viewport().mapToGlobal(position))
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if not index.isValid():
            super().mouseDoubleClickEvent(event)
            return

        position = event.position().toPoint()
        cursor_key = self._cursor_key_at(index, position)
        cursor_rect = self._cursor_rect_for_key(index, cursor_key)
        if cursor_key is not None and cursor_rect is not None and _cursor_name_rect(cursor_rect).contains(position):
            self.edit_requested.emit(index, cursor_key, _CURSOR_EDIT_FIELD_NAME)
            event.accept()
            return
        if cursor_key is not None and cursor_rect is not None and _cursor_value_rect(cursor_rect).contains(position):
            self.edit_requested.emit(index, cursor_key, _CURSOR_EDIT_FIELD_VALUE)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def _cursor_key_at(self, index: QModelIndex, position: QPoint) -> str | None:
        record = index.data(_CURSOR_DISPLAY_ROLE)
        if not isinstance(record, _CursorListItemRecord):
            return None
        for cursor_record, cursor_rect in zip(
            record.cursor_records,
            _cursor_band_rects(self.visualRect(index), record),
        ):
            hit_rect = _cursor_pair_member_rect(cursor_rect) if record.pair_key is not None else cursor_rect
            if hit_rect.contains(position):
                return cursor_record.key
        return None

    def _cursor_rect_for_key(self, index: QModelIndex, cursor_key: str | None) -> QRect | None:
        record = index.data(_CURSOR_DISPLAY_ROLE)
        if not isinstance(record, _CursorListItemRecord) or cursor_key is None:
            return None
        for cursor_record, cursor_rect in zip(
            record.cursor_records,
            _cursor_band_rects(self.visualRect(index), record),
        ):
            if cursor_record.key == cursor_key:
                return _cursor_pair_member_rect(cursor_rect) if record.pair_key is not None else cursor_rect
        return None

class PyQtLabGraphCursorWidget(QWidget):
    """Compact Qt list widget for plot-owned cursor state."""

    selection_changed = Signal()

    def __init__(
        self,
        plot: "PyQtLabGraphWidget",
        *,
        parent: QWidget | None = None,
        show_frame: bool = True,
    ) -> None:
        super().__init__(parent)
        self.plot = plot
        self._show_frame = show_frame
        self.setObjectName("pyqtLabGraphCursorWidget")

        self.model = _CursorListModel(plot, self)
        self._settings_dialogs: list[_CursorSettingsDialog] = []
        self.list = _CursorListView(self)
        self.list.setObjectName("pyqtLabGraphCursorList")
        self.list.setModel(self.model)
        self.list.setItemDelegate(_CursorListDelegate(self.list))
        self.list.setSelectionMode(QListView.SelectionMode.ExtendedSelection)
        self.list.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        self.list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._show_context_menu)
        self.list.delete_requested.connect(self.delete_selected_cursors)
        self.list.cursor_pressed.connect(self._handle_cursor_pressed)
        self.list.pair_group_pressed.connect(self._handle_pair_group_pressed)
        self.list.edit_requested.connect(self._handle_edit_requested)
        self.list.nudge_requested.connect(self._handle_nudge_requested)
        self.list.row_menu_requested.connect(self._show_row_menu)
        self.list.color_menu_requested.connect(self._show_color_menu)
        self.list.visibility_requested.connect(self._toggle_cursor_visibility)
        self.list.pair_visibility_requested.connect(self._toggle_pair_visibility)
        self._configure_list_view()
        self.list.selectionModel().selectionChanged.connect(self._sync_selection_from_rows)
        self.model.cursor_name_edit_requested.connect(self.plot.set_cursor_name)
        self.model.cursor_value_edit_requested.connect(self.plot.set_cursor_value)
        self.model.pair_requested.connect(self.plot.add_cursor_pair)
        self.model.cursor_order_requested.connect(self.plot.set_cursor_order)

        self.add_x_action = QAction("X Cursor", self)
        self.add_y_action = QAction("Y Cursor", self)
        self.add_x_action.triggered.connect(lambda: self.plot.add_cursor("x"))
        self.add_y_action.triggered.connect(lambda: self.plot.add_cursor("y"))

        self.delete_action = QAction("Delete Selected", self)
        self.delete_action.triggered.connect(self.delete_selected_cursors)
        self.settings_action = QAction("Settings...", self)
        self.settings_action.triggered.connect(self.show_selected_cursor_settings)
        self._actions = _CursorActionController(
            owner=self,
            plot=self.plot,
            add_x_action=self.add_x_action,
            add_y_action=self.add_y_action,
            settings_action=self.settings_action,
            delete_action=self.delete_action,
            selected_cursor_keys=self._selected_cursor_keys,
            selected_row_count=self._selected_row_count,
            pairable_cursor_keys=self._pairable_selected_cursor_keys,
            copy_selected_rows=self.copy_selected_rows,
            pair_selected_cursors=self.pair_selected_cursors,
            set_cursor_color=self._set_cursor_color,
            choose_cursor_color=self._choose_cursor_color,
            color_swatch_icon=_color_swatch_icon,
        )

        self.title_label = QLabel("Cursors", self)
        self.title_label.setObjectName("pyqtLabGraphCursorTitle")
        self.add_x_button = self._create_add_button(
            "pyqtLabGraphCursorAddXButton",
            "+ X",
            "Add X cursor",
            self.add_x_action,
        )
        self.add_y_button = self._create_add_button(
            "pyqtLabGraphCursorAddYButton",
            "+ Y",
            "Add Y cursor",
            self.add_y_action,
        )

        header = QWidget(self)
        header.setObjectName("pyqtLabGraphCursorHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(*_CURSOR_HEADER_MARGINS)
        header_layout.setSpacing(_CURSOR_HEADER_SPACING)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch(1)
        header_layout.addWidget(self.add_x_button)
        header_layout.addWidget(self.add_y_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(*_CURSOR_WIDGET_MARGINS)
        layout.setSpacing(_CURSOR_WIDGET_SPACING)
        layout.addWidget(header)
        layout.addWidget(self.list)

        self.plot.cursor_added.connect(self.refresh)
        self.plot.cursor_removed.connect(self.refresh)
        self.plot.cursor_moved.connect(lambda key, _value: self.refresh_cursor(key))
        self.plot.cursor_changed.connect(self.refresh_cursor)
        self.plot.cursor_pair_added.connect(lambda _key: self.refresh_preserving_selection())
        self.plot.cursor_pair_removed.connect(lambda _key: self.refresh_preserving_selection())
        self.plot.cursor_pair_changed.connect(self.refresh_pair)
        self.plot.cursor_order_changed.connect(self.refresh_preserving_selection)
        self.plot.cursor_selection_changed.connect(self._sync_selection_from_plot)
        self.plot.presentation_changed.connect(self.refresh_all_display)
        self.plot.state_reset.connect(self.refresh_preserving_selection)
        self.refresh()
        self._sync_selection_from_plot()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._show_frame:
            paint_host_frame(self)

    def refresh(self, *_args: object) -> None:
        self.model.refresh()
        self._sync_selection_from_plot()

    def refresh_preserving_selection(self, *_args: object) -> None:
        self.model.refresh()
        self._sync_selection_from_plot()

    def _sync_selection_from_plot(self) -> None:
        selected = self.plot.selected_cursor_keys()
        selected_set = set(selected)
        selection_model = self.list.selectionModel()
        selection_model.blockSignals(True)
        try:
            selection_model.clearSelection()
            for row in range(self.model.rowCount()):
                block_keys = self.model.block_cursor_keys(row)
                block_selected = [key for key in block_keys if key in selected_set]
                if block_selected:
                    active_key = self.model.active_cursor_key(row)
                    if active_key not in block_selected:
                        self.model.set_active_cursor(row, block_selected[0])
                    selection_model.select(
                        self.model.index(row, 0),
                        QItemSelectionModel.SelectionFlag.Select,
                    )
        finally:
            selection_model.blockSignals(False)
        self.list.viewport().update()

    def refresh_cursor(self, cursor_key: str) -> None:
        self.model.refresh_cursor(cursor_key)
        self.list.doItemsLayout()

    def refresh_pair(self, pair_key: str) -> None:
        self.model.refresh_pair(pair_key)
        self.list.doItemsLayout()

    def refresh_all_display(self) -> None:
        for state in self.plot.cursor_states():
            self.model.refresh_cursor(state.key)
        self.list.doItemsLayout()

    def sizeHint(self) -> QSize:
        return QSize(_CURSOR_PREFERRED_SIZE)

    def minimumSizeHint(self) -> QSize:
        return QSize(_CURSOR_MINIMUM_SIZE)

    def select_cursor(self, cursor_key: str) -> bool:
        return self.activate_cursor_from_plot(cursor_key, preserve_existing_selection=False)

    def activate_cursor_from_plot(self, cursor_key: str, *, preserve_existing_selection: bool = True) -> bool:
        row = self.model.row_for_cursor(cursor_key)
        if row is None:
            return False
        index = self.model.index(row, 0)
        self.model.set_active_cursor(row, cursor_key)
        selection_model = self.list.selectionModel()
        if preserve_existing_selection and cursor_key in self.plot.selected_cursor_keys():
            selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
        else:
            self._request_selection([cursor_key])
        selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
        self.list.scrollTo(index)
        self.list.setFocus(Qt.FocusReason.MouseFocusReason)
        self.list.viewport().setFocus(Qt.FocusReason.MouseFocusReason)
        self.list.viewport().update(self.list.visualRect(index))
        return True

    def nudge_selected_cursor_for_key(self, event: QKeyEvent) -> bool:
        return self._nudge_selected_cursor(event.key(), event.modifiers())

    def _nudge_selected_cursor(
        self,
        key: int,
        modifiers: Qt.KeyboardModifier,
    ) -> bool:
        cursor_key = self._active_selected_cursor_key()
        if cursor_key is None:
            return False

        state = self.plot.cursor_state(cursor_key)
        direction = _keyboard_nudge_direction(state.cursor_type, key)
        if direction is None:
            return False

        self.plot.nudge_cursor_group(
            cursor_key,
            selected_cursor_keys=self._selected_cursor_keys(),
            direction=direction,
            step_ratio=_keyboard_step_ratio(modifiers),
        )
        return True

    def copy_selected_cells(self) -> str:
        return self.copy_selected_rows()

    def copy_selected_rows(self) -> str:
        lines = []
        selected_keys = set(self.plot.selected_cursor_keys())
        for row in self._selected_rows():
            item_record = self.model.display_item(row)
            for record in item_record.cursor_records:
                if record.key not in selected_keys:
                    continue
                values = [
                    record.type_label,
                    record.name,
                    record.value_text,
                    record.target_curve_text,
                    record.target_value_text,
                ]
                lines.append("\t".join(values))

        text = "\n".join(lines)
        if text:
            QApplication.clipboard().setText(text)
        return text

    def delete_selected_cursors(self) -> None:
        cursor_keys = self._selected_cursor_keys()
        if not cursor_keys or not self._confirm_delete_selected(len(cursor_keys)):
            return
        for cursor_key in cursor_keys:
            self.plot.remove_cursor(cursor_key)

    def edit_cursor_name(self, index: QModelIndex, cursor_key: str) -> None:
        if index.isValid():
            self.model.set_active_cursor(index.row(), cursor_key)
            self.model.edit_cursor_key = cursor_key
            self.model.edit_field = _CURSOR_EDIT_FIELD_NAME
            self.list.edit(index)

    def edit_cursor_value(self, index: QModelIndex, cursor_key: str) -> None:
        if index.isValid():
            self.model.set_active_cursor(index.row(), cursor_key)
            self.model.edit_cursor_key = cursor_key
            self.model.edit_field = _CURSOR_EDIT_FIELD_VALUE
            self.list.edit(index)

    def show_selected_cursor_settings(self) -> None:
        cursor_keys = self._selected_cursor_keys()
        if len(cursor_keys) != 1:
            return

        cursor_key = cursor_keys[0]
        for dialog in self._settings_dialogs:
            if dialog.cursor_key == cursor_key:
                dialog.raise_()
                dialog.activateWindow()
                return

        dialog = _CursorSettingsDialog(self.plot, cursor_key, self)
        self._settings_dialogs.append(dialog)
        dialog.finished.connect(lambda _result, dialog=dialog: self._forget_settings_dialog(dialog))
        dialog.show()

    def pair_selected_cursors(self) -> None:
        cursor_keys = self._pairable_selected_cursor_keys()
        if cursor_keys is not None:
            self.plot.add_cursor_pair(*cursor_keys)

    def _create_add_button(
        self,
        object_name: str,
        text: str,
        tooltip: str,
        action: QAction,
    ) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName(object_name)
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        button.setMinimumSize(28, 28)
        button.clicked.connect(action.trigger)
        return button

    def _toggle_cursor_visibility(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        cursor_key = self.model.active_cursor_key(index.row())
        if cursor_key is None:
            return
        state = self.plot.cursor_state(cursor_key)
        self.plot.set_cursor_visible(cursor_key, not state.visible)

    def _toggle_pair_visibility(self, pair_key: str) -> None:
        state = self.plot.cursor_pair_state(pair_key)
        self.plot.set_cursor_pair_measurement_visible(pair_key, not state.measurement_visible)

    def _configure_list_view(self) -> None:
        self.list.setAlternatingRowColors(False)
        self.list.setUniformItemSizes(False)
        self.list.setSpacing(0)
        self.list.setWordWrap(False)
        self.list.setDragEnabled(True)
        self.list.setAcceptDrops(True)
        self.list.setDragDropMode(QListView.DragDropMode.DragDrop)
        self.list.setDropIndicatorShown(True)
        self.list.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.list.setMouseTracking(True)

    def _selected_cursor_keys(self) -> list[str]:
        selected_keys = set(self.plot.selected_cursor_keys())
        return [
            cursor_key
            for cursor_key in self.model.cursor_keys()
            if cursor_key in selected_keys
        ]

    def _single_selected_cursor_key(self) -> str | None:
        cursor_keys = self._selected_cursor_keys()
        return cursor_keys[0] if len(cursor_keys) == 1 else None

    def _pairable_selected_cursor_keys(self) -> tuple[str, str] | None:
        cursor_keys = self._selected_cursor_keys()
        if len(cursor_keys) != 2:
            return None
        first_key, second_key = cursor_keys
        if self.plot.cursor_state(first_key).cursor_type is not self.plot.cursor_state(second_key).cursor_type:
            return None
        if self.plot.cursor_pair_for_cursor(first_key) is not None:
            return None
        if self.plot.cursor_pair_for_cursor(second_key) is not None:
            return None
        return first_key, second_key

    def _active_selected_cursor_key(self) -> str | None:
        current_index = self.list.currentIndex()
        if current_index.isValid():
            current_key = self.model.active_cursor_key(current_index.row())
            if current_key in self._selected_cursor_keys():
                return current_key
        return self._single_selected_cursor_key()

    def _select_cursor_keys(self, cursor_keys: list[str]) -> None:
        self._request_selection(cursor_keys)

    def _set_active_cursor_for_index(self, index: QModelIndex, cursor_key: str) -> None:
        if not index.isValid():
            return
        self.model.set_active_cursor(index.row(), cursor_key)
        self.list.viewport().update(self.list.visualRect(index))

    def _select_cursor_after_press(
        self,
        index: QModelIndex,
        cursor_key: str,
        modifiers: Qt.KeyboardModifier,
        *,
        was_selected: bool,
    ) -> None:
        selected_keys = set(self.plot.selected_cursor_keys())
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if was_selected:
                selected_keys.discard(cursor_key)
            else:
                selected_keys.add(cursor_key)
        else:
            selected_keys = {cursor_key}
        self._request_selection_in_model_order(selected_keys, current_index=index)

    def _select_group_for_index(
        self,
        index: QModelIndex,
        modifiers: Qt.KeyboardModifier,
    ) -> None:
        block_keys = self.model.block_cursor_keys(index.row())
        group_keys = set(block_keys)
        selected_keys = set(self.plot.selected_cursor_keys())
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if group_keys.issubset(selected_keys):
                selected_keys.difference_update(group_keys)
            else:
                selected_keys.update(group_keys)
        else:
            selected_keys = group_keys
        if block_keys:
            self.model.set_active_cursor(index.row(), block_keys[0])
        self._request_selection_in_model_order(selected_keys, current_index=index)

    def _request_selection_in_model_order(
        self,
        selected_keys: set[str],
        *,
        current_index: QModelIndex,
    ) -> None:
        ordered = [key for key in self.model.cursor_keys() if key in selected_keys]
        self._request_selection(ordered)
        self.list.selectionModel().setCurrentIndex(
            current_index,
            QItemSelectionModel.SelectionFlag.NoUpdate,
        )

    def _sync_selection_from_rows(self, selected, deselected) -> None:
        selected_keys = set(self.plot.selected_cursor_keys())
        for index in deselected.indexes():
            selected_keys.difference_update(self.model.block_cursor_keys(index.row()))
        for index in selected.indexes():
            cursor_key = self.model.active_cursor_key(index.row())
            if cursor_key is not None:
                selected_keys.add(cursor_key)
        self._request_selection_in_model_order(
            selected_keys,
            current_index=self.list.currentIndex(),
        )

    def _request_selection(self, cursor_keys: list[str]) -> None:
        before = self.plot.selected_cursor_keys()
        self.plot.set_selected_cursor_keys(cursor_keys)
        if before != self.plot.selected_cursor_keys():
            self.selection_changed.emit()

    def _handle_cursor_pressed(
        self,
        index: QModelIndex,
        cursor_key: str,
        modifiers: Qt.KeyboardModifier,
    ) -> None:
        was_selected = cursor_key in self.plot.selected_cursor_keys()
        self._set_active_cursor_for_index(index, cursor_key)
        self._select_cursor_after_press(
            index,
            cursor_key,
            modifiers,
            was_selected=was_selected,
        )

    def _handle_pair_group_pressed(
        self,
        index: QModelIndex,
        modifiers: Qt.KeyboardModifier,
    ) -> None:
        self._select_group_for_index(index, modifiers)

    def _handle_edit_requested(
        self,
        index: QModelIndex,
        cursor_key: str,
        edit_field: str,
    ) -> None:
        if edit_field == _CURSOR_EDIT_FIELD_NAME:
            self.edit_cursor_name(index, cursor_key)
        else:
            self.edit_cursor_value(index, cursor_key)

    def _handle_nudge_requested(
        self,
        key: int,
        modifiers: Qt.KeyboardModifier,
    ) -> None:
        self._nudge_selected_cursor(key, modifiers)

    def _forget_settings_dialog(self, dialog: "_CursorSettingsDialog") -> None:
        if dialog in self._settings_dialogs:
            self._settings_dialogs.remove(dialog)

    def _show_context_menu(self, position: QPoint) -> None:
        index = self._sync_context_selection(position)
        pair_key = self._pair_key_at_footer(index, position)
        self._show_cursor_menu(
            index,
            self.list.viewport().mapToGlobal(position),
            pair_key=pair_key,
        )

    def _show_row_menu(self, index: QModelIndex, global_position: QPoint) -> None:
        self._select_index_if_needed(index)
        self._show_cursor_menu(index, global_position)

    def _show_color_menu(self, index: QModelIndex, global_position: QPoint) -> None:
        self._select_index_if_needed(index)
        cursor_key = self._single_selected_cursor_key()
        if cursor_key is None:
            return

        menu = self._actions.create_color_menu(cursor_key)
        menu.exec(global_position)

    def _show_cursor_menu(
        self,
        index: QModelIndex,
        global_position: QPoint,
        *,
        pair_key: str | None = None,
    ) -> None:
        menu = self._create_cursor_menu(pair_key=pair_key)
        try:
            menu.exec(global_position)
        finally:
            self._actions.restore_shared_actions()

    def _create_cursor_menu(self, *, pair_key: str | None = None) -> QMenu:
        return self._actions.create_menu(pair_key=pair_key)

    def _pair_key_at_footer(self, index: QModelIndex, position: QPoint) -> str | None:
        if not index.isValid():
            return None
        record = index.data(_CURSOR_DISPLAY_ROLE)
        if not isinstance(record, _CursorListItemRecord) or record.pair_key is None:
            return None
        return record.pair_key if _cursor_pair_footer_rect(self.list.visualRect(index), record).contains(position) else None

    def _set_cursor_color(self, cursor_key: str, color_name: str) -> None:
        state = self.plot.cursor_state(cursor_key)
        self.plot.set_cursor_style(
            cursor_key,
            CursorStyle(
                line_color=color_name,
                line_width=state.style.line_width,
                line_style=state.style.line_style,
            ),
        )

    def _choose_cursor_color(self, cursor_key: str) -> None:
        state = self.plot.cursor_state(cursor_key)
        selected = QColorDialog.getColor(QColor(state.style.line_color), self, f"{state.name} line color")
        if selected.isValid():
            self._set_cursor_color(cursor_key, selected.name())

    def _confirm_delete_selected(self, cursor_count: int) -> bool:
        label = "cursor" if cursor_count == 1 else "cursors"
        result = QMessageBox.question(
            self,
            "Delete Cursor",
            f"Delete {cursor_count} selected {label}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def _sync_context_selection(self, position: QPoint) -> QModelIndex:
        index = self.list.indexAt(position)
        if not index.isValid():
            return QModelIndex()
        self._select_index_if_needed(index)
        return index

    def _select_index_if_needed(self, index: QModelIndex) -> None:
        if not index.isValid():
            return
        selection_model = self.list.selectionModel()
        if selection_model.isSelected(index):
            return
        self.list.clearSelection()
        selection_model.select(index, QItemSelectionModel.SelectionFlag.Select)
        selection_model.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
        self.selection_changed.emit()

    def _selected_row_count(self) -> int:
        return len(self._selected_rows())

    def _selected_rows(self) -> list[int]:
        return sorted(
            {
                index.row()
                for index in self.list.selectionModel().selectedIndexes()
                if index.isValid()
            }
        )

    def selected_cursor_keys(self) -> list[str]:
        return self._selected_cursor_keys()


def _keyboard_nudge_direction(cursor_type: CursorType, key: int) -> int | None:
    if cursor_type is CursorType.X:
        if key == Qt.Key.Key_Left:
            return -1
        if key == Qt.Key.Key_Right:
            return 1
    if cursor_type is CursorType.Y:
        if key == Qt.Key.Key_Down:
            return -1
        if key == Qt.Key.Key_Up:
            return 1
    return None


def _keyboard_step_ratio(modifiers: Qt.KeyboardModifier) -> float:
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        return _CURSOR_KEYBOARD_COARSE_STEP_RATIO
    if modifiers & Qt.KeyboardModifier.AltModifier:
        return _CURSOR_KEYBOARD_FINE_STEP_RATIO
    return _CURSOR_KEYBOARD_STEP_RATIO
