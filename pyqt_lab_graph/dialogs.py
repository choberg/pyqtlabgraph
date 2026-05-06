from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QWidget,
)

from .axis import AxisMode

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


def show_customize_dialog(plot: PyQtLabGraphWidget, curve_key: str | None = None) -> None:
    if not plot.curve_order:
        return

    dialog = QDialog(plot.plot_container)
    dialog.setWindowTitle("Customize")

    x_label = QLineEdit(plot.x_label_text, dialog)
    y_label = QLineEdit(plot.y_label_text, dialog)

    x_mode_combo = QComboBox(dialog)
    x_mode_combo.addItem("Auto (SI)", AxisMode.AUTO)
    x_mode_combo.addItem("Linear (Raw)", AxisMode.LINEAR)
    x_mode_combo.addItem("Time (h:min:s)", AxisMode.TIME)
    x_mode_combo.setCurrentIndex(x_mode_combo.findData(plot.x_axis_mode))

    y_mode_combo = QComboBox(dialog)
    y_mode_combo.addItem("Auto (SI)", AxisMode.AUTO)
    y_mode_combo.addItem("Linear (Raw)", AxisMode.LINEAR)
    y_mode_combo.addItem("Time (h:min:s)", AxisMode.TIME)
    y_mode_combo.setCurrentIndex(y_mode_combo.findData(plot.y_axis_mode))

    grid_checkbox = QCheckBox(dialog)
    grid_checkbox.setChecked(plot.grid_item.isVisible())
    apply_x_range_checkbox = QCheckBox(dialog)
    apply_y_range_checkbox = QCheckBox(dialog)

    curve_combo = QComboBox(dialog)
    for key in plot.curve_order:
        curve = plot.curves[key]
        curve_combo.addItem(curve.label, key)
    if curve_key is not None:
        curve_index = curve_combo.findData(curve_key)
        curve_combo.setCurrentIndex(max(curve_index, 0))

    line_enabled_checkbox = QCheckBox(dialog)
    line_color_button = QPushButton(dialog)
    line_width_spin = QDoubleSpinBox(dialog)
    line_width_spin.setRange(0.1, 20.0)
    line_width_spin.setDecimals(1)
    line_width_spin.setSingleStep(0.1)
    marker_enabled_checkbox = QCheckBox(dialog)
    marker_filled_checkbox = QCheckBox(dialog)
    marker_symbol_combo = QComboBox(dialog)
    marker_options = [
        ("Circle", "o"),
        ("Square", "s"),
        ("Diamond", "d"),
        ("Triangle up", "t1"),
        ("Triangle down", "t"),
        ("Triangle right", "t2"),
        ("Triangle left", "t3"),
        ("Pentagon", "p"),
        ("Hexagon", "h"),
        ("Star", "star"),
        ("Plus", "+"),
        ("Cross", "x"),
        ("Crosshair", "crosshair"),
    ]
    for label, symbol in marker_options:
        marker_symbol_combo.addItem(label, symbol)
    marker_size_spin = QSpinBox(dialog)
    marker_size_spin.setRange(1, 40)

    selected_color = QColor()

    def load_curve_style(index: int) -> None:
        nonlocal selected_color
        curve = plot.curves[str(curve_combo.itemData(index))]
        style = curve.style
        line_enabled_checkbox.setChecked(bool(style["line_enabled"]))
        selected_color = QColor(str(style["line_color"]))
        _set_color_button_style(line_color_button, selected_color)
        line_width_spin.setValue(float(style["line_width"]))
        marker_enabled_checkbox.setChecked(bool(style["marker_enabled"]))
        marker_filled_checkbox.setChecked(bool(style["marker_filled"]))
        marker_index = marker_symbol_combo.findData(str(style["marker_symbol"]))
        marker_symbol_combo.setCurrentIndex(max(marker_index, 0))
        marker_size_spin.setValue(int(style["marker_size"]))

    def choose_line_color() -> None:
        nonlocal selected_color
        selected = QColorDialog.getColor(selected_color, dialog, "Line color")
        if selected.isValid():
            selected_color = selected
            _set_color_button_style(line_color_button, selected_color)

    curve_combo.currentIndexChanged.connect(load_curve_style)
    line_color_button.clicked.connect(choose_line_color)
    load_curve_style(curve_combo.currentIndex())

    xmin, xmax = plot.get_x_range()
    ymin, ymax = plot.get_y_range()
    x_min_spin = _range_spin_box(xmin, dialog)
    x_max_spin = _range_spin_box(xmax, dialog)
    y_min_spin = _range_spin_box(ymin, dialog)
    y_max_spin = _range_spin_box(ymax, dialog)

    layout = QFormLayout(dialog)
    layout.addRow("X label:", x_label)
    layout.addRow("X mode:", x_mode_combo)
    layout.addRow("Y label:", y_label)
    layout.addRow("Y mode:", y_mode_combo)
    layout.addRow("Grid:", grid_checkbox)
    layout.addRow("Curve:", curve_combo)
    layout.addRow("Line:", line_enabled_checkbox)
    layout.addRow("Line color:", line_color_button)
    layout.addRow("Line width:", line_width_spin)
    layout.addRow("Markers:", marker_enabled_checkbox)
    layout.addRow("Filled markers:", marker_filled_checkbox)
    layout.addRow("Marker shape:", marker_symbol_combo)
    layout.addRow("Marker size:", marker_size_spin)
    layout.addRow("Apply X range:", apply_x_range_checkbox)
    layout.addRow("X range:", _range_row(x_min_spin, x_max_spin))
    layout.addRow("Apply Y range:", apply_y_range_checkbox)
    layout.addRow("Y range:", _range_row(y_min_spin, y_max_spin))

    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    plot.set_axis_labels(
        x_label.text(),
        y_label.text(),
        x_mode=x_mode_combo.currentData(),
        y_mode=y_mode_combo.currentData(),
    )
    plot.set_grid_visible(grid_checkbox.isChecked())
    selected_curve_key = str(curve_combo.currentData())
    plot.set_curve_style(
        selected_curve_key,
        {
            "line_enabled": line_enabled_checkbox.isChecked(),
            "line_color": selected_color.name(),
            "line_width": line_width_spin.value(),
            "marker_enabled": marker_enabled_checkbox.isChecked(),
            "marker_filled": marker_filled_checkbox.isChecked(),
            "marker_symbol": marker_symbol_combo.currentData(),
            "marker_size": marker_size_spin.value(),
        },
    )
    if apply_x_range_checkbox.isChecked():
        plot.apply_manual_x_limits(
            min(x_min_spin.value(), x_max_spin.value()),
            max(x_min_spin.value(), x_max_spin.value()),
        )
        if plot.toolbar is not None:
            plot.toolbar.set_autoscale_x_checked(False)
            plot.toolbar.set_rolling_checked(False)
    if apply_y_range_checkbox.isChecked():
        plot.apply_manual_y_limits(
            min(y_min_spin.value(), y_max_spin.value()),
            max(y_min_spin.value(), y_max_spin.value()),
        )
        if plot.toolbar is not None:
            plot.toolbar.set_autoscale_y_checked(False)


def _range_spin_box(value: float, parent: QWidget) -> QDoubleSpinBox:
    spin_box = QDoubleSpinBox(parent)
    spin_box.setRange(-1_000_000.0, 1_000_000.0)
    spin_box.setDecimals(3)
    spin_box.setValue(value)
    return spin_box


def _range_row(min_spin: QDoubleSpinBox, max_spin: QDoubleSpinBox) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(QLabel("Min"))
    layout.addWidget(min_spin)
    layout.addWidget(QLabel("Max"))
    layout.addWidget(max_spin)
    return widget


def _set_color_button_style(button: QPushButton, color: QColor) -> None:
    button.setText(color.name())
    text_color = "#ffffff" if color.lightness() < 128 else "#111827"
    button.setStyleSheet(
        f"""
        QPushButton {{
            background-color: {color.name()};
            color: {text_color};
            border: 1px solid #6b7280;
            border-radius: 4px;
            padding: 4px 8px;
        }}
        """
    )
