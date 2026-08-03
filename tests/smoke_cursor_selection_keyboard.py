from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cursor_smoke_helpers import container, graph, select_rows
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox


def main() -> None:
    app = QApplication.instance() or QApplication([])
    plot = graph("cursor-selection-keyboard", cursor_container=container())
    plot.plot("sensor", np.array([0.0, 1.0, 3.0]), np.array([0.0, 10.0, 30.0]))
    plot.apply_manual_x_limits(0.0, 10.0)
    plot.apply_manual_y_limits(-5.0, 5.0)
    free_x = plot.add_cursor("x", key="free_x", value=5.0)
    peer_x = plot.add_cursor("x", key="peer_x", value=7.0)
    free_y = plot.add_cursor("y", key="free_y", value=0.0)
    snap_x = plot.add_cursor(
        "x",
        key="snap_x",
        value=1.0,
        snap_target_curve_key="sensor",
    )
    assert plot._test_cursor_widget is not None
    widget = plot._test_cursor_widget
    view = widget.list.viewport()
    view.setFocus()

    assert widget.select_cursor(free_x)
    assert not widget.select_cursor("missing")
    select_rows(widget, 0, 1)
    QTest.keyClick(view, Qt.Key.Key_Right)
    app.processEvents()
    assert math.isclose(plot.cursor_state(free_x).value, 5.1)
    assert math.isclose(plot.cursor_state(peer_x).value, 7.1)
    assert widget.selected_cursor_keys() == [free_x, peer_x]

    widget.select_cursor(free_y)
    QTest.keyClick(view, Qt.Key.Key_Up)
    app.processEvents()
    assert math.isclose(plot.cursor_state(free_y).value, 0.1)
    widget.select_cursor(snap_x)
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert plot.cursor_state(snap_x).value == 3.0
    QTest.keyClick(view, Qt.Key.Key_Left)
    assert plot.cursor_state(snap_x).value == 1.0

    removed: list[str] = []
    plot.cursor_removed.connect(removed.append)
    widget.select_cursor(peer_x)
    original_question = QMessageBox.question
    QMessageBox.question = lambda *args, **kwargs: QMessageBox.StandardButton.Yes
    try:
        QTest.keyClick(view, Qt.Key.Key_Delete)
        app.processEvents()
    finally:
        QMessageBox.question = original_question
    assert peer_x not in {state.key for state in plot.cursor_states()}
    assert removed == [peer_x]
    print("cursor selection and keyboard smoke ok")


if __name__ == "__main__":
    main()
