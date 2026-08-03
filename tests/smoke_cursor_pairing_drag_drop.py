from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cursor_smoke_helpers import graph, select_rows
from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import PyQtLabGraphCursorWidget
from pyqtlabgraph.cursor_ui import _CURSOR_MIME_TYPE


def _action(menu, text: str):
    return next(action for action in menu.actions() if action.text() == text)


def main() -> None:
    QApplication.instance() or QApplication([])
    plot = graph("cursor-pairing-context")
    first = plot.add_cursor("x", key="first", value=1.5)
    second = plot.add_cursor("x", key="second", value=3.0)
    y_cursor = plot.add_cursor("y", key="y_cursor", value=0.0)
    widget = PyQtLabGraphCursorWidget(plot)

    select_rows(widget, 0, 1)
    pair_action = _action(widget._create_cursor_menu(), "Pair Selected Cursors")
    assert pair_action.isEnabled()
    pair_action.trigger()
    pair = plot.cursor_pair_states()[0]
    assert (pair.first_cursor_key, pair.second_cursor_key) == (first, second)
    assert widget.model.rowCount() == 2
    display_item = widget.model.display_item(0)
    assert [record.key for record in display_item.cursor_records] == [first, second]
    assert display_item.pair_detail_text == "Δx = 1.5"

    pair_menu = widget._create_cursor_menu(pair_key=pair.key)
    assert [action.text() for action in pair_menu.actions() if not action.isSeparator()] == [
        "Visible", "Copy Measurement", "Ungroup Pair",
    ]
    _action(pair_menu, "Visible").trigger()
    assert plot.cursor_pair_state(pair.key).measurement_visible is False
    assert plot.cursor_state(first).visible is True
    _action(widget._create_cursor_menu(pair_key=pair.key), "Ungroup Pair").trigger()
    assert plot.cursor_pair_states() == ()

    select_rows(widget, 0, 2)
    mixed_action = _action(widget._create_cursor_menu(), "Pair Selected Cursors")
    assert not mixed_action.isEnabled()
    assert y_cursor in {state.key for state in plot.cursor_states()}

    pair_mime = widget.model.mimeData([widget.model.index(0, 0)])
    assert widget.model.dropMimeData(
        pair_mime, Qt.DropAction.MoveAction, -1, 0, widget.model.index(1, 0)
    )
    assert len(plot.cursor_pair_states()) == 1

    reorder = graph("cursor-reorder-dnd")
    keys = [
        reorder.add_cursor("x", key="a"),
        reorder.add_cursor("y", key="b"),
        reorder.add_cursor("x", key="c"),
        reorder.add_cursor("y", key="d"),
    ]
    reorder_widget = PyQtLabGraphCursorWidget(reorder)
    move_c = reorder_widget.model.mimeData([reorder_widget.model.index(2, 0)])
    assert reorder_widget.model.dropMimeData(
        move_c, Qt.DropAction.MoveAction, 0, 0, reorder_widget.model.index(-1, -1)
    )
    assert [state.key for state in reorder.cursor_states()] == [keys[2], keys[0], keys[1], keys[3]]

    cross_axis = reorder_widget.model.mimeData([reorder_widget.model.index(0, 0)])
    assert not reorder_widget.model.canDropMimeData(
        cross_axis, Qt.DropAction.MoveAction, -1, 0, reorder_widget.model.index(2, 0)
    )
    malformed = QMimeData()
    malformed.setData(_CURSOR_MIME_TYPE, b"not-json")
    assert not reorder_widget.model.canDropMimeData(
        malformed, Qt.DropAction.MoveAction, 0, 0, reorder_widget.model.index(-1, -1)
    )
    foreign = graph("cursor-foreign-dnd")
    foreign.add_cursor("x", key="foreign")
    foreign_widget = PyQtLabGraphCursorWidget(foreign)
    foreign_mime = foreign_widget.model.mimeData([foreign_widget.model.index(0, 0)])
    assert not reorder_widget.model.canDropMimeData(
        foreign_mime, Qt.DropAction.MoveAction, 0, 0, reorder_widget.model.index(-1, -1)
    )
    print("cursor pairing and drag-and-drop smoke ok")


if __name__ == "__main__":
    main()
