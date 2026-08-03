from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
)

from .axis import AxisMode
from .customize_controls import (
    build_curve_tabs,
    build_global_tab,
    set_color_button_style,
)
from .customize_session import CustomizeSession

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


_CUSTOMIZE_DIALOG_SIZE = (430, 690)
_PREVIEW_HINT = (
    "Changes are previewed live. Cancel restores the state from when the dialog "
    "was opened or last saved."
)


def prepare_customize_dialog(
    plot: PyQtLabGraphWidget,
    curve_key: str | None = None,
    *,
    existing_dialog: QDialog | None = None,
) -> tuple[QDialog, bool]:
    dialog = existing_dialog
    if dialog is not None:
        if curve_key is not None and isinstance(dialog, _CustomizeDialog):
            dialog.select_initial_curve_tab(curve_key)
        dialog.raise_()
        dialog.activateWindow()
        return dialog, False

    dialog = _CustomizeDialog(plot, curve_key)
    return dialog, True


class _CustomizeDialog(QDialog):
    def __init__(self, plot: PyQtLabGraphWidget, curve_key: str | None) -> None:
        super().__init__(plot)
        self.plot = plot
        self.session = CustomizeSession(plot)
        self._x_range_return_widgets: tuple[QObject, ...] = ()
        self._y_range_return_widgets: tuple[QObject, ...] = ()
        self._preview_enabled = False

        self.setObjectName("pyqtLabGraphCustomizeDialog")
        self.setWindowTitle("Customize")
        self.resize(*_CUSTOMIZE_DIALOG_SIZE)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self.tabs = QTabWidget(self)
        self.global_controls = build_global_tab(plot, self, self.tabs)
        self.curve_editors = build_curve_tabs(
            plot,
            self,
            self.tabs,
            self._choose_line_color,
        )
        self.select_initial_curve_tab(curve_key)
        self._sync_log_checkbox_availability()
        self.session.sync_ranges_from_plot()

        hint = QLabel(_PREVIEW_HINT, self)
        hint.setObjectName("pyqtLabGraphCustomizePreviewHint")
        hint.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(hint)
        layout.addWidget(self._build_buttons())

        self._connect_live_preview()
        self._install_range_return_handlers()
        self._preview_enabled = True

    def showEvent(self, event: QEvent) -> None:
        if not event.spontaneous():
            self.session.capture_baseline()
        super().showEvent(event)

    def select_initial_curve_tab(self, curve_key: str | None) -> None:
        curve_keys = [key for key, _label in self.plot.curve_choices()]
        if curve_key in curve_keys:
            index = curve_keys.index(str(curve_key)) + 1
            self.tabs.setCurrentIndex(index)

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        apply_and_close = buttons.button(QDialogButtonBox.StandardButton.Ok)
        apply_and_close.setText("Apply && Close")
        apply_and_close.setObjectName("pyqtLabGraphApplyAndCloseButton")
        save_button = buttons.addButton("Save Layout", QDialogButtonBox.ButtonRole.ActionRole)
        save_button.setObjectName("pyqtLabGraphSaveLayoutButton")
        save_button.clicked.connect(self._save_layout)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.finished.connect(self._finish)
        return buttons

    def _connect_live_preview(self) -> None:
        controls = self.global_controls
        for line_edit in (
            controls.x_label,
            controls.x_units,
            controls.y_label,
            controls.y_units,
        ):
            line_edit.textChanged.connect(self._preview_axes)
        controls.x_mode.currentIndexChanged.connect(self._handle_axis_mode_changed)
        controls.y_mode.currentIndexChanged.connect(self._handle_axis_mode_changed)
        controls.x_log.toggled.connect(self._preview_axes)
        controls.y_log.toggled.connect(self._preview_axes)
        for checkbox in (
            controls.grid,
            controls.antialiasing,
            controls.downsampling,
            controls.clip_to_view,
            controls.adaptive_performance,
        ):
            checkbox.toggled.connect(self._preview_rendering)
        controls.plot_background.currentIndexChanged.connect(self._preview_plot_background)
        controls.plot_style.currentIndexChanged.connect(self._preview_plot_style)
        controls.preview_x_range_button.clicked.connect(self._preview_x_range)
        controls.preview_y_range_button.clicked.connect(self._preview_y_range)
        for key, editor in self.curve_editors.items():
            editor.visible.toggled.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.line_enabled.toggled.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.line_width.valueChanged.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_enabled.toggled.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_filled.toggled.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_symbol.currentIndexChanged.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_size.valueChanged.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_outline_width.valueChanged.connect(
                lambda _value, curve_key=key: self._preview_curve(curve_key)
            )

    def _install_range_return_handlers(self) -> None:
        controls = self.global_controls
        self._x_range_return_widgets = (
            controls.x_min,
            controls.x_min.lineEdit(),
            controls.x_max,
            controls.x_max.lineEdit(),
        )
        self._y_range_return_widgets = (
            controls.y_min,
            controls.y_min.lineEdit(),
            controls.y_max,
            controls.y_max.lineEdit(),
        )
        for widget in self._x_range_return_widgets + self._y_range_return_widgets:
            widget.installEventFilter(self)

    def _handle_axis_mode_changed(self, *_args: object) -> None:
        self._sync_log_checkbox_availability()
        self._preview_axes()

    def _sync_log_checkbox_availability(self) -> None:
        controls = self.global_controls
        self._sync_log_checkbox(controls.x_mode, controls.x_log)
        self._sync_log_checkbox(controls.y_mode, controls.y_log)

    @staticmethod
    def _sync_log_checkbox(mode_combo: QComboBox, log_checkbox: QCheckBox) -> None:
        time_mode = mode_combo.currentData() == AxisMode.TIME
        if time_mode and log_checkbox.isChecked():
            log_checkbox.blockSignals(True)
            log_checkbox.setChecked(False)
            log_checkbox.blockSignals(False)
        log_checkbox.setEnabled(not time_mode)

    def _preview_axes(self, *_args: object) -> None:
        if not self._preview_enabled:
            return
        self._sync_log_checkbox_availability()
        x_range, y_range = self.session.preview_axes(self.global_controls)
        self._set_range_controls(x_range, y_range)

    def _set_range_controls(
        self,
        x_range: tuple[float, float],
        y_range: tuple[float, float],
    ) -> None:
        controls = self.global_controls
        spins = (controls.x_min, controls.x_max, controls.y_min, controls.y_max)
        for spin in spins:
            spin.blockSignals(True)
        controls.x_min.setValue(x_range[0])
        controls.x_max.setValue(x_range[1])
        controls.y_min.setValue(y_range[0])
        controls.y_max.setValue(y_range[1])
        for spin in spins:
            spin.blockSignals(False)

    def _preview_rendering(self, *_args: object) -> None:
        if self._preview_enabled:
            self.session.preview_rendering(self.global_controls)

    def _preview_plot_background(self, *_args: object) -> None:
        if not self._preview_enabled:
            return
        self.session.preview_theme(self.global_controls)
        for editor in self.curve_editors.values():
            set_color_button_style(editor.line_color_button, editor.line_color, self.plot.theme)

    def _preview_plot_style(self, *_args: object) -> None:
        if not self._preview_enabled:
            return
        style = self.plot.style_registry.resolve_plot_style(
            str(self.global_controls.plot_style.currentData())
        )
        self.plot.set_plot_style(style)
        for index, (key, _label) in enumerate(self.plot.curve_choices()):
            self.curve_editors[key].set_curve_style(style.curve_style(index), self.plot.theme)

    def _preview_x_range(self, *_args: object) -> None:
        if self._preview_enabled:
            self.session.preview_x_range(self.global_controls)

    def _preview_y_range(self, *_args: object) -> None:
        if self._preview_enabled:
            self.session.preview_y_range(self.global_controls)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }:
            if watched in self._x_range_return_widgets:
                self._preview_x_range()
                return True
            if watched in self._y_range_return_widgets:
                self._preview_y_range()
                return True
        return super().eventFilter(watched, event)

    def _preview_curve(self, key: str) -> None:
        if self._preview_enabled:
            self.session.preview_curve(key, self.curve_editors[key])

    def _choose_line_color(self, key: str) -> None:
        editor = self.curve_editors[key]
        curve_labels = dict(self.plot.curve_choices())
        if key not in curve_labels:
            return
        selected = QColorDialog.getColor(
            QColor(editor.line_color),
            self,
            f"{curve_labels[key]} line color",
        )
        if selected.isValid():
            editor.line_color = selected
            set_color_button_style(editor.line_color_button, selected, self.plot.theme)
            self._preview_curve(key)

    def _save_layout(self) -> None:
        try:
            self.session.save_layout(self.global_controls, self.curve_editors)
        except Exception as exc:
            QMessageBox.critical(self, "Save layout", str(exc))

    def _finish(self, result: int) -> None:
        if result == int(QDialog.DialogCode.Accepted):
            self.session.apply_all(self.global_controls, self.curve_editors)
        else:
            self.session.rollback()
        self.deleteLater()
