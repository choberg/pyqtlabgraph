from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPalette, QPixmap
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
        parent: QWidget | None = None,
        on_tool_requested: Callable[[InteractionTool, bool], None] | None = None,
        on_autoscale_x_requested: Callable[[bool], None] | None = None,
        on_autoscale_y_requested: Callable[[bool], None] | None = None,
        on_rolling_requested: Callable[[bool], None] | None = None,
        on_rolling_window_selected: Callable[[float], None] | None = None,
        get_current_x_window_size: Callable[[], float] | None = None,
        on_show_all_requested: Callable[[], None] | None = None,
        on_save_requested: Callable[[], None] | None = None,
        on_customize_requested: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pyqtLabGraphToolbar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setStyleSheet(
            "QToolBar#pyqtLabGraphToolbar { background: transparent; border: none; }"
        )
        self.on_tool_requested = on_tool_requested
        self.on_autoscale_x_requested = on_autoscale_x_requested
        self.on_autoscale_y_requested = on_autoscale_y_requested
        self.on_rolling_requested = on_rolling_requested
        self.on_rolling_window_selected = on_rolling_window_selected
        self.get_current_x_window_size = get_current_x_window_size
        self.on_show_all_requested = on_show_all_requested
        self.on_save_requested = on_save_requested
        self.on_customize_requested = on_customize_requested
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

    def show_all(self) -> None:
        if self.on_show_all_requested is not None:
            self.on_show_all_requested()

    def zoom(self, enabled: bool) -> None:
        self._request_tool(InteractionTool.RECT_ZOOM, enabled)

    def customize(self) -> None:
        if self.on_customize_requested is not None:
            self.on_customize_requested()

    def save_figure(self) -> None:
        if self.on_save_requested is not None:
            self.on_save_requested()

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

    def _autoscale_x_toggled(self, enabled: bool) -> None:
        if self.on_autoscale_x_requested is not None:
            self.on_autoscale_x_requested(enabled)

    def _autoscale_y_toggled(self, enabled: bool) -> None:
        if self.on_autoscale_y_requested is not None:
            self.on_autoscale_y_requested(enabled)

    def _rolling_toggled(self, enabled: bool) -> None:
        if enabled:
            self._select_current_x_rolling_window()
        if self.on_rolling_requested is not None:
            self.on_rolling_requested(enabled)

    def _enable_rolling_window(self, size: float) -> None:
        if self.on_rolling_window_selected is not None:
            self.on_rolling_window_selected(size)
        if self.on_rolling_requested is not None:
            self.on_rolling_requested(True)

    def _select_current_x_rolling_window(self) -> None:
        if (
            self.get_current_x_window_size is not None
            and self.on_rolling_window_selected is not None
        ):
            self.on_rolling_window_selected(self.get_current_x_window_size())

    def _enable_current_x_rolling_window(self) -> None:
        if self.get_current_x_window_size is not None:
            self._enable_rolling_window(self.get_current_x_window_size())

    def _enable_custom_rolling_window(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Rolling Window")
        spin_box = QDoubleSpinBox(dialog)
        spin_box.setRange(_ROLLING_CUSTOM_MINIMUM, _ROLLING_CUSTOM_MAXIMUM)
        spin_box.setDecimals(_ROLLING_CUSTOM_DECIMALS)
        if self.get_current_x_window_size is not None:
            spin_box.setValue(self.get_current_x_window_size())
        else:
            spin_box.setValue(_ROLLING_CUSTOM_DEFAULT)
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
        if self.on_tool_requested is not None:
            self.on_tool_requested(tool, enabled)

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
