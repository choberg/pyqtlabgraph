from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cursor_smoke_helpers import graph
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QLineEdit, QListView

from pyqtlabgraph import PyQtLabGraphCursorWidget
from pyqtlabgraph.cursor_ui import (
    _CURSOR_EDIT_FIELD_NAME,
    _CURSOR_EDIT_FIELD_VALUE,
)


def _record(widget: PyQtLabGraphCursorWidget, row: int):
    return widget.model.display_record(row)


def main() -> None:
    QApplication.instance() or QApplication([])
    plot = graph("cursor-display-editing-settings")
    plot.plot("sensor", np.array([1.0, 2.0, 3.0]), np.array([10.0, 20.0, 30.0]))
    free_x = plot.add_cursor("x", key="free_x", name="Free X", value=1.5)
    free_y = plot.add_cursor("y", key="free_y", name="Free Y", value=20.0)
    snap_x = plot.add_cursor(
        "x",
        key="snap_x",
        name="Snap X",
        value=2.6,
        snap_target_curve_key="sensor",
    )
    widget = PyQtLabGraphCursorWidget(plot)

    assert isinstance(widget.list, QListView)
    assert widget.title_label.text() == "Cursors"
    assert widget.model.rowCount() == 3
    assert [_record(widget, row).name for row in range(3)] == ["Free X", "Free Y", "Snap X"]
    assert _record(widget, 2).detail_text == "sensor  30"
    tooltip = widget.model.data(widget.model.index(2, 0), Qt.ItemDataRole.ToolTipRole)
    assert "Target curve: sensor" in str(tooltip)
    assert "Target value: 30" in str(tooltip)

    moved: list[tuple[str, float]] = []
    plot.cursor_moved.connect(lambda key, value: moved.append((key, value)))
    assert widget.model.setData(widget.model.index(0, 0), "2.75", Qt.ItemDataRole.EditRole)
    assert plot.cursor_state(free_x).value == 2.75
    assert _record(widget, 0).value_text == "2.75"
    assert moved[-1] == (free_x, 2.75)
    assert widget.model.setData(widget.model.index(2, 0), "1.6", Qt.ItemDataRole.EditRole)
    assert plot.cursor_state(snap_x).value == 2.0
    for invalid in ("abc", "nan", "inf"):
        assert not widget.model.setData(widget.model.index(0, 0), invalid, Qt.ItemDataRole.EditRole)

    widget.model.edit_field = _CURSOR_EDIT_FIELD_NAME
    assert widget.model.setData(widget.model.index(1, 0), "Inline Y", Qt.ItemDataRole.EditRole)
    assert plot.cursor_state(free_y).name == "Inline Y"
    widget.model.edit_field = _CURSOR_EDIT_FIELD_VALUE
    widget._set_cursor_color(free_y, "#e69f00")
    assert plot.cursor_state(free_y).style.line_color == "#e69f00"
    widget._toggle_cursor_visibility(widget.model.index(1, 0))
    assert plot.cursor_state(free_y).visible is False

    original_show = QDialog.show

    def accept_settings(dialog: QDialog) -> None:
        if dialog.objectName() != "pyqtLabGraphCursorSettingsDialog":
            original_show(dialog)
            return
        name = dialog.findChild(QLineEdit, "pyqtLabGraphCursorNameEdit")
        visible = dialog.findChild(QCheckBox, "pyqtLabGraphCursorVisibleCheckbox")
        label = dialog.findChild(QCheckBox, "pyqtLabGraphCursorShowLabelCheckbox")
        assert name is not None and visible is not None and label is not None
        name.setText("Edited X")
        visible.setChecked(False)
        label.setChecked(True)
        dialog.line_color = QColor("#cc79a7")
        dialog._accept()

    widget.select_cursor(free_x)
    QDialog.show = accept_settings
    try:
        widget.show_selected_cursor_settings()
    finally:
        QDialog.show = original_show
    state = plot.cursor_state(free_x)
    assert state.name == "Edited X"
    assert state.visible is False
    assert state.label_visible is True
    assert state.style.line_color == "#cc79a7"

    unit_plot = graph("cursor-display-units")
    unit_plot.set_axis_labels("Voltage", "Signal", "V", "A", x_mode="auto", y_mode="linear")
    unit_plot.apply_manual_x_limits(0.0, 0.002)
    unit_plot.bottom_axis.updateAutoSIPrefix()
    unit_plot.add_cursor("x", value=0.0015)
    unit_widget = PyQtLabGraphCursorWidget(unit_plot)
    assert _record(unit_widget, 0).value_text == "1.5 mV"
    assert _record(unit_widget, 0).edit_value_text == "0.0015"
    unit_plot.set_axis_labels("Elapsed", "Signal", "s", "A", x_mode="time")
    assert _record(unit_widget, 0).value_text == "0.0015 s"
    print("cursor display, editing, and settings smoke ok")


if __name__ == "__main__":
    main()
