from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPaintEvent, QPalette, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QMenu,
    QToolBar,
    QToolButton,
    QWidget,
)

from .models import InteractionState, InteractionTool
from .qt_styles import paint_host_frame

if TYPE_CHECKING:
    from .widget import PyQtLabGraphWidget

_TOOLBAR_ICON_SIZE = 24

_ROLLING_CUSTOM_MINIMUM = 1e-6
_ROLLING_CUSTOM_MAXIMUM = 1_000_000_000.0
_ROLLING_CUSTOM_DECIMALS = 6
_ROLLING_CUSTOM_DEFAULT = 100.0
_ROLLING_PRESET_SHORT = 100.0
_ROLLING_PRESET_LONG = 1000.0
_ROLLING_PRESET_SHORT_LABEL = f"{_ROLLING_PRESET_SHORT:g} X units"
_ROLLING_PRESET_LONG_LABEL = f"{_ROLLING_PRESET_LONG:,.0f} X units"


class PyQtLabGraphToolbar(QToolBar):
    """PyQtGraph toolbar for PyQtLabGraphWidget."""

    def __init__(
        self,
        plot: PyQtLabGraphWidget,
        *,
        parent: QWidget | None = None,
        show_frame: bool = True,
    ) -> None:
        super().__init__(parent)
        self.plot = plot
        self._show_frame = show_frame
        self.setObjectName("pyqtLabGraphToolbar")
        if show_frame:
            self.setContentsMargins(4, 4, 4, 4)
        self._themed_icon_actions: list[tuple[QAction, str]] = []

        self.setMovable(False)
        self.setIconSize(QPixmap(_TOOLBAR_ICON_SIZE, _TOOLBAR_ICON_SIZE).size())

        self.show_all_action = self._add_action("reset_zoom.png", "Show All", self.show_all)
        self.zoom_action = self._add_action("zoom_area.png", "Zoom", self.zoom, checkable=True)
        self.addSeparator()
        self.x_zoom_action = self._add_action(
            "x-zoom.png",
            "X-Zoom",
            self.set_x_zoom_enabled,
            checkable=True,
        )
        self.y_zoom_action = self._add_action(
            "y-zoom.png",
            "Y-Zoom",
            self.set_y_zoom_enabled,
            checkable=True,
        )
        self.addSeparator()
        self.autoscale_x_action = self._add_action(
            "autox.png",
            "Autoscale X",
            self._autoscale_x_toggled,
            checkable=True,
        )
        self.autoscale_x_action.blockSignals(True)
        self.autoscale_x_action.setChecked(True)
        self.autoscale_x_action.blockSignals(False)
        self.autoscale_y_action = self._add_action(
            "autoy.png",
            "Autoscale Y",
            self._autoscale_y_toggled,
            checkable=True,
        )
        self.autoscale_y_action.blockSignals(True)
        self.autoscale_y_action.setChecked(True)
        self.autoscale_y_action.blockSignals(False)
        self.rolling_button = self._create_rolling_button()
        self.addWidget(self.rolling_button)
        self.addSeparator()
        self.customize_action = self._add_action("edit_params.png", "Customize", self.customize)
        self.save_action = self._add_action("saveplot.png", "Save", self.save_figure)
        self.plot.interaction_state_changed.connect(self.sync_state)
        self.plot.state_reset.connect(
            lambda: self.sync_state(self.plot.interaction_state)
        )
        self.sync_state(self.plot.interaction_state)

    def show_all(self) -> None:
        self.plot.request_show_all()

    def zoom(self, enabled: bool) -> None:
        self._request_tool(InteractionTool.RECT_ZOOM, enabled)

    def customize(self) -> None:
        self.plot.show_customize_dialog()

    def save_figure(self) -> None:
        self.plot.save_figure()

    def set_x_zoom_enabled(self, enabled: bool) -> None:
        self._request_tool(InteractionTool.X_ZOOM, enabled)

    def set_y_zoom_enabled(self, enabled: bool) -> None:
        self._request_tool(InteractionTool.Y_ZOOM, enabled)

    def sync_state(self, state: InteractionState) -> None:
        self._set_checked(self.autoscale_x_action, state.autoscale_x)
        self._set_checked(self.autoscale_y_action, state.autoscale_y)
        self._set_checked(self.rolling_button, state.rolling_x)
        self._set_checked(self.zoom_action, state.active_tool == InteractionTool.RECT_ZOOM)
        self._set_checked(self.x_zoom_action, state.active_tool == InteractionTool.X_ZOOM)
        self._set_checked(self.y_zoom_action, state.active_tool == InteractionTool.Y_ZOOM)

    def refresh_icons(self) -> None:
        if not hasattr(self, "_themed_icon_actions"):
            return
        for action, icon_filename in self._themed_icon_actions:
            action.setIcon(self._themed_icon(icon_filename))
        if hasattr(self, "rolling_button"):
            self.rolling_button.setIcon(self._themed_icon("rolling.png"))

    def event(self, event: QEvent) -> bool:
        handled = super().event(event)
        if event.type() in {
            QEvent.Type.ApplicationPaletteChange,
            QEvent.Type.PaletteChange,
            QEvent.Type.StyleChange,
        }:
            self.refresh_icons()
        return handled

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        if self._show_frame:
            paint_host_frame(self)

    def _autoscale_x_toggled(self, enabled: bool) -> None:
        self.plot.request_autoscale_x(enabled)

    def _autoscale_y_toggled(self, enabled: bool) -> None:
        self.plot.request_autoscale_y(enabled)

    def _rolling_toggled(self, enabled: bool) -> None:
        if enabled:
            self._select_current_x_rolling_window()
        self.plot.request_rolling_x(enabled)

    def _enable_rolling_window(self, size: float) -> None:
        self.plot.set_rolling_window_size(size)
        self.plot.request_rolling_x(True)

    def _select_current_x_rolling_window(self) -> None:
        self.plot.set_rolling_window_size(self.plot.get_current_x_window_size())

    def _enable_current_x_rolling_window(self) -> None:
        self._enable_rolling_window(self.plot.get_current_x_window_size())

    def _enable_custom_rolling_window(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Rolling Window")
        spin_box = QDoubleSpinBox(dialog)
        spin_box.setRange(_ROLLING_CUSTOM_MINIMUM, _ROLLING_CUSTOM_MAXIMUM)
        spin_box.setDecimals(_ROLLING_CUSTOM_DECIMALS)
        spin_box.setValue(self.plot.get_current_x_window_size())
        layout = QFormLayout(dialog)
        layout.addRow("X range width:", spin_box)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            dialog,
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._enable_rolling_window(spin_box.value())

    def _create_rolling_button(self) -> QToolButton:
        button = QToolButton(self)
        button.setObjectName("pyqtLabGraphRollingButton")
        button.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        button.setText("Rolling")
        button.setIcon(self._themed_icon("rolling.png"))
        button.setToolTip("Rolling X range")
        button.setCheckable(True)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        button.toggled.connect(self._rolling_toggled)
        menu = QMenu(button)
        menu.setObjectName("pyqtLabGraphRollingMenu")
        menu.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        current_x_action = QAction("Current X range", menu)
        current_x_action.triggered.connect(self._enable_current_x_rolling_window)
        menu.addAction(current_x_action)
        short_range_action = QAction(_ROLLING_PRESET_SHORT_LABEL, menu)
        short_range_action.triggered.connect(
            lambda: self._enable_rolling_window(_ROLLING_PRESET_SHORT)
        )
        menu.addAction(short_range_action)
        long_range_action = QAction(_ROLLING_PRESET_LONG_LABEL, menu)
        long_range_action.triggered.connect(
            lambda: self._enable_rolling_window(_ROLLING_PRESET_LONG)
        )
        menu.addAction(long_range_action)
        custom_action = QAction("Custom", menu)
        custom_action.triggered.connect(self._enable_custom_rolling_window)
        menu.addAction(custom_action)
        button.setMenu(menu)
        return button

    def _request_tool(self, tool: InteractionTool, enabled: bool) -> None:
        self.plot.request_tool(tool, enabled)

    @staticmethod
    def _set_checked(action: QAction | QToolButton, checked: bool) -> None:
        action.blockSignals(True)
        action.setChecked(checked)
        action.blockSignals(False)

    def _add_action(
        self,
        icon_filename: str,
        text: str,
        slot: Callable,
        checkable: bool = False,
    ) -> QAction:
        icon = self._themed_icon(icon_filename)
        action = QAction(icon, text, self)
        action.setToolTip(text)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(slot)
        else:
            action.triggered.connect(slot)
        self.addAction(action)
        button = self.widgetForAction(action)
        if button is not None:
            button.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        if icon_filename:
            self._themed_icon_actions.append((action, icon_filename))
        return action

    def _themed_icon(self, filename: str) -> QIcon:
        icon_color = self.palette().color(QPalette.ColorRole.ButtonText)
        return self._recolored_png_icon(filename, icon_color)

    @staticmethod
    def _recolored_png_icon(filename: str, color: QColor) -> QIcon:
        icon_path = Path(__file__).resolve().parent / "assets" / filename
        source = QPixmap(str(icon_path))
        if source.isNull():
            return QIcon()
        recolored = QPixmap(source.size())
        recolored.setDevicePixelRatio(source.devicePixelRatio())
        recolored.fill(Qt.GlobalColor.transparent)
        painter = QPainter(recolored)
        painter.drawPixmap(0, 0, source)
        painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        painter.fillRect(recolored.rect(), color)
        painter.end()
        return QIcon(recolored)
