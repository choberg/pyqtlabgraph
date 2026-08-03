from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from demo_cursor import create_window
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication


def _record(window, row: int):
    return window.cursor_widget.model.display_record(row)


def _simulate_drag(window, cursor_key: str, value: float) -> None:
    line = window.graph._cursor_controller.presenter.cursor_items[cursor_key].item
    line.blockSignals(True)
    try:
        line.setValue(value)
    finally:
        line.blockSignals(False)
    line.sigPositionChanged.emit(line)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = create_window()
    window.show()
    app.processEvents()

    assert len(window.cursor_keys) == 3
    assert {state.key for state in window.graph.cursor_states()} == set(window.cursor_keys)

    snap_state = window.graph.cursor_state("signal_snap")
    assert snap_state.snap_target_curve_key is not None
    assert snap_state.snap_target_curve_key == "signal"

    cursor_widget = window.cursor_widget
    assert cursor_widget.plot is window.graph
    assert cursor_widget is not None
    assert cursor_widget.model.rowCount() == 3
    assert cursor_widget.layout().count() == 2
    assert cursor_widget.layout().itemAt(1).widget() is cursor_widget.list
    assert cursor_widget.title_label.text() == "Cursors"
    assert cursor_widget.add_x_button.text() == "+ X"
    assert cursor_widget.add_y_button.text() == "+ Y"
    assert window.cursor_container.layout().itemAt(0).widget() is cursor_widget
    assert window.cursor_container.objectName() == "cursorDemoInspectorContainer"
    assert window.content_container.layout().itemAt(1).widget() is window.cursor_container
    assert window.plot_column.layout().itemAt(0).widget() is window.graph.parentWidget()
    names = [_record(window, row).name for row in range(cursor_widget.model.rowCount())]
    assert names == ["Free X", "Free Y", "Signal Snap"]

    assert window.move_free_x_button.objectName() == "cursorDemoMoveFreeXButton"
    assert window.move_free_y_button.objectName() == "cursorDemoMoveFreeYButton"
    assert window.move_snap_button.objectName() == "cursorDemoMoveSnapButton"
    assert window.reset_button.objectName() == "cursorDemoResetButton"
    assert window.status_label.objectName() == "cursorDemoStatusLabel"
    assert window.status_label.text() == "Last cursor move: none"
    dark_mode_action = window.findChild(QAction, "demoDarkModeAction")
    assert dark_mode_action is not None
    dark_mode_action.setChecked(True)
    app.processEvents()
    assert window.graph.theme.name == "dark"
    assert window.graph.plot_style.name == "dark"

    window.move_free_x_button.click()
    app.processEvents()
    assert window.graph.cursor_state("free_x").value == 4.5
    assert _record(window, 0).value_text == "4.5 s"
    assert window.status_label.text() == "Last cursor move: Free X = 4.5"

    window.move_free_y_button.click()
    app.processEvents()
    assert window.graph.cursor_state("free_y").value == -0.35
    assert _record(window, 1).value_text == "-0.35 V"
    assert window.status_label.text() == "Last cursor move: Free Y = -0.35"

    window.move_snap_button.click()
    app.processEvents()
    snapped_value = window.graph.cursor_state("signal_snap").value
    assert snapped_value != 8.12
    assert _record(window, 2).target_curve_text == "signal"
    assert _record(window, 2).target_value_text != ""
    assert window.status_label.text() == f"Last cursor move: Signal Snap = {snapped_value:.6g}"

    assert cursor_widget.model.setData(
        cursor_widget.model.index(0, 0),
        "5.25",
        Qt.ItemDataRole.EditRole,
    )
    app.processEvents()
    assert window.graph.cursor_state("free_x").value == 5.25
    assert _record(window, 0).value_text == "5.25 s"
    assert window.status_label.text() == "Last cursor move: Free X = 5.25"

    window.reset_button.click()
    app.processEvents()
    assert window.graph.cursor_state("free_x").value == 3.0
    assert window.graph.cursor_state("free_y").value == 0.5
    assert window.graph.cursor_state("signal_snap").value != snapped_value

    _simulate_drag(window, "free_x", 4.5)
    app.processEvents()
    free_x_value = cursor_widget.model.data(
        cursor_widget.model.index(0, 0),
        Qt.ItemDataRole.DisplayRole,
    )
    assert str(free_x_value).startswith("X\tFree X\t4.5 s")

    _simulate_drag(window, "signal_snap", 8.12)
    app.processEvents()
    assert window.graph.cursor_state("signal_snap").value != 8.12
    assert _record(window, 2).target_curve_text == "signal"
    assert _record(window, 2).target_value_text != ""

    window.close()
    app.processEvents()
    print("cursor demo smoke ok")


if __name__ == "__main__":
    main()
