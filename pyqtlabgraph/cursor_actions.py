from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from PySide6.QtGui import QAction, QColor, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from .cursor_ui import _CURSOR_QUICK_COLORS
from .models import CursorType

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


class _CursorActionController:
    """Builds cursor context actions from plot state and panel intents."""

    def __init__(
        self,
        *,
        owner: QWidget,
        plot: PyQtLabGraphWidget,
        add_x_action: QAction,
        add_y_action: QAction,
        settings_action: QAction,
        delete_action: QAction,
        selected_cursor_keys: Callable[[], list[str]],
        selected_row_count: Callable[[], int],
        pairable_cursor_keys: Callable[[], tuple[str, str] | None],
        copy_selected_rows: Callable[[], str],
        pair_selected_cursors: Callable[[], None],
        set_cursor_color: Callable[[str, str], None],
        choose_cursor_color: Callable[[str], None],
        color_swatch_icon: Callable[[QColor], QIcon],
    ) -> None:
        self._owner = owner
        self._plot = plot
        self._add_x_action = add_x_action
        self._add_y_action = add_y_action
        self._settings_action = settings_action
        self._delete_action = delete_action
        self._selected_cursor_keys = selected_cursor_keys
        self._selected_row_count = selected_row_count
        self._pairable_cursor_keys = pairable_cursor_keys
        self._copy_selected_rows = copy_selected_rows
        self._pair_selected_cursors = pair_selected_cursors
        self._set_cursor_color = set_cursor_color
        self._choose_cursor_color = choose_cursor_color
        self._color_swatch_icon = color_swatch_icon

    def create_color_menu(self, cursor_key: str) -> QMenu:
        menu = QMenu(self._owner)
        for label, color_name in _CURSOR_QUICK_COLORS:
            action = QAction("", menu)
            action.setIcon(self._color_swatch_icon(QColor(color_name)))
            action.setToolTip(label)
            action.setData(color_name)
            action.triggered.connect(
                lambda _checked=False, color=color_name: self._set_cursor_color(
                    cursor_key,
                    color,
                )
            )
            menu.addAction(action)
        menu.addSeparator()
        custom_action = menu.addAction("Custom...")
        custom_action.triggered.connect(
            lambda _checked=False: self._choose_cursor_color(cursor_key)
        )
        return menu

    def create_menu(self, *, pair_key: str | None = None) -> QMenu:
        if pair_key is not None:
            return self._create_pair_result_menu(pair_key)

        selected_row_count = self._selected_row_count()
        menu = QMenu(self._owner)
        new_menu = menu.addMenu("New")
        new_menu.addAction(self._add_x_action)
        new_menu.addAction(self._add_y_action)
        menu.addSeparator()
        copy_action = menu.addAction(_copy_action_text(selected_row_count))
        copy_action.setEnabled(selected_row_count > 0)
        copy_action.triggered.connect(self._copy_selected_rows)

        if selected_row_count == 2:
            pair_action = menu.addAction("Pair Selected Cursors")
            pair_action.setEnabled(self._pairable_cursor_keys() is not None)
            pair_action.triggered.connect(self._pair_selected_cursors)

        selected_keys = self._selected_cursor_keys()
        cursor_key = selected_keys[0] if len(selected_keys) == 1 else None
        if cursor_key is not None:
            self._add_cursor_actions(menu, cursor_key)
            menu.addAction(self._settings_action)
        else:
            menu.addAction(self._settings_action)
            self._settings_action.setEnabled(False)

        menu.addAction(self._delete_action)
        self._delete_action.setEnabled(selected_row_count > 0)
        return menu

    def restore_shared_actions(self) -> None:
        self._settings_action.setEnabled(True)
        self._delete_action.setEnabled(True)

    def _add_cursor_actions(self, menu: QMenu, cursor_key: str) -> None:
        state = self._plot.cursor_state(cursor_key)
        visible_action = menu.addAction("Visible")
        visible_action.setCheckable(True)
        visible_action.setChecked(state.visible)
        visible_action.triggered.connect(
            lambda checked: self._plot.set_cursor_visible(cursor_key, checked)
        )

        label_action = menu.addAction("Show Label")
        label_action.setCheckable(True)
        label_action.setChecked(state.label_visible)
        label_action.triggered.connect(
            lambda checked: self._plot.set_cursor_label_visible(cursor_key, checked)
        )

        snap_menu = menu.addMenu("Snap to Curve")
        curve_choices = self._plot.curve_choices()
        snap_menu.setEnabled(state.cursor_type is CursorType.X and bool(curve_choices))
        off_action = snap_menu.addAction("Off")
        off_action.setCheckable(True)
        off_action.setChecked(state.snap_target_curve_key is None)
        off_action.triggered.connect(
            lambda _checked=False: self._plot.set_cursor_snap_target(cursor_key, None)
        )
        for curve_key, curve_label in curve_choices:
            target_action = snap_menu.addAction(curve_label)
            target_action.setCheckable(True)
            target_action.setChecked(state.snap_target_curve_key == curve_key)
            target_action.triggered.connect(
                lambda _checked=False, target=curve_key: self._plot.set_cursor_snap_target(
                    cursor_key,
                    target,
                )
            )

        pair_state = self._plot.cursor_pair_for_cursor(cursor_key)
        if pair_state is None:
            return
        menu.addSeparator()
        distance_action = menu.addAction("Show Distance Annotation")
        distance_action.setCheckable(True)
        distance_action.setChecked(pair_state.measurement_visible)
        distance_action.triggered.connect(
            lambda checked: self._plot.set_cursor_pair_measurement_visible(
                pair_state.key,
                checked,
            )
        )
        ungroup_action = menu.addAction("Ungroup Pair")
        ungroup_action.triggered.connect(
            lambda _checked=False: self._plot.remove_cursor_pair(pair_state.key)
        )

    def _create_pair_result_menu(self, pair_key: str) -> QMenu:
        pair_state = self._plot.cursor_pair_state(pair_key)
        menu = QMenu(self._owner)
        visible_action = menu.addAction("Visible")
        visible_action.setCheckable(True)
        visible_action.setChecked(pair_state.measurement_visible)
        visible_action.triggered.connect(
            lambda checked: self._plot.set_cursor_pair_measurement_visible(
                pair_key,
                checked,
            )
        )
        copy_action = menu.addAction("Copy Measurement")
        copy_action.triggered.connect(
            lambda _checked=False: QApplication.clipboard().setText(
                self._plot.cursor_pair_measurement_text(pair_key)
            )
        )
        menu.addSeparator()
        ungroup_action = menu.addAction("Ungroup Pair")
        ungroup_action.triggered.connect(
            lambda _checked=False: self._plot.remove_cursor_pair(pair_key)
        )
        return menu


def _copy_action_text(selected_row_count: int) -> str:
    if selected_row_count == 1:
        return "Copy Selected Row"
    if selected_row_count > 1:
        return f"Copy {selected_row_count} Selected Rows"
    return "Copy Selected Rows"
