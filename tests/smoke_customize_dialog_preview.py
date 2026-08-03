from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customize_smoke_helpers import child, graph, set_combo_data, show_with_callback
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
)

from pyqtlabgraph import AxisMode, CurveStyle


def main() -> None:
    app = QApplication.instance() or QApplication([])
    plot = graph("customize-preview")
    plot.plot("sensor", [0.0, 1.0], [1.0, 2.0], style=CurveStyle(line_color="#123456"))
    plot.set_axis_labels("Before X", "Before Y", x_units="s", y_units="V")
    plot.apply_manual_x_limits(-1.0, 3.0)
    plot.apply_manual_y_limits(-2.0, 4.0)
    original_style = plot.curve_style("sensor")

    def preview_and_cancel(dialog: QDialog) -> None:
        child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Preview X")
        set_combo_data(child(dialog, QComboBox, "pyqtLabGraphXModeCombo"), AxisMode.TIME)
        assert child(dialog, QCheckBox, "pyqtLabGraphXLogCheckbox").isEnabled() is False
        child(dialog, QCheckBox, "pyqtLabGraphGridCheckbox").setChecked(False)
        child(dialog, QCheckBox, "pyqtLabGraphAntialiasingCheckbox").setChecked(False)
        set_combo_data(child(dialog, QComboBox, "pyqtLabGraphPlotBackgroundCombo"), "dark")
        set_combo_data(child(dialog, QComboBox, "pyqtLabGraphPlotStyleCombo"), "dark")
        child(dialog, QCheckBox, "pyqtLabGraphCurveVisible_sensor").setChecked(False)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphCurveLineWidth_sensor").setValue(3.5)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").setValue(10.0)
        x_max = child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin")
        x_max.setValue(20.0)
        assert plot.get_x_range() == (-1.0, 3.0)
        x_max.lineEdit().setFocus()
        QTest.keyClick(x_max.lineEdit(), Qt.Key.Key_Return)
        assert plot.get_x_range() == (10.0, 20.0)
        assert plot.x_label_text == "Preview X"
        assert plot.theme.name == "dark"
        assert plot.grid_item.isVisible() is False
        assert plot.curve_item("sensor").isVisible() is False
        dialog.reject()

    show_with_callback(plot, preview_and_cancel)
    assert plot.x_label_text == "Before X"
    assert plot.x_label_units == "s"
    assert plot.theme.name == "light"
    assert plot.grid_item.isVisible() is True
    assert plot._render_optimizer.antialiasing_enabled is True
    assert plot.get_x_range() == (-1.0, 3.0)
    assert plot.get_y_range() == (-2.0, 4.0)
    assert plot.curve_style("sensor") == original_style

    def apply_and_close(dialog: QDialog) -> None:
        child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Applied X")
        child(dialog, QDoubleSpinBox, "pyqtLabGraphYMinSpin").setValue(-5.0)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphYMaxSpin").setValue(5.0)
        child(dialog, QPushButton, "pyqtLabGraphApplyAndCloseButton").click()

    show_with_callback(plot, apply_and_close)
    app.processEvents()
    assert plot.x_label_text == "Applied X"
    assert plot.get_y_range() == (-5.0, 5.0)

    plot.show_customize_dialog()
    app.processEvents()
    visible_dialogs = [
        dialog
        for dialog in plot.findChildren(QDialog, "pyqtLabGraphCustomizeDialog")
        if dialog.isVisible()
    ]
    assert len(visible_dialogs) == 1
    close_dialog = visible_dialogs[0]
    child(close_dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Window-close preview")
    assert plot.x_label_text == "Window-close preview"
    close_dialog.close()
    app.processEvents()
    assert plot.x_label_text == "Applied X"
    print("customize dialog preview smoke ok")


if __name__ == "__main__":
    main()
