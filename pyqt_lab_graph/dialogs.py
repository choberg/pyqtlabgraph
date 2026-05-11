from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtCore import QEvent, QObject, Qt
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
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode
from .layouts import PlotLayoutState
from .styles import BUILTIN_PLOT_STYLES, CurveStyle
from .themes import BUILTIN_THEMES, PyQtLabGraphTheme

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


_CUSTOMIZE_DIALOG_SIZE = (430, 460)

_LINE_WIDTH_MINIMUM = 0.1
_LINE_WIDTH_MAXIMUM = 20.0
_LINE_WIDTH_DECIMALS = 1
_LINE_WIDTH_STEP = 0.1

_MARKER_SIZE_MINIMUM = 1
_MARKER_SIZE_MAXIMUM = 40

_MARKER_OUTLINE_WIDTH_MINIMUM = 0.1
_MARKER_OUTLINE_WIDTH_MAXIMUM = 10.0
_MARKER_OUTLINE_WIDTH_DECIMALS = 1
_MARKER_OUTLINE_WIDTH_STEP = 0.1

_RANGE_SPIN_MINIMUM = -1_000_000.0
_RANGE_SPIN_MAXIMUM = 1_000_000.0
_RANGE_SPIN_DECIMALS = 3

_ROW_LAYOUT_MARGINS = (0, 0, 0, 0)

_COLOR_BUTTON_DARK_TEXT = "#111827"
_COLOR_BUTTON_LIGHT_TEXT = "#ffffff"
_COLOR_BUTTON_LIGHTNESS_THRESHOLD = 128
_COLOR_BUTTON_BORDER_WIDTH = 1
_COLOR_BUTTON_BORDER_RADIUS = 4
_COLOR_BUTTON_PADDING = (4, 8)

_THEME_LABELS = {
    "light": "Light",
    "dark": "Dark",
    "light-solarized": "Light Solarized",
    "dark-solarized": "Dark Solarized",
}

_PLOT_STYLE_LABELS = {
    "light": "Light",
    "dark": "Dark",
    "solarized": "Solarized",
}

_MARKER_OPTIONS = [
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


@dataclass
class _CurveStyleEditor:
    visible: QCheckBox
    line_enabled: QCheckBox
    line_color: QColor
    line_color_button: QPushButton
    line_width: QDoubleSpinBox
    marker_enabled: QCheckBox
    marker_filled: QCheckBox
    marker_symbol: QComboBox
    marker_size: QSpinBox
    marker_outline_width: QDoubleSpinBox


@dataclass
class _GlobalControls:
    x_label: QLineEdit
    x_units: QLineEdit
    y_label: QLineEdit
    y_units: QLineEdit
    x_mode: QComboBox
    y_mode: QComboBox
    grid: QCheckBox
    antialiasing: QCheckBox
    downsampling: QCheckBox
    clip_to_view: QCheckBox
    adaptive_performance: QCheckBox
    plot_background: QComboBox
    plot_style: QComboBox
    restore_view_state_on_load: QCheckBox
    x_min: QDoubleSpinBox
    x_max: QDoubleSpinBox
    apply_x_range_button: QPushButton
    y_min: QDoubleSpinBox
    y_max: QDoubleSpinBox
    apply_y_range_button: QPushButton


def show_customize_dialog(plot: PyQtLabGraphWidget, curve_key: str | None = None) -> None:
    dialog = _CustomizeDialog(plot, curve_key)
    open_dialogs = getattr(plot, "_pyqt_lab_graph_customize_dialogs", None)
    if open_dialogs is None:
        open_dialogs = []
        setattr(plot, "_pyqt_lab_graph_customize_dialogs", open_dialogs)
    open_dialogs.append(dialog)
    dialog.finished.connect(lambda _result: _forget_dialog(plot, dialog))
    dialog.show()


class _CustomizeDialog(QDialog):
    def __init__(self, plot: PyQtLabGraphWidget, curve_key: str | None) -> None:
        super().__init__(plot.plot_container)
        self.plot = plot
        self.original_state = PlotLayoutState.from_widget(
            plot,
            include_x_range=True,
            include_y_range=True,
        )
        self.curve_editors: dict[str, _CurveStyleEditor] = {}
        self._x_range_return_widgets: tuple[QObject, ...] = ()
        self._y_range_return_widgets: tuple[QObject, ...] = ()
        self._preview_enabled = False

        self.setObjectName("pyqtLabGraphCustomizeDialog")
        self.setWindowTitle("Customize")
        self.resize(*_CUSTOMIZE_DIALOG_SIZE)
        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)

        self.tabs = QTabWidget(self)
        self.global_controls = self._build_global_tab()
        self._build_curve_tabs()
        self._select_initial_curve_tab(curve_key)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self._build_buttons())

        self._connect_live_preview()
        self._install_range_return_handlers()
        self._preview_enabled = True

    def _build_global_tab(self) -> _GlobalControls:
        x_label = QLineEdit(self.plot.x_label_text, self)
        x_label.setObjectName("pyqtLabGraphXLabelEdit")
        x_units = QLineEdit(self.plot.x_label_units or "", self)
        x_units.setObjectName("pyqtLabGraphXUnitsEdit")
        y_label = QLineEdit(self.plot.y_label_text, self)
        y_label.setObjectName("pyqtLabGraphYLabelEdit")
        y_units = QLineEdit(self.plot.y_label_units or "", self)
        y_units.setObjectName("pyqtLabGraphYUnitsEdit")

        x_mode = _axis_mode_combo(self, self.plot.x_axis_mode)
        x_mode.setObjectName("pyqtLabGraphXModeCombo")
        y_mode = _axis_mode_combo(self, self.plot.y_axis_mode)
        y_mode.setObjectName("pyqtLabGraphYModeCombo")

        grid = QCheckBox(self)
        grid.setObjectName("pyqtLabGraphGridCheckbox")
        grid.setChecked(self.plot.grid_item.isVisible())
        grid.setToolTip("Shows or hides the plot grid.")

        antialiasing = QCheckBox(self)
        antialiasing.setObjectName("pyqtLabGraphAntialiasingCheckbox")
        antialiasing.setChecked(self.plot.antialiasing_enabled)
        antialiasing.setToolTip("Smooths plotted lines and markers at the cost of rendering speed.")

        downsampling = QCheckBox(self)
        downsampling.setObjectName("pyqtLabGraphDownsamplingCheckbox")
        downsampling.setChecked(self.plot.downsampling_enabled)
        downsampling.setToolTip("Lets pyqtgraph reduce dense visible data before drawing.")

        clip_to_view = QCheckBox(self)
        clip_to_view.setObjectName("pyqtLabGraphClipToViewCheckbox")
        clip_to_view.setChecked(self.plot.clip_to_view_enabled)
        clip_to_view.setToolTip("Draws only the data that intersects the current visible X range.")

        adaptive_performance = QCheckBox(self)
        adaptive_performance.setObjectName("pyqtLabGraphAdaptivePerformanceCheckbox")
        adaptive_performance.setChecked(self.plot.adaptive_performance_enabled)
        adaptive_performance.setToolTip(
            "Temporarily hides markers and disables anti-aliasing when many points are visible."
        )

        plot_background = QComboBox(self)
        plot_background.setObjectName("pyqtLabGraphPlotBackgroundCombo")
        for name in BUILTIN_THEMES:
            plot_background.addItem(_THEME_LABELS.get(name, name.title()), name)
        plot_background.setCurrentIndex(max(plot_background.findData(self.plot.theme.name), 0))

        plot_style = QComboBox(self)
        plot_style.setObjectName("pyqtLabGraphPlotStyleCombo")
        for name in BUILTIN_PLOT_STYLES:
            plot_style.addItem(_PLOT_STYLE_LABELS.get(name, name.title()), name)
        plot_style.setCurrentIndex(max(plot_style.findData(self.plot.plot_style.name), 0))

        restore_view_state_on_load = QCheckBox(self)
        restore_view_state_on_load.setObjectName("pyqtLabGraphRestoreViewStateOnLoadCheckbox")
        restore_view_state_on_load.setChecked(True)
        restore_view_state_on_load.setToolTip(
            "Restores saved zoom, autoscale, and rolling-range state when loading this layout."
        )

        xmin, xmax = self.plot.get_x_range()
        ymin, ymax = self.plot.get_y_range()
        x_min = _range_spin_box(xmin, self)
        x_min.setObjectName("pyqtLabGraphXMinSpin")
        x_max = _range_spin_box(xmax, self)
        x_max.setObjectName("pyqtLabGraphXMaxSpin")
        apply_x_range_button = QPushButton("Apply", self)
        apply_x_range_button.setObjectName("pyqtLabGraphApplyXRangeButton")
        y_min = _range_spin_box(ymin, self)
        y_min.setObjectName("pyqtLabGraphYMinSpin")
        y_max = _range_spin_box(ymax, self)
        y_max.setObjectName("pyqtLabGraphYMaxSpin")
        apply_y_range_button = QPushButton("Apply", self)
        apply_y_range_button.setObjectName("pyqtLabGraphApplyYRangeButton")

        tab = QWidget(self)
        layout = QFormLayout(tab)
        layout.addRow("X label:", x_label)
        layout.addRow("X units:", x_units)
        layout.addRow("X mode:", x_mode)
        layout.addRow("Y label:", y_label)
        layout.addRow("Y units:", y_units)
        layout.addRow("Y mode:", y_mode)
        layout.addRow("Grid:", grid)
        layout.addRow("Anti-aliasing:", antialiasing)
        layout.addRow("Downsampling:", downsampling)
        layout.addRow("Clip to view:", clip_to_view)
        layout.addRow("Adaptive rendering:", adaptive_performance)
        layout.addRow("Plot background:", plot_background)
        layout.addRow("Plot style:", plot_style)
        layout.addRow("Restore view on load:", restore_view_state_on_load)
        layout.addRow("X range:", _range_row(x_min, x_max, apply_x_range_button))
        layout.addRow("Y range:", _range_row(y_min, y_max, apply_y_range_button))
        self.tabs.addTab(tab, "Global")

        return _GlobalControls(
            x_label=x_label,
            x_units=x_units,
            y_label=y_label,
            y_units=y_units,
            x_mode=x_mode,
            y_mode=y_mode,
            grid=grid,
            antialiasing=antialiasing,
            downsampling=downsampling,
            clip_to_view=clip_to_view,
            adaptive_performance=adaptive_performance,
            plot_background=plot_background,
            plot_style=plot_style,
            restore_view_state_on_load=restore_view_state_on_load,
            x_min=x_min,
            x_max=x_max,
            apply_x_range_button=apply_x_range_button,
            y_min=y_min,
            y_max=y_max,
            apply_y_range_button=apply_y_range_button,
        )

    def _build_curve_tabs(self) -> None:
        for key in self.plot.curve_order:
            self._add_curve_tab(key)

    def _add_curve_tab(self, key: str) -> None:
        curve = self.plot.curves[key]
        style = curve.style

        tab = QWidget(self)
        layout = QFormLayout(tab)
        visible = QCheckBox(tab)
        visible.setObjectName(f"pyqtLabGraphCurveVisible_{key}")
        visible.setChecked(curve.visible)
        line_enabled = QCheckBox(tab)
        line_enabled.setObjectName(f"pyqtLabGraphCurveLineEnabled_{key}")
        line_enabled.setChecked(style.line_enabled)
        line_color_button = QPushButton(tab)
        line_color_button.setObjectName(f"pyqtLabGraphCurveLineColor_{key}")
        line_color = QColor(style.line_color)
        _set_color_button_style(line_color_button, line_color, self.plot.theme)
        line_width = QDoubleSpinBox(tab)
        line_width.setObjectName(f"pyqtLabGraphCurveLineWidth_{key}")
        _configure_line_width_spin_box(line_width)
        line_width.setValue(style.line_width)
        marker_enabled = QCheckBox(tab)
        marker_enabled.setObjectName(f"pyqtLabGraphCurveMarkerEnabled_{key}")
        marker_enabled.setChecked(style.marker_enabled)
        marker_filled = QCheckBox(tab)
        marker_filled.setObjectName(f"pyqtLabGraphCurveMarkerFilled_{key}")
        marker_filled.setChecked(style.marker_filled)
        marker_symbol = QComboBox(tab)
        marker_symbol.setObjectName(f"pyqtLabGraphCurveMarkerSymbol_{key}")
        for label, symbol in _MARKER_OPTIONS:
            marker_symbol.addItem(label, symbol)
        marker_symbol.setCurrentIndex(max(marker_symbol.findData(style.marker_symbol), 0))
        marker_size = QSpinBox(tab)
        marker_size.setObjectName(f"pyqtLabGraphCurveMarkerSize_{key}")
        marker_size.setRange(_MARKER_SIZE_MINIMUM, _MARKER_SIZE_MAXIMUM)
        marker_size.setValue(style.marker_size)
        marker_outline_width = QDoubleSpinBox(tab)
        marker_outline_width.setObjectName(f"pyqtLabGraphCurveMarkerOutlineWidth_{key}")
        _configure_marker_outline_width_spin_box(marker_outline_width)
        marker_outline_width.setValue(style.marker_outline_width)

        editor = _CurveStyleEditor(
            visible=visible,
            line_enabled=line_enabled,
            line_color=line_color,
            line_color_button=line_color_button,
            line_width=line_width,
            marker_enabled=marker_enabled,
            marker_filled=marker_filled,
            marker_symbol=marker_symbol,
            marker_size=marker_size,
            marker_outline_width=marker_outline_width,
        )
        self.curve_editors[key] = editor

        line_color_button.clicked.connect(lambda _checked=False, curve_key=key: self._choose_line_color(curve_key))

        layout.addRow("Visibility:", visible)
        layout.addRow("Line:", line_enabled)
        layout.addRow("Line color:", line_color_button)
        layout.addRow("Line width:", line_width)
        layout.addRow("Markers:", marker_enabled)
        layout.addRow("Filled markers:", marker_filled)
        layout.addRow("Marker shape:", marker_symbol)
        layout.addRow("Marker size:", marker_size)
        layout.addRow("Marker outline width:", marker_outline_width)
        self.tabs.addTab(tab, curve.label)

    def _build_buttons(self) -> QDialogButtonBox:
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        save_button = buttons.addButton("Apply + Save", QDialogButtonBox.ButtonRole.ActionRole)
        save_button.setObjectName("pyqtLabGraphApplyAndSaveLayoutButton")
        save_button.clicked.connect(self._apply_and_save_layout)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.finished.connect(self._finish)
        return buttons

    def _connect_live_preview(self) -> None:
        controls = self.global_controls
        for line_edit in (controls.x_label, controls.x_units, controls.y_label, controls.y_units):
            line_edit.textChanged.connect(self._preview_axes)
        controls.x_mode.currentIndexChanged.connect(self._preview_axes)
        controls.y_mode.currentIndexChanged.connect(self._preview_axes)
        controls.grid.toggled.connect(self.plot.set_grid_visible)
        controls.antialiasing.toggled.connect(self.plot.set_antialiasing_enabled)
        controls.downsampling.toggled.connect(self.plot.set_downsampling_enabled)
        controls.clip_to_view.toggled.connect(self.plot.set_clip_to_view_enabled)
        controls.adaptive_performance.toggled.connect(self.plot.set_adaptive_performance_enabled)
        controls.plot_background.currentIndexChanged.connect(self._preview_plot_background)
        controls.plot_style.currentIndexChanged.connect(self._preview_plot_style)
        controls.apply_x_range_button.clicked.connect(self._apply_x_range_preview)
        controls.apply_y_range_button.clicked.connect(self._apply_y_range_preview)

        for key, editor in self.curve_editors.items():
            editor.visible.toggled.connect(
                lambda checked, curve_key=key: self._preview_curve(curve_key)
            )
            editor.line_enabled.toggled.connect(
                lambda checked, curve_key=key: self._preview_curve(curve_key)
            )
            editor.line_width.valueChanged.connect(
                lambda value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_enabled.toggled.connect(
                lambda checked, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_filled.toggled.connect(
                lambda checked, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_symbol.currentIndexChanged.connect(
                lambda index, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_size.valueChanged.connect(
                lambda value, curve_key=key: self._preview_curve(curve_key)
            )
            editor.marker_outline_width.valueChanged.connect(
                lambda value, curve_key=key: self._preview_curve(curve_key)
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

    def _select_initial_curve_tab(self, curve_key: str | None) -> None:
        if curve_key in self.plot.curves:
            self.tabs.setCurrentIndex(self.plot.curve_order.index(str(curve_key)) + 1)

    def _preview_axes(self) -> None:
        if not self._preview_enabled:
            return
        controls = self.global_controls
        self.plot.set_axis_labels(
            controls.x_label.text(),
            controls.y_label.text(),
            x_units=_optional_text(controls.x_units),
            y_units=_optional_text(controls.y_units),
            x_mode=controls.x_mode.currentData(),
            y_mode=controls.y_mode.currentData(),
        )

    def _preview_plot_background(self) -> None:
        if not self._preview_enabled:
            return
        self.plot.set_theme(str(self.global_controls.plot_background.currentData()))
        for editor in self.curve_editors.values():
            _set_color_button_style(editor.line_color_button, editor.line_color, self.plot.theme)

    def _preview_plot_style(self) -> None:
        if not self._preview_enabled:
            return
        plot_style = BUILTIN_PLOT_STYLES[str(self.global_controls.plot_style.currentData())]
        self.plot.apply_plot_style(plot_style)
        for index, key in enumerate(self.plot.curve_order):
            editor = self.curve_editors[key]
            style = plot_style.curve_style(index)
            editor.line_enabled.setChecked(style.line_enabled)
            editor.line_color = QColor(style.line_color)
            _set_color_button_style(editor.line_color_button, editor.line_color, self.plot.theme)
            editor.line_width.setValue(style.line_width)
            editor.marker_enabled.setChecked(style.marker_enabled)
            editor.marker_filled.setChecked(style.marker_filled)
            editor.marker_symbol.setCurrentIndex(max(editor.marker_symbol.findData(style.marker_symbol), 0))
            editor.marker_size.setValue(style.marker_size)
            editor.marker_outline_width.setValue(style.marker_outline_width)

    def _apply_x_range_preview(self) -> None:
        if not self._preview_enabled:
            return
        controls = self.global_controls
        self.plot.apply_manual_x_limits(controls.x_min.value(), controls.x_max.value())

    def _apply_y_range_preview(self) -> None:
        if not self._preview_enabled:
            return
        controls = self.global_controls
        self.plot.apply_manual_y_limits(controls.y_min.value(), controls.y_max.value())

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress and event.key() in {
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
        }:
            if watched in self._x_range_return_widgets:
                self._apply_x_range_preview()
                return True
            if watched in self._y_range_return_widgets:
                self._apply_y_range_preview()
                return True
        return super().eventFilter(watched, event)

    def _preview_curve(self, key: str) -> None:
        if not self._preview_enabled:
            return
        editor = self.curve_editors[key]
        self.plot.set_curve_visible(key, editor.visible.isChecked())
        self.plot.set_curve_style(key, self._curve_style_from_editor(editor))

    def _choose_line_color(self, key: str) -> None:
        editor = self.curve_editors[key]
        curve = self.plot.curves[key]
        selected = QColorDialog.getColor(
            QColor(editor.line_color),
            self,
            f"{curve.label} line color",
        )
        if selected.isValid():
            editor.line_color = selected
            _set_color_button_style(editor.line_color_button, selected, self.plot.theme)
            self._preview_curve(key)

    def _apply_dialog_values(self) -> None:
        controls = self.global_controls
        self.plot.set_axis_labels(
            controls.x_label.text(),
            controls.y_label.text(),
            x_units=_optional_text(controls.x_units),
            y_units=_optional_text(controls.y_units),
            x_mode=controls.x_mode.currentData(),
            y_mode=controls.y_mode.currentData(),
        )
        self.plot.set_grid_visible(controls.grid.isChecked())
        self.plot.set_antialiasing_enabled(controls.antialiasing.isChecked())
        self.plot.set_downsampling_enabled(controls.downsampling.isChecked())
        self.plot.set_clip_to_view_enabled(controls.clip_to_view.isChecked())
        self.plot.set_adaptive_performance_enabled(controls.adaptive_performance.isChecked())
        self.plot.set_theme(str(controls.plot_background.currentData()))
        self.plot.set_plot_style(str(controls.plot_style.currentData()))
        for key, editor in self.curve_editors.items():
            self.plot.set_curve_visible(key, editor.visible.isChecked())
            self.plot.set_curve_style(key, self._curve_style_from_editor(editor))
        self.plot.apply_manual_x_limits(controls.x_min.value(), controls.x_max.value())
        self.plot.apply_manual_y_limits(controls.y_min.value(), controls.y_max.value())

    def _apply_and_save_layout(self) -> None:
        controls = self.global_controls
        try:
            self._apply_dialog_values()
            state = PlotLayoutState.from_widget(
                self.plot,
                include_x_range=True,
                include_y_range=True,
                restore_view_state_on_load=controls.restore_view_state_on_load.isChecked(),
            )
            self.plot.save_layout(
                include_x_range=True,
                include_y_range=True,
                restore_view_state_on_load=controls.restore_view_state_on_load.isChecked(),
            )
            self.original_state = PlotLayoutState.from_widget(
                self.plot,
                include_x_range=True,
                include_y_range=True,
                restore_view_state_on_load=state.restore_view_state_on_load,
            )
        except Exception as exc:
            QMessageBox.critical(self, "Save layout", str(exc))

    def _finish(self, result: int) -> None:
        if result == int(QDialog.DialogCode.Accepted):
            self._apply_dialog_values()
        else:
            self.original_state.apply_to_widget(self.plot, restore_view_state=True)
        self.deleteLater()

    @staticmethod
    def _curve_style_from_editor(editor: _CurveStyleEditor) -> CurveStyle:
        return CurveStyle(
            line_enabled=editor.line_enabled.isChecked(),
            line_color=editor.line_color.name(),
            line_width=editor.line_width.value(),
            marker_enabled=editor.marker_enabled.isChecked(),
            marker_filled=editor.marker_filled.isChecked(),
            marker_symbol=str(editor.marker_symbol.currentData()),
            marker_size=editor.marker_size.value(),
            marker_outline_width=editor.marker_outline_width.value(),
        )


def _forget_dialog(plot: PyQtLabGraphWidget, dialog: QDialog) -> None:
    open_dialogs = getattr(plot, "_pyqt_lab_graph_customize_dialogs", [])
    if dialog in open_dialogs:
        open_dialogs.remove(dialog)


def _axis_mode_combo(parent: QWidget, current_mode: AxisMode) -> QComboBox:
    combo = QComboBox(parent)
    combo.addItem("Auto (SI)", AxisMode.AUTO)
    combo.addItem("Linear (Raw)", AxisMode.LINEAR)
    combo.addItem("Time (h:min:s)", AxisMode.TIME)
    combo.setCurrentIndex(combo.findData(current_mode))
    return combo


def _range_spin_box(value: float, parent: QWidget) -> QDoubleSpinBox:
    spin_box = QDoubleSpinBox(parent)
    spin_box.setRange(_RANGE_SPIN_MINIMUM, _RANGE_SPIN_MAXIMUM)
    spin_box.setDecimals(_RANGE_SPIN_DECIMALS)
    spin_box.setValue(value)
    return spin_box


def _optional_text(line_edit: QLineEdit) -> str | None:
    text = line_edit.text().strip()
    return text or None


def _configure_line_width_spin_box(spin_box: QDoubleSpinBox) -> None:
    spin_box.setRange(_LINE_WIDTH_MINIMUM, _LINE_WIDTH_MAXIMUM)
    spin_box.setDecimals(_LINE_WIDTH_DECIMALS)
    spin_box.setSingleStep(_LINE_WIDTH_STEP)


def _configure_marker_outline_width_spin_box(spin_box: QDoubleSpinBox) -> None:
    spin_box.setRange(_MARKER_OUTLINE_WIDTH_MINIMUM, _MARKER_OUTLINE_WIDTH_MAXIMUM)
    spin_box.setDecimals(_MARKER_OUTLINE_WIDTH_DECIMALS)
    spin_box.setSingleStep(_MARKER_OUTLINE_WIDTH_STEP)


def _range_row(
    min_spin: QDoubleSpinBox,
    max_spin: QDoubleSpinBox,
    apply_button: QPushButton,
) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(*_ROW_LAYOUT_MARGINS)
    layout.addWidget(QLabel("Min"))
    layout.addWidget(min_spin)
    layout.addWidget(QLabel("Max"))
    layout.addWidget(max_spin)
    layout.addWidget(apply_button)
    return widget


def _set_color_button_style(button: QPushButton, color: QColor, theme: PyQtLabGraphTheme) -> None:
    button.setText(color.name())
    text_color = (
        _COLOR_BUTTON_LIGHT_TEXT
        if color.lightness() < _COLOR_BUTTON_LIGHTNESS_THRESHOLD
        else _COLOR_BUTTON_DARK_TEXT
    )
    padding_vertical, padding_horizontal = _COLOR_BUTTON_PADDING
    button.setStyleSheet(
        f"""
        background-color: {color.name()};
        color: {text_color};
        border: {_COLOR_BUTTON_BORDER_WIDTH}px solid {theme.border};
        border-radius: {_COLOR_BUTTON_BORDER_RADIUS}px;
        padding: {padding_vertical}px {padding_horizontal}px;
        """
    )
