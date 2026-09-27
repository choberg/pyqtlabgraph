from __future__ import annotations

from cursor_helpers import graph, select_rows
from PySide6.QtCore import QMimeData, Qt
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import PyQtLabGraphCursorWidget
from pyqtlabgraph.cursor_ui import _CURSOR_MIME_TYPE


def _action(menu, text: str):
    return next(action for action in menu.actions() if action.text() == text)


def test_cursor_pairing_drag_drop() -> None:
    QApplication.instance() or QApplication([])
    plot = graph("cursor-pairing-context")
    first = plot.cursors.add("x", key="first", value=1.5)
    second = plot.cursors.add("x", key="second", value=3.0)
    y_cursor = plot.cursors.add("y", key="y_cursor", value=0.0)
    widget = PyQtLabGraphCursorWidget(plot)

    select_rows(widget, 0, 1)
    pair_action = _action(widget._create_cursor_menu(), "Pair Selected Cursors")
    assert pair_action.isEnabled()
    pair_action.trigger()
    pair = plot.cursors.pair_states()[0]
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
    assert plot.cursors.pair_state(pair.key).measurement_visible is False
    assert plot.cursors.state(first).visible is True
    _action(widget._create_cursor_menu(pair_key=pair.key), "Ungroup Pair").trigger()
    assert plot.cursors.pair_states() == ()

    select_rows(widget, 0, 2)
    mixed_action = _action(widget._create_cursor_menu(), "Pair Selected Cursors")
    assert not mixed_action.isEnabled()
    assert y_cursor in {state.key for state in plot.cursors.states()}

    pair_mime = widget.model.mimeData([widget.model.index(0, 0)])
    assert widget.model.dropMimeData(
        pair_mime, Qt.DropAction.MoveAction, -1, 0, widget.model.index(1, 0)
    )
    assert len(plot.cursors.pair_states()) == 1

    reorder = graph("cursor-reorder-dnd")
    keys = [
        reorder.cursors.add("x", key="a"),
        reorder.cursors.add("y", key="b"),
        reorder.cursors.add("x", key="c"),
        reorder.cursors.add("y", key="d"),
    ]
    reorder_widget = PyQtLabGraphCursorWidget(reorder)
    move_c = reorder_widget.model.mimeData([reorder_widget.model.index(2, 0)])
    assert reorder_widget.model.dropMimeData(
        move_c, Qt.DropAction.MoveAction, 0, 0, reorder_widget.model.index(-1, -1)
    )
    assert [state.key for state in reorder.cursors.states()] == [keys[2], keys[0], keys[1], keys[3]]

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
    foreign.cursors.add("x", key="foreign")
    foreign_widget = PyQtLabGraphCursorWidget(foreign)
    foreign_mime = foreign_widget.model.mimeData([foreign_widget.model.index(0, 0)])
    assert not reorder_widget.model.canDropMimeData(
        foreign_mime, Qt.DropAction.MoveAction, 0, 0, reorder_widget.model.index(-1, -1)
    )


def _drag_row_onto_row(widget, source_row: int, target_row: int) -> None:  # type: ignore[no-untyped-def]
    """Drive a real mouse drag in the list and deliver the drop onto a row."""
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
    from PySide6.QtTest import QTest

    view = widget.list
    dragged: list[object] = []
    view.startDrag = lambda _actions: dragged.append(  # type: ignore[method-assign]
        widget.model.mimeData(view.selectedIndexes())
    )
    source = view.visualRect(widget.model.index(source_row, 0))
    target = view.visualRect(widget.model.index(target_row, 0))
    start = QPoint(source.left() + 60, source.center().y())
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    QTest.mouseMove(view.viewport(), QPoint(start.x(), target.center().y()))
    assert dragged, "A mouse drag on a cursor row must start a drag."

    drop_point = QPointF(start.x(), target.center().y())
    viewport = view.viewport()
    for event_type in (QDragEnterEvent, QDragMoveEvent):
        event = event_type(
            drop_point.toPoint(),
            Qt.DropAction.MoveAction,
            dragged[0],
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        QApplication.sendEvent(viewport, event)
    drop = QDropEvent(
        drop_point,
        Qt.DropAction.MoveAction,
        dragged[0],
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(viewport, drop)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)


def test_mouse_drag_onto_cursor_row_creates_pair(qapp: QApplication) -> None:
    plot = graph("cursor-mouse-drag-pair")
    widget = PyQtLabGraphCursorWidget(plot)
    widget.resize(420, 400)
    widget.show()
    qapp.processEvents()
    first = plot.cursors.add("x", key="first", value=0.2)
    second = plot.cursors.add("x", key="second", value=0.6)
    qapp.processEvents()

    _drag_row_onto_row(widget, 0, 1)

    pair = plot.cursors.pair_for_cursor(first)
    assert pair is not None
    assert {pair.first_cursor_key, pair.second_cursor_key} == {first, second}
    widget.close()


def test_mouse_drag_carries_only_the_pressed_cursor(qapp: QApplication) -> None:
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    plot = graph("cursor-mouse-drag-selection")
    widget = PyQtLabGraphCursorWidget(plot)
    widget.resize(420, 400)
    widget.show()
    for key, value in (("first", 0.2), ("second", 0.4), ("third", 0.6)):
        plot.cursors.add("x", key=key, value=value)
    qapp.processEvents()
    view = widget.list
    dragged: list[list[str]] = []
    view.startDrag = lambda _actions: dragged.append(  # type: ignore[method-assign]
        [
            key
            for row in sorted({index.row() for index in view.selectedIndexes()})
            for key in widget.model.block_cursor_keys(row)
        ]
    )
    source = view.visualRect(widget.model.index(0, 0))
    target = view.visualRect(widget.model.index(2, 0))
    start = QPoint(source.left() + 60, source.center().y())

    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start)
    for step in range(1, target.center().y() - start.y(), 2):
        QTest.mouseMove(view.viewport(), QPoint(start.x(), start.y() + step))
    QTest.mouseRelease(
        view.viewport(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, start
    )

    assert dragged == [["first"]]
    assert plot.cursors.selected_keys() == ["first"]
    widget.close()


def _three_cursor_list(qapp: QApplication, identifier: str):  # type: ignore[no-untyped-def]
    from PySide6.QtCore import QPoint

    plot = graph(identifier)
    widget = PyQtLabGraphCursorWidget(plot)
    widget.resize(420, 400)
    widget.show()
    for key, value in (("first", 0.2), ("second", 0.4), ("third", 0.6)):
        plot.cursors.add("x", key=key, value=value)
    qapp.processEvents()
    view = widget.list

    def point(row: int) -> QPoint:
        rect = view.visualRect(widget.model.index(row, 0))
        return QPoint(rect.left() + 60, rect.center().y())

    return plot, widget, view, point


def test_mouse_drag_of_a_multi_selection_carries_all_selected_cursors(
    qapp: QApplication,
) -> None:
    from PySide6.QtTest import QTest

    plot, widget, view, point = _three_cursor_list(qapp, "cursor-multi-drag")
    dragged: list[list[str]] = []
    view.startDrag = lambda _actions: dragged.append(  # type: ignore[method-assign]
        [
            key
            for row in sorted({index.row() for index in view.selectedIndexes()})
            for key in widget.model.block_cursor_keys(row)
        ]
    )
    left, none, ctrl = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ControlModifier
    QTest.mouseClick(view.viewport(), left, none, point(0))
    QTest.mouseClick(view.viewport(), left, ctrl, point(2))
    QTest.mousePress(view.viewport(), left, none, point(0))
    QTest.mouseMove(view.viewport(), point(1))
    QTest.mouseRelease(view.viewport(), left, none, point(1))

    assert dragged == [["first", "third"]]
    assert plot.cursors.selected_keys() == ["first", "third"]
    widget.close()


def test_click_on_a_multi_selection_without_drag_selects_only_that_cursor(
    qapp: QApplication,
) -> None:
    from PySide6.QtTest import QTest

    plot, widget, view, point = _three_cursor_list(qapp, "cursor-multi-click")
    left, none, ctrl = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, Qt.KeyboardModifier.ControlModifier
    QTest.mouseClick(view.viewport(), left, none, point(0))
    QTest.mouseClick(view.viewport(), left, ctrl, point(2))
    QTest.mouseClick(view.viewport(), left, none, point(2))

    assert plot.cursors.selected_keys() == ["third"]
    widget.close()
