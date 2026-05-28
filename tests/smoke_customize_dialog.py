from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from pyqt_lab_graph import AxisMode, CurveStyle, PyQtLabGraphWidget
from pyqt_lab_graph import dialogs
from pyqt_lab_graph.styles import BUILTIN_PLOT_STYLES


def _child(dialog: QDialog, widget_type: type, name: str):
    widget = dialog.findChild(widget_type, name)
    assert widget is not None, f"Missing dialog control: {name}"
    return widget


def _set_combo_data(combo: QComboBox, data: object) -> None:
    index = combo.findData(data)
    assert index >= 0, f"Missing combo data: {data!r}"
    combo.setCurrentIndex(index)


def main() -> None:
    app = QApplication.instance() or QApplication([])

    plot_container = QWidget()
    toolbar_container = QWidget()
    legend_container = QWidget()
    for widget in (plot_container, toolbar_container, legend_container):
        widget.setLayout(QVBoxLayout())

    graph = PyQtLabGraphWidget(
        plot_container,
        toolbar_container,
        legend_container,
        plot_identifier="customize-main",
        show_toolbar=True,
        show_legend=True,
    )
    graph.plot(
        "sensor",
        [0.0, 1.0, 2.0],
        [1.0, 2.0, 3.0],
        style=CurveStyle(line_color="#123456", marker_symbol="o"),
    )
    graph.plot("reference", [0.0, 1.0, 2.0], [3.0, 2.0, 1.0])
    graph.set_axis_labels("Time", "Temperature", x_units="s", y_units="deg C")

    original_show = dialogs.QDialog.show

    def accept_with_changes(dialog: QDialog) -> None:
        assert dialog.objectName() == "pyqtLabGraphCustomizeDialog"
        assert dialog.isModal() is False
        assert dialog.windowModality() == Qt.WindowModality.NonModal

        _child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Elapsed")
        _child(dialog, QLineEdit, "pyqtLabGraphXUnitsEdit").setText("ms")
        _child(dialog, QLineEdit, "pyqtLabGraphYLabelEdit").setText("Signal")
        _child(dialog, QLineEdit, "pyqtLabGraphYUnitsEdit").setText("V")
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphXModeCombo"), AxisMode.TIME)
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphYModeCombo"), AxisMode.LINEAR)
        assert graph.x_label_text == "Elapsed"
        assert graph.y_label_text == "Signal"
        assert graph.x_axis_mode == AxisMode.TIME
        assert graph.y_axis_mode == AxisMode.LINEAR

        _child(dialog, QCheckBox, "pyqtLabGraphGridCheckbox").setChecked(False)
        _child(dialog, QCheckBox, "pyqtLabGraphAntialiasingCheckbox").setChecked(False)
        _child(dialog, QCheckBox, "pyqtLabGraphDownsamplingCheckbox").setChecked(False)
        _child(dialog, QCheckBox, "pyqtLabGraphClipToViewCheckbox").setChecked(False)
        _child(dialog, QCheckBox, "pyqtLabGraphAdaptivePerformanceCheckbox").setChecked(False)
        assert graph.grid_item.isVisible() is False
        assert graph.render_optimizer.antialiasing_enabled is False
        assert graph.render_optimizer.downsampling_enabled is False
        assert graph.render_optimizer.clip_to_view_enabled is False
        assert graph.render_optimizer.enabled is False

        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphPlotBackgroundCombo"), "dark")
        assert graph.theme.name == "dark"
        style_combo = _child(dialog, QComboBox, "pyqtLabGraphPlotStyleCombo")
        _set_combo_data(style_combo, "dark")
        assert dialog.findChild(QPushButton, "pyqtLabGraphApplyPlotStyleButton") is None
        assert graph.plot_style.name == "dark"

        _child(dialog, QCheckBox, "pyqtLabGraphCurveVisible_sensor").setChecked(False)
        _child(dialog, QCheckBox, "pyqtLabGraphCurveLineEnabled_sensor").setChecked(False)
        _child(dialog, QDoubleSpinBox, "pyqtLabGraphCurveLineWidth_sensor").setValue(3.5)
        _child(dialog, QCheckBox, "pyqtLabGraphCurveMarkerEnabled_sensor").setChecked(True)
        _child(dialog, QCheckBox, "pyqtLabGraphCurveMarkerFilled_sensor").setChecked(True)
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphCurveMarkerSymbol_sensor"), "d")
        _child(dialog, QSpinBox, "pyqtLabGraphCurveMarkerSize_sensor").setValue(11)
        _child(dialog, QDoubleSpinBox, "pyqtLabGraphCurveMarkerOutlineWidth_sensor").setValue(2.5)
        assert graph.curve_manager.curves["sensor"].visible is False
        assert graph.curve_style("sensor").line_enabled is False
        assert graph.curve_style("sensor").marker_symbol == "d"

        assert dialog.findChild(QCheckBox, "pyqtLabGraphApplyXRangeCheckbox") is None
        assert dialog.findChild(QCheckBox, "pyqtLabGraphApplyYRangeCheckbox") is None
        _child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").setValue(7.0)
        x_max_spin = _child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin")
        x_max_spin.setValue(2.0)
        assert graph.get_x_range() != (2.0, 7.0)
        x_max_spin.lineEdit().setFocus()
        QTest.keyClick(x_max_spin.lineEdit(), Qt.Key.Key_Return)
        assert dialog in getattr(graph, "_pyqt_lab_graph_customize_dialogs")
        assert graph.get_x_range() == (2.0, 7.0)

        y_min_spin = _child(dialog, QDoubleSpinBox, "pyqtLabGraphYMinSpin")
        y_min_spin.setValue(5.0)
        _child(dialog, QDoubleSpinBox, "pyqtLabGraphYMaxSpin").setValue(-1.0)
        assert graph.get_y_range() != (-1.0, 5.0)
        y_min_spin.lineEdit().setFocus()
        QTest.keyClick(y_min_spin.lineEdit(), Qt.Key.Key_Return)
        assert dialog in getattr(graph, "_pyqt_lab_graph_customize_dialogs")
        assert graph.get_y_range() == (-1.0, 5.0)

        dialog.accept()

    dialogs.QDialog.show = accept_with_changes
    try:
        dialogs.show_customize_dialog(graph)
    finally:
        dialogs.QDialog.show = original_show

    assert graph.x_label_text == "Elapsed"
    assert graph.y_label_text == "Signal"
    assert graph.x_label_units == "ms"
    assert graph.y_label_units == "V"
    assert graph.x_axis_mode == AxisMode.TIME
    assert graph.y_axis_mode == AxisMode.LINEAR
    assert graph.grid_item.isVisible() is False
    assert graph.render_optimizer.antialiasing_enabled is False
    assert graph.render_optimizer.downsampling_enabled is False
    assert graph.render_optimizer.clip_to_view_enabled is False
    assert graph.render_optimizer.enabled is False

    assert graph.theme.name == "dark"
    assert graph.plot_style.name == "dark"
    assert graph.curve_manager.curves["sensor"].visible is False
    assert graph.curve_manager.curves["sensor"].item.isVisible() is False

    sensor_style = graph.curve_style("sensor")
    assert sensor_style.line_enabled is False
    assert sensor_style.line_width == 3.5
    assert sensor_style.marker_enabled is True
    assert sensor_style.marker_filled is True
    assert sensor_style.marker_symbol == "d"
    assert sensor_style.marker_size == 11
    assert sensor_style.marker_outline_width == 2.5

    reference_style = graph.curve_style("reference")
    dark_reference_style = BUILTIN_PLOT_STYLES["dark"].curve_style(1)
    assert reference_style.line_enabled == dark_reference_style.line_enabled
    assert reference_style.line_color.lower() == dark_reference_style.line_color.lower()
    assert reference_style.line_width == dark_reference_style.line_width
    assert reference_style.marker_symbol == dark_reference_style.marker_symbol
    assert reference_style.marker_size == dark_reference_style.marker_size
    assert reference_style.marker_outline_width == dark_reference_style.marker_outline_width
    assert reference_style.marker_enabled == dark_reference_style.marker_enabled
    assert reference_style.marker_filled == dark_reference_style.marker_filled
    assert graph.get_x_range() == (2.0, 7.0)
    assert graph.get_y_range() == (-1.0, 5.0)
    assert getattr(graph, "_pyqt_lab_graph_customize_dialogs") == []

    empty_plot_container = QWidget()
    empty_toolbar_container = QWidget()
    empty_legend_container = QWidget()
    for widget in (empty_plot_container, empty_toolbar_container, empty_legend_container):
        widget.setLayout(QVBoxLayout())

    empty_graph = PyQtLabGraphWidget(
        empty_plot_container,
        empty_toolbar_container,
        empty_legend_container,
        plot_identifier="customize-empty",
        show_toolbar=False,
        show_legend=False,
    )
    empty_graph.set_axis_labels("Raw X", "Raw Y", x_units="samples", y_units="counts")
    no_curve_dialog_was_shown = False

    def accept_no_curve_dialog(dialog: QDialog) -> None:
        nonlocal no_curve_dialog_was_shown
        no_curve_dialog_was_shown = True
        assert dialog.objectName() == "pyqtLabGraphCustomizeDialog"

        _child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Index")
        _child(dialog, QLineEdit, "pyqtLabGraphXUnitsEdit").setText("")
        _child(dialog, QLineEdit, "pyqtLabGraphYLabelEdit").setText("Amplitude")
        _child(dialog, QLineEdit, "pyqtLabGraphYUnitsEdit").setText("mV")
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphXModeCombo"), AxisMode.LINEAR)
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphYModeCombo"), AxisMode.AUTO)
        _child(dialog, QCheckBox, "pyqtLabGraphGridCheckbox").setChecked(False)
        dialog.accept()

    dialogs.QDialog.show = accept_no_curve_dialog
    try:
        dialogs.show_customize_dialog(empty_graph, curve_key="missing")
    finally:
        dialogs.QDialog.show = original_show

    assert no_curve_dialog_was_shown is True
    assert empty_graph.x_label_text == "Index"
    assert empty_graph.y_label_text == "Amplitude"
    assert empty_graph.x_label_units is None
    assert empty_graph.y_label_units == "mV"
    assert empty_graph.x_axis_mode == AxisMode.LINEAR
    assert empty_graph.y_axis_mode == AxisMode.AUTO
    assert empty_graph.grid_item.isVisible() is False

    restore_plot_container = QWidget()
    restore_plot_container.setLayout(QVBoxLayout())
    restore_graph = PyQtLabGraphWidget(
        restore_plot_container,
        plot_identifier="customize-restore",
        show_toolbar=False,
        show_legend=False,
        theme="light",
        plot_style="light",
    )
    restore_graph.plot("sensor", [0.0, 1.0], [1.0, 2.0])
    restore_graph.set_axis_labels("Before X", "Before Y", x_units="s", y_units="V")
    restore_graph.apply_manual_x_limits(-1.0, 3.0)
    restore_graph.apply_manual_y_limits(-2.0, 4.0)
    original_style = restore_graph.curve_style("sensor")

    def cancel_after_preview(dialog: QDialog) -> None:
        _child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Preview X")
        _child(dialog, QLineEdit, "pyqtLabGraphYLabelEdit").setText("Preview Y")
        _child(dialog, QCheckBox, "pyqtLabGraphGridCheckbox").setChecked(False)
        _child(dialog, QCheckBox, "pyqtLabGraphAntialiasingCheckbox").setChecked(False)
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphPlotBackgroundCombo"), "dark")
        _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphPlotStyleCombo"), "dark")
        _child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").setValue(10.0)
        _child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin").setValue(20.0)
        assert restore_graph.get_x_range() == (-1.0, 3.0)
        _child(dialog, QPushButton, "pyqtLabGraphApplyXRangeButton").click()
        assert restore_graph.theme.name == "dark"
        assert restore_graph.plot_style.name == "dark"
        assert restore_graph.x_label_text == "Preview X"
        assert restore_graph.grid_item.isVisible() is False
        assert restore_graph.get_x_range() == (10.0, 20.0)
        dialog.reject()

    dialogs.QDialog.show = cancel_after_preview
    try:
        dialogs.show_customize_dialog(restore_graph)
    finally:
        dialogs.QDialog.show = original_show

    assert restore_graph.theme.name == "light"
    assert restore_graph.plot_style.name == "light"
    assert restore_graph.x_label_text == "Before X"
    assert restore_graph.y_label_text == "Before Y"
    assert restore_graph.x_label_units == "s"
    assert restore_graph.y_label_units == "V"
    assert restore_graph.grid_item.isVisible() is True
    assert restore_graph.render_optimizer.antialiasing_enabled is True
    assert restore_graph.get_x_range() == (-1.0, 3.0)
    assert restore_graph.get_y_range() == (-2.0, 4.0)
    assert restore_graph.curve_style("sensor") == original_style

    # Verify that rolling X-range remains enabled after opening customize and clicking accept (if unchanged)
    restore_graph.request_rolling_x(True)
    assert restore_graph.interaction_state.rolling_x is True

    def accept_without_changes(dialog: QDialog) -> None:
        dialog.accept()

    dialogs.QDialog.show = accept_without_changes
    try:
        dialogs.show_customize_dialog(restore_graph)
    finally:
        dialogs.QDialog.show = original_show

    assert restore_graph.interaction_state.rolling_x is True

    app.processEvents()
    print("customize dialog smoke ok")


if __name__ == "__main__":
    main()
