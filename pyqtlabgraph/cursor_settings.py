from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .cursor_delegate import (
    _CURSOR_COLOR_BUTTON_BORDER,
    _CURSOR_COLOR_BUTTON_DARK_TEXT,
    _CURSOR_COLOR_BUTTON_LIGHT_TEXT,
    _CURSOR_COLOR_BUTTON_LIGHTNESS_THRESHOLD,
    _CURSOR_LINE_STYLE_LABELS,
)
from .models import CursorLineStyle, CursorStyle, CursorType

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


class _CursorSettingsDialog(QDialog):
    def __init__(
        self,
        plot: "PyQtLabGraphWidget",
        cursor_key: str,
        parent: QWidget,
    ) -> None:
        super().__init__(parent)
        self.plot = plot
        self.cursor_key = cursor_key
        self.state = plot.cursor_state(cursor_key)
        self.line_color = QColor(self.state.style.line_color)
        self.setObjectName("pyqtLabGraphCursorSettingsDialog")
        self.setWindowTitle(f"{self.state.name} settings")

        self.name_edit = QLineEdit(self.state.name, self)
        self.name_edit.setObjectName("pyqtLabGraphCursorNameEdit")
        self.name_edit.textEdited.connect(lambda _text: self.name_edit.setStyleSheet(""))
        self.visible_checkbox = QCheckBox(self)
        self.visible_checkbox.setObjectName("pyqtLabGraphCursorVisibleCheckbox")
        self.visible_checkbox.setChecked(self.state.visible)
        self.show_label_checkbox = QCheckBox(self)
        self.show_label_checkbox.setObjectName("pyqtLabGraphCursorShowLabelCheckbox")
        self.show_label_checkbox.setChecked(self.state.label_visible)
        self.follow_visibility_checkbox = QCheckBox(self)
        self.follow_visibility_checkbox.setObjectName("pyqtLabGraphCursorFollowVisibilityCheckbox")
        self.follow_visibility_checkbox.setChecked(self.state.follow_target_visibility)

        self.line_color_button = QPushButton(self)
        self.line_color_button.setObjectName("pyqtLabGraphCursorLineColorButton")
        _set_cursor_color_button_style(self.line_color_button, self.line_color)
        self.line_color_button.clicked.connect(self._choose_line_color)
        self.line_width_spin = QDoubleSpinBox(self)
        self.line_width_spin.setObjectName("pyqtLabGraphCursorLineWidthSpin")
        self.line_width_spin.setRange(0.1, 20.0)
        self.line_width_spin.setSingleStep(0.5)
        self.line_width_spin.setValue(self.state.style.line_width)
        self.line_style_combo = QComboBox(self)
        self.line_style_combo.setObjectName("pyqtLabGraphCursorLineStyleCombo")
        for key, label in _CURSOR_LINE_STYLE_LABELS.items():
            self.line_style_combo.addItem(label, key)
        self.line_style_combo.setCurrentIndex(
            max(self.line_style_combo.findData(self.state.style.line_style.value), 0)
        )

        self.snap_checkbox = QCheckBox(self)
        self.snap_checkbox.setObjectName("pyqtLabGraphCursorSnapCheckbox")
        self.snap_checkbox.setChecked(self.state.snap_target_curve_key is not None)
        self.target_curve_combo = QComboBox(self)
        self.target_curve_combo.setObjectName("pyqtLabGraphCursorTargetCurveCombo")
        self._populate_target_curves()
        self.snap_checkbox.toggled.connect(self._sync_snap_controls)
        self._sync_snap_controls()

        form = QFormLayout()
        form.addRow("Name:", self.name_edit)
        form.addRow("Visible:", self.visible_checkbox)
        form.addRow("Show label:", self.show_label_checkbox)
        form.addRow("Follow target visibility:", self.follow_visibility_checkbox)
        form.addRow("Line color:", self.line_color_button)
        form.addRow("Line width:", self.line_width_spin)
        form.addRow("Line style:", self.line_style_combo)
        form.addRow("Snap to curve:", self.snap_checkbox)
        form.addRow("Target curve:", self.target_curve_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _populate_target_curves(self) -> None:
        curve_choices = self.plot.curve_choices()
        curve_order = [key for key, _label in curve_choices]
        for key, label in curve_choices:
            self.target_curve_combo.addItem(label, key)
        if self.state.snap_target_curve_key and self.state.snap_target_curve_key not in curve_order:
            self.target_curve_combo.addItem(
                f"{self.state.snap_target_curve_key} (missing)",
                self.state.snap_target_curve_key,
            )
        if self.state.snap_target_curve_key:
            self.target_curve_combo.setCurrentIndex(
                max(self.target_curve_combo.findData(self.state.snap_target_curve_key), 0)
            )

    def _sync_snap_controls(self) -> None:
        is_x_cursor = self.state.cursor_type is CursorType.X
        has_targets = self.target_curve_combo.count() > 0
        self.snap_checkbox.setEnabled(is_x_cursor and has_targets)
        self.target_curve_combo.setEnabled(is_x_cursor and has_targets and self.snap_checkbox.isChecked())
        self.follow_visibility_checkbox.setEnabled(is_x_cursor and has_targets)

    def _choose_line_color(self) -> None:
        selected = QColorDialog.getColor(self.line_color, self, f"{self.state.name} line color")
        if selected.isValid():
            self.line_color = selected
            _set_cursor_color_button_style(self.line_color_button, selected)

    def _accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.name_edit.setStyleSheet("border: 1px solid #c62828;")
            self.name_edit.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        self._apply_dialog_values(name)
        self.accept()

    def _apply_dialog_values(self, name: str) -> None:
        style = CursorStyle(
            line_color=self.line_color.name(),
            line_width=self.line_width_spin.value(),
            line_style=CursorLineStyle(str(self.line_style_combo.currentData())),
        )
        self.plot.set_cursor_name(self.cursor_key, name)
        self.plot.set_cursor_visible(self.cursor_key, self.visible_checkbox.isChecked())
        self.plot.set_cursor_label_visible(self.cursor_key, self.show_label_checkbox.isChecked())
        self.plot.set_cursor_style(self.cursor_key, style)
        if self.state.cursor_type is CursorType.X:
            snap_enabled = self.snap_checkbox.isChecked() and self.target_curve_combo.count() > 0
            target_curve_key = str(self.target_curve_combo.currentData()) if snap_enabled else None
            self.plot.set_cursor_snap_target(self.cursor_key, target_curve_key)
            self.plot.set_cursor_follow_target_visibility(
                self.cursor_key,
                self.follow_visibility_checkbox.isChecked() and snap_enabled,
            )


def _set_cursor_color_button_style(button: QPushButton, color: QColor) -> None:
    button.setText(color.name())
    text_color = (
        _CURSOR_COLOR_BUTTON_LIGHT_TEXT
        if color.lightness() < _CURSOR_COLOR_BUTTON_LIGHTNESS_THRESHOLD
        else _CURSOR_COLOR_BUTTON_DARK_TEXT
    )
    button.setStyleSheet(
        f"background-color: {color.name()}; "
        f"color: {text_color}; "
        f"border: 1px solid {_CURSOR_COLOR_BUTTON_BORDER}; "
        "padding: 2px 6px;"
    )
