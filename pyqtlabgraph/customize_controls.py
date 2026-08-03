from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .axis import AxisMode
from .styles import CurveStyle
from .themes import PyQtLabGraphTheme

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget


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
class CurveStyleEditor:
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

    def curve_style(self) -> CurveStyle:
        return CurveStyle(
            line_enabled=self.line_enabled.isChecked(),
            line_color=self.line_color.name(),
            line_width=self.line_width.value(),
            marker_enabled=self.marker_enabled.isChecked(),
            marker_filled=self.marker_filled.isChecked(),
            marker_symbol=str(self.marker_symbol.currentData()),
            marker_size=self.marker_size.value(),
            marker_outline_width=self.marker_outline_width.value(),
        )

    def set_curve_style(self, style: CurveStyle, theme: PyQtLabGraphTheme) -> None:
        self.line_enabled.setChecked(style.line_enabled)
        self.line_color = QColor(style.line_color)
        set_color_button_style(self.line_color_button, self.line_color, theme)
        self.line_width.setValue(style.line_width)
        self.marker_enabled.setChecked(style.marker_enabled)
        self.marker_filled.setChecked(style.marker_filled)
        self.marker_symbol.setCurrentIndex(max(self.marker_symbol.findData(style.marker_symbol), 0))
        self.marker_size.setValue(style.marker_size)
        self.marker_outline_width.setValue(style.marker_outline_width)


@dataclass
class GlobalControls:
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
    preview_x_range_button: QPushButton
    y_min: QDoubleSpinBox
    y_max: QDoubleSpinBox
    preview_y_range_button: QPushButton
    x_log: QCheckBox
    y_log: QCheckBox


def build_global_tab(
    plot: PyQtLabGraphWidget,
    parent: QWidget,
    tabs: QTabWidget,
) -> GlobalControls:
    x_label = _line_edit(plot.x_label_text, "pyqtLabGraphXLabelEdit", parent)
    x_units = _line_edit(plot.x_label_units or "", "pyqtLabGraphXUnitsEdit", parent)
    y_label = _line_edit(plot.y_label_text, "pyqtLabGraphYLabelEdit", parent)
    y_units = _line_edit(plot.y_label_units or "", "pyqtLabGraphYUnitsEdit", parent)
    x_mode = _axis_mode_combo(parent, plot.x_axis_mode, "pyqtLabGraphXModeCombo")
    y_mode = _axis_mode_combo(parent, plot.y_axis_mode, "pyqtLabGraphYModeCombo")
    grid = _check_box(plot.grid_visible, "pyqtLabGraphGridCheckbox", parent)
    grid.setToolTip("Shows or hides the plot grid.")
    x_log = _check_box(plot.x_log, "pyqtLabGraphXLogCheckbox", parent)
    x_log.setToolTip("Enables or disables logarithmic scaling on the X axis.")
    y_log = _check_box(plot.y_log, "pyqtLabGraphYLogCheckbox", parent)
    y_log.setToolTip("Enables or disables logarithmic scaling on the Y axis.")
    antialiasing = _check_box(
        plot.antialiasing_enabled,
        "pyqtLabGraphAntialiasingCheckbox",
        parent,
    )
    antialiasing.setToolTip("Smooths plotted lines and markers at the cost of rendering speed.")
    downsampling = _check_box(
        plot.downsampling_enabled,
        "pyqtLabGraphDownsamplingCheckbox",
        parent,
    )
    downsampling.setToolTip("Lets pyqtgraph reduce dense visible data before drawing.")
    clip_to_view = _check_box(
        plot.clip_to_view_enabled,
        "pyqtLabGraphClipToViewCheckbox",
        parent,
    )
    clip_to_view.setToolTip("Draws only the data that intersects the current visible X range.")
    adaptive_performance = _check_box(
        plot.adaptive_performance_enabled,
        "pyqtLabGraphAdaptivePerformanceCheckbox",
        parent,
    )
    adaptive_performance.setToolTip(
        "Temporarily hides markers and disables anti-aliasing when many points are visible."
    )
    plot_background = QComboBox(parent)
    plot_background.setObjectName("pyqtLabGraphPlotBackgroundCombo")
    for theme in plot.style_registry.themes:
        name = theme.name
        plot_background.addItem(_THEME_LABELS.get(name, name.title()), name)
    plot_background.setCurrentIndex(max(plot_background.findData(plot.theme.name), 0))
    plot_style = QComboBox(parent)
    plot_style.setObjectName("pyqtLabGraphPlotStyleCombo")
    for registered_plot_style in plot.style_registry.plot_styles:
        name = registered_plot_style.name
        plot_style.addItem(_PLOT_STYLE_LABELS.get(name, name.title()), name)
    plot_style.setCurrentIndex(max(plot_style.findData(plot.plot_style.name), 0))
    restore_view = _check_box(True, "pyqtLabGraphRestoreViewStateOnLoadCheckbox", parent)
    restore_view.setToolTip(
        "Restores saved zoom, autoscale, and rolling-range state when loading this layout."
    )

    xmin, xmax = plot.get_x_range()
    ymin, ymax = plot.get_y_range()
    x_min = _range_spin_box(xmin, "pyqtLabGraphXMinSpin", parent)
    x_max = _range_spin_box(xmax, "pyqtLabGraphXMaxSpin", parent)
    y_min = _range_spin_box(ymin, "pyqtLabGraphYMinSpin", parent)
    y_max = _range_spin_box(ymax, "pyqtLabGraphYMaxSpin", parent)
    preview_x = QPushButton("Preview Range", parent)
    preview_x.setObjectName("pyqtLabGraphPreviewXRangeButton")
    preview_y = QPushButton("Preview Range", parent)
    preview_y.setObjectName("pyqtLabGraphPreviewYRangeButton")

    tab = QWidget(parent)
    layout = QVBoxLayout(tab)
    axes_group, axes_layout = _form_group("Axes", "pyqtLabGraphAxesGroup", tab)
    for label, control in (
        ("X label:", x_label), ("X units:", x_units), ("X mode:", x_mode),
        ("X logarithmic:", x_log), ("Y label:", y_label), ("Y units:", y_units),
        ("Y mode:", y_mode), ("Y logarithmic:", y_log),
    ):
        axes_layout.addRow(label, control)
    layout.addWidget(axes_group)
    ranges_group, ranges_layout = _form_group(
        "View ranges", "pyqtLabGraphViewRangesGroup", tab
    )
    ranges_layout.addRow("X range:", _range_row(x_min, x_max, preview_x))
    ranges_layout.addRow("Y range:", _range_row(y_min, y_max, preview_y))
    layout.addWidget(ranges_group)
    appearance_group, appearance_layout = _form_group(
        "Appearance", "pyqtLabGraphAppearanceGroup", tab
    )
    appearance_layout.addRow("Plot background:", plot_background)
    appearance_layout.addRow("Plot style:", plot_style)
    appearance_layout.addRow("Grid:", grid)
    layout.addWidget(appearance_group)
    rendering_group, rendering_layout = _form_group(
        "Rendering", "pyqtLabGraphRenderingGroup", tab
    )
    rendering_layout.addRow("Anti-aliasing:", antialiasing)
    rendering_layout.addRow("Downsampling:", downsampling)
    rendering_layout.addRow("Clip to view:", clip_to_view)
    rendering_layout.addRow("Adaptive rendering:", adaptive_performance)
    layout.addWidget(rendering_group)
    saving_group, saving_layout = _form_group(
        "Layout saving", "pyqtLabGraphLayoutSavingGroup", tab
    )
    saving_layout.addRow("Restore view on load:", restore_view)
    layout.addWidget(saving_group)
    layout.addStretch(1)
    tabs.addTab(tab, "Global")
    return GlobalControls(
        x_label, x_units, y_label, y_units, x_mode, y_mode, grid, antialiasing,
        downsampling, clip_to_view, adaptive_performance, plot_background, plot_style,
        restore_view, x_min, x_max, preview_x, y_min, y_max, preview_y, x_log, y_log,
    )


def build_curve_tabs(
    plot: PyQtLabGraphWidget,
    parent: QWidget,
    tabs: QTabWidget,
    choose_color: Callable[[str], None],
) -> dict[str, CurveStyleEditor]:
    editors: dict[str, CurveStyleEditor] = {}
    for key, curve_label in plot.curve_choices():
        style = plot.curve_style(key)
        tab = QWidget(parent)
        layout = QVBoxLayout(tab)
        visible = _check_box(
            plot.curve_visible(key),
            f"pyqtLabGraphCurveVisible_{key}",
            tab,
        )
        line_enabled = _check_box(
            style.line_enabled, f"pyqtLabGraphCurveLineEnabled_{key}", tab
        )
        line_color_button = QPushButton(tab)
        line_color_button.setObjectName(f"pyqtLabGraphCurveLineColor_{key}")
        line_color = QColor(style.line_color)
        set_color_button_style(line_color_button, line_color, plot.theme)
        line_width = QDoubleSpinBox(tab)
        line_width.setObjectName(f"pyqtLabGraphCurveLineWidth_{key}")
        _configure_line_width_spin_box(line_width)
        line_width.setValue(style.line_width)
        marker_enabled = _check_box(
            style.marker_enabled, f"pyqtLabGraphCurveMarkerEnabled_{key}", tab
        )
        marker_filled = _check_box(
            style.marker_filled, f"pyqtLabGraphCurveMarkerFilled_{key}", tab
        )
        marker_symbol = QComboBox(tab)
        marker_symbol.setObjectName(f"pyqtLabGraphCurveMarkerSymbol_{key}")
        for marker_label, symbol in _MARKER_OPTIONS:
            marker_symbol.addItem(marker_label, symbol)
        marker_symbol.setCurrentIndex(max(marker_symbol.findData(style.marker_symbol), 0))
        marker_size = QSpinBox(tab)
        marker_size.setObjectName(f"pyqtLabGraphCurveMarkerSize_{key}")
        marker_size.setRange(_MARKER_SIZE_MINIMUM, _MARKER_SIZE_MAXIMUM)
        marker_size.setValue(style.marker_size)
        outline = QDoubleSpinBox(tab)
        outline.setObjectName(f"pyqtLabGraphCurveMarkerOutlineWidth_{key}")
        _configure_marker_outline_width_spin_box(outline)
        outline.setValue(style.marker_outline_width)
        editor = CurveStyleEditor(
            visible, line_enabled, line_color, line_color_button, line_width,
            marker_enabled, marker_filled, marker_symbol, marker_size, outline,
        )
        editors[key] = editor
        line_color_button.clicked.connect(
            lambda _checked=False, curve_key=key: choose_color(curve_key)
        )
        curve_group, curve_layout = _form_group(
            "Curve", f"pyqtLabGraphCurveGroup_{key}", tab
        )
        curve_layout.addRow("Visibility:", visible)
        layout.addWidget(curve_group)
        line_group, line_layout = _form_group(
            "Line", f"pyqtLabGraphCurveLineGroup_{key}", tab
        )
        line_layout.addRow("Line:", line_enabled)
        line_layout.addRow("Line color:", line_color_button)
        line_layout.addRow("Line width:", line_width)
        layout.addWidget(line_group)
        marker_group, marker_layout = _form_group(
            "Markers", f"pyqtLabGraphCurveMarkersGroup_{key}", tab
        )
        marker_layout.addRow("Markers:", marker_enabled)
        marker_layout.addRow("Marker shape:", marker_symbol)
        marker_layout.addRow("Marker size:", marker_size)
        marker_layout.addRow("Filled markers:", marker_filled)
        marker_layout.addRow("Marker outline width:", outline)
        layout.addWidget(marker_group)
        layout.addStretch(1)
        tabs.addTab(tab, curve_label)
    return editors


def optional_text(line_edit: QLineEdit) -> str | None:
    return line_edit.text().strip() or None


def set_color_button_style(
    button: QPushButton,
    color: QColor,
    theme: PyQtLabGraphTheme,
) -> None:
    button.setText(color.name())
    text_color = (
        _COLOR_BUTTON_LIGHT_TEXT
        if color.lightness() < _COLOR_BUTTON_LIGHTNESS_THRESHOLD
        else _COLOR_BUTTON_DARK_TEXT
    )
    vertical, horizontal = _COLOR_BUTTON_PADDING
    button.setStyleSheet(
        f"background-color: {color.name()}; color: {text_color}; "
        f"border: {_COLOR_BUTTON_BORDER_WIDTH}px solid {theme.border}; "
        f"border-radius: {_COLOR_BUTTON_BORDER_RADIUS}px; "
        f"padding: {vertical}px {horizontal}px;"
    )


def _line_edit(text: str, name: str, parent: QWidget) -> QLineEdit:
    control = QLineEdit(text, parent)
    control.setObjectName(name)
    return control


def _check_box(checked: bool, name: str, parent: QWidget) -> QCheckBox:
    control = QCheckBox(parent)
    control.setObjectName(name)
    control.setChecked(checked)
    return control


def _axis_mode_combo(parent: QWidget, mode: AxisMode, name: str) -> QComboBox:
    combo = QComboBox(parent)
    combo.setObjectName(name)
    combo.addItem("Auto (SI)", AxisMode.AUTO)
    combo.addItem("Linear (Raw)", AxisMode.LINEAR)
    combo.addItem("Time (h:min:s)", AxisMode.TIME)
    combo.setCurrentIndex(combo.findData(mode))
    return combo


def _range_spin_box(value: float, name: str, parent: QWidget) -> QDoubleSpinBox:
    spin = QDoubleSpinBox(parent)
    spin.setObjectName(name)
    spin.setRange(_RANGE_SPIN_MINIMUM, _RANGE_SPIN_MAXIMUM)
    spin.setDecimals(_RANGE_SPIN_DECIMALS)
    spin.setValue(value)
    return spin


def _configure_line_width_spin_box(spin: QDoubleSpinBox) -> None:
    spin.setRange(_LINE_WIDTH_MINIMUM, _LINE_WIDTH_MAXIMUM)
    spin.setDecimals(_LINE_WIDTH_DECIMALS)
    spin.setSingleStep(_LINE_WIDTH_STEP)


def _configure_marker_outline_width_spin_box(spin: QDoubleSpinBox) -> None:
    spin.setRange(_MARKER_OUTLINE_WIDTH_MINIMUM, _MARKER_OUTLINE_WIDTH_MAXIMUM)
    spin.setDecimals(_MARKER_OUTLINE_WIDTH_DECIMALS)
    spin.setSingleStep(_MARKER_OUTLINE_WIDTH_STEP)


def _form_group(title: str, name: str, parent: QWidget) -> tuple[QGroupBox, QFormLayout]:
    group = QGroupBox(title, parent)
    group.setObjectName(name)
    return group, QFormLayout(group)


def _range_row(
    minimum: QDoubleSpinBox,
    maximum: QDoubleSpinBox,
    button: QPushButton,
) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(*_ROW_LAYOUT_MARGINS)
    layout.addWidget(QLabel("Min"))
    layout.addWidget(minimum)
    layout.addWidget(QLabel("Max"))
    layout.addWidget(maximum)
    layout.addWidget(button)
    return widget
