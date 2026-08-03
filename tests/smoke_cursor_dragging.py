from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import PyQtLabGraphCursorWidget, PyQtLabGraphWidget


def _container() -> QWidget:
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


def _cursor_item(graph: PyQtLabGraphWidget, cursor_key: str):
    return graph._cursor_controller.presenter.cursor_items[cursor_key].item


def _simulate_drag(graph: PyQtLabGraphWidget, cursor_key: str, value: float) -> None:
    line = _cursor_item(graph, cursor_key)
    line.blockSignals(True)
    try:
        line.setValue(value)
    finally:
        line.blockSignals(False)
    line.sigPositionChanged.emit(line)


def _select_rows(graph: PyQtLabGraphWidget, *rows: int) -> None:
    assert graph._test_cursor_widget is not None
    selection = graph._test_cursor_widget.list.selectionModel()
    selection.clearSelection()
    first_index = None
    for row in rows:
        index = graph._test_cursor_widget.model.index(row, 0)
        selection.select(index, QItemSelectionModel.SelectionFlag.Select)
        if first_index is None:
            first_index = index
    if first_index is not None:
        selection.setCurrentIndex(first_index, QItemSelectionModel.SelectionFlag.NoUpdate)


def main() -> None:
    app = QApplication.instance() or QApplication([])

    graph = PyQtLabGraphWidget(
        plot_identifier="cursor-dragging",
    )
    graph.plot("sensor", np.array([1.0, 3.0, 5.0]), np.array([10.0, 30.0, 50.0]))

    moved_events: list[tuple[str, float]] = []
    graph.cursor_moved.connect(lambda key, value: moved_events.append((key, value)))

    x_key = graph.add_cursor("x", value=1.0)
    _simulate_drag(graph, x_key, 2.5)
    assert graph.cursor_state(x_key).value == 2.5
    assert moved_events[-1] == (x_key, 2.5)

    y_key = graph.add_cursor("y", value=10.0)
    _simulate_drag(graph, y_key, 42.0)
    assert graph.cursor_state(y_key).value == 42.0
    assert moved_events[-1] == (y_key, 42.0)

    moved_events.clear()
    graph.set_cursor_value(x_key, 3.5)
    assert moved_events == [(x_key, 3.5)]

    snap_key = graph.add_cursor(
        "x",
        value=1.0,
        snap_target_curve_key="sensor",
    )
    _simulate_drag(graph, snap_key, 4.6)
    assert graph.cursor_state(snap_key).value == 5.0
    assert _cursor_item(graph, snap_key).value() == 5.0
    assert moved_events[-1] == (snap_key, 5.0)

    group_cursor_container = _container()
    group_graph = PyQtLabGraphWidget(
        plot_identifier="cursor-group-dragging",
    )
    group_graph._test_cursor_widget = PyQtLabGraphCursorWidget(group_graph)
    group_cursor_container.layout().addWidget(group_graph._test_cursor_widget)
    group_graph.apply_manual_x_limits(0.0, 10.0)
    group_graph.apply_manual_y_limits(0.0, 10.0)
    group_x = group_graph.add_cursor("x", key="group_x", value=1.0)
    group_x_peer = group_graph.add_cursor("x", key="group_x_peer", value=3.0)
    group_y = group_graph.add_cursor("y", key="group_y", value=5.0)
    group_x_single = group_graph.add_cursor("x", key="group_x_single", value=8.0)
    _select_rows(group_graph, 0, 1, 2)
    assert group_graph._test_cursor_widget is not None
    group_graph._cursor_controller.presenter.handle_cursor_clicked(group_x)
    assert group_graph._test_cursor_widget.selected_cursor_keys() == [group_x, group_x_peer, group_y]
    _simulate_drag(group_graph, group_x, 2.0)
    assert group_graph.cursor_state(group_x).value == 2.0
    assert group_graph.cursor_state(group_x_peer).value == 4.0
    assert group_graph.cursor_state(group_y).value == 5.0

    group_graph._cursor_controller.presenter.handle_cursor_clicked(group_x_single)
    assert group_graph._test_cursor_widget.selected_cursor_keys() == [group_x_single]
    _simulate_drag(group_graph, group_x_single, 9.0)
    assert group_graph.cursor_state(group_x_single).value == 9.0
    assert group_graph.cursor_state(group_x).value == 2.0
    assert group_graph.cursor_state(group_x_peer).value == 4.0

    paired_container = _container()
    paired_graph = PyQtLabGraphWidget(
        plot_identifier="paired-group-dragging",
    )
    paired_graph._test_cursor_widget = PyQtLabGraphCursorWidget(paired_graph)
    paired_container.layout().addWidget(paired_graph._test_cursor_widget)
    paired_graph.apply_manual_x_limits(0.0, 10.0)
    paired_first = paired_graph.add_cursor("x", key="paired_first", value=2.0)
    paired_second = paired_graph.add_cursor("x", key="paired_second", value=4.0)
    paired_graph.add_cursor_pair(paired_first, paired_second)
    assert paired_graph._test_cursor_widget is not None
    paired_index = paired_graph._test_cursor_widget.model.index(0, 0)
    paired_graph._test_cursor_widget._select_group_for_index(
        paired_index,
        Qt.KeyboardModifier.NoModifier,
    )
    assert paired_graph._test_cursor_widget.selected_cursor_keys() == [paired_first, paired_second]
    _simulate_drag(paired_graph, paired_first, 3.0)
    assert paired_graph.cursor_state(paired_first).value == 3.0
    assert paired_graph.cursor_state(paired_second).value == 5.0

    log_graph = PyQtLabGraphWidget(
        plot_identifier="cursor-log-dragging",
    )
    log_graph.plot("positive", np.array([1.0, 10.0, 100.0]), np.array([1.0, 10.0, 100.0]))
    log_graph.set_x_log(True)
    log_graph.set_y_log(True)

    log_x_key = log_graph.add_cursor("x", value=10.0)
    _simulate_drag(log_graph, log_x_key, 2.0)
    assert math.isclose(log_graph.cursor_state(log_x_key).value, 100.0)

    log_y_key = log_graph.add_cursor("y", value=1.0)
    _simulate_drag(log_graph, log_y_key, 1.0)
    assert math.isclose(log_graph.cursor_state(log_y_key).value, 10.0)

    _simulate_drag(log_graph, log_x_key, float("nan"))
    assert math.isclose(log_graph.cursor_state(log_x_key).value, 100.0)
    assert math.isclose(_cursor_item(log_graph, log_x_key).value(), 2.0)

    app.processEvents()
    print("cursor dragging smoke ok")


if __name__ == "__main__":
    main()
