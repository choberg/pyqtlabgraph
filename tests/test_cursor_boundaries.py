from __future__ import annotations

import inspect
import os

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QItemSelectionModel, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import PyQtLabGraphCursorWidget, PyQtLabGraphWidget
from pyqtlabgraph.cursor_actions import _CursorActionController
from pyqtlabgraph.cursor_controller import CursorController
from pyqtlabgraph.cursor_delegate import _CursorListDelegate
from pyqtlabgraph.cursor_list_model import _CursorListModel
from pyqtlabgraph.cursor_presenter import CursorPlotPresenter
from pyqtlabgraph.cursor_ui import (
    _CURSOR_DISPLAY_ROLE,
    _CursorDisplayRecord,
    _CursorListItemRecord,
)
from pyqtlabgraph.cursor_widget import _CursorListView


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _dispose(qapp: QApplication, *widgets: object) -> None:
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def test_cursor_core_receives_explicit_dependencies(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="cursor-explicit-dependencies")
    controller = plot._cursor_controller
    presenter = controller.presenter

    assert isinstance(controller, CursorController)
    assert isinstance(presenter, CursorPlotPresenter)
    assert not hasattr(controller, "plot")
    assert not hasattr(presenter, "plot")
    assert "PyQtLabGraphWidget" not in inspect.getsource(CursorController)
    assert "PyQtLabGraphWidget" not in inspect.getsource(CursorPlotPresenter)
    assert "self.plot" not in inspect.getsource(CursorPlotPresenter)
    assert "._curve_manager" not in inspect.getsource(CursorController)
    _dispose(qapp, plot)


def test_cursor_ui_types_are_neutral_and_import_direction_is_one_way() -> None:
    record = _CursorDisplayRecord(
        key="cursor",
        name="Cursor",
        type_label="X",
        value_text="1",
        edit_value_text="1",
        target_curve_text="",
        target_value_text="",
        color=QColor("#123456"),
        visible=True,
        show_label=False,
        snap_enabled=False,
        selected=False,
    )
    item = _CursorListItemRecord(item_key=("cursor",), cursor_records=(record,))

    assert _CURSOR_DISPLAY_ROLE > int(Qt.ItemDataRole.UserRole)
    assert item.cursor_records == (record,)
    assert "cursor_delegate" not in inspect.getsource(inspect.getmodule(_CursorListModel))
    assert "cursor_list_model" not in inspect.getsource(inspect.getmodule(_CursorListDelegate))


def test_model_and_view_emit_intents_instead_of_calling_plot_commands() -> None:
    model_source = inspect.getsource(_CursorListModel)
    view_source = inspect.getsource(_CursorListView)

    assert "self.plot.set_" not in model_source
    assert "self.plot.add_" not in model_source
    assert ".parent()" not in view_source
    for signal_name in (
        "cursor_pressed",
        "pair_group_pressed",
        "edit_requested",
        "nudge_requested",
        "delete_requested",
        "row_menu_requested",
        "color_menu_requested",
        "visibility_requested",
        "pair_visibility_requested",
    ):
        assert hasattr(_CursorListView, signal_name)
    for signal_name in (
        "cursor_name_edit_requested",
        "cursor_value_edit_requested",
        "pair_requested",
        "cursor_order_requested",
    ):
        assert hasattr(_CursorListModel, signal_name)


def test_plot_selection_is_the_only_panel_selection_authority(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="cursor-selection-authority")
    first = plot.add_cursor("x", key="first")
    second = plot.add_cursor("x", key="second")
    first_panel = PyQtLabGraphCursorWidget(plot)
    second_panel = PyQtLabGraphCursorWidget(plot)

    assert not hasattr(first_panel, "_selected_cursor_keys_state")
    plot.set_selected_cursor_keys([first, second])
    qapp.processEvents()
    assert first_panel.selected_cursor_keys() == [first, second]
    assert second_panel.selected_cursor_keys() == [first, second]

    plot.set_selected_cursor_keys([])
    qapp.processEvents()
    assert first_panel.list.selectionModel().selectedIndexes() == []
    assert second_panel.list.selectionModel().selectedIndexes() == []

    index = first_panel.model.index(0, 0)
    first_panel.list.selectionModel().select(
        index,
        QItemSelectionModel.SelectionFlag.Select,
    )
    qapp.processEvents()
    assert plot.selected_cursor_keys() == [first]
    assert second_panel.selected_cursor_keys() == [first]
    _dispose(qapp, first_panel, second_panel, plot)


def test_context_actions_are_extracted(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="cursor-actions")
    plot.add_cursor("x", key="cursor")
    panel = PyQtLabGraphCursorWidget(plot)

    assert isinstance(panel._actions, _CursorActionController)
    assert "_create_pair_result_menu" not in inspect.getsource(PyQtLabGraphCursorWidget)
    _dispose(qapp, panel, plot)
