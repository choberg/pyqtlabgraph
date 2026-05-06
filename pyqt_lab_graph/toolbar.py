from __future__ import annotations

from pathlib import Path
from typing import Callable

import pyqtgraph as pg
from PySide6.QtCore import QEvent, QObject, QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QMenu,
    QRubberBand,
    QToolBar,
    QToolButton,
    QWidget,
)


class AxisSpanZoomFilter(QObject):
    """Rubber-band span selection for one-shot X/Y zoom actions."""

    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        direction: str,
        on_selected: Callable[[float, float], None],
        parent: QObject,
    ) -> None:
        super().__init__(parent)
        self.plot_widget = plot_widget
        self.viewport_widget = plot_widget.viewport()
        self.direction = direction
        self.on_selected = on_selected
        self.enabled = False
        self.origin = QPoint()
        self.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, self.viewport_widget)
        self.viewport_widget.installEventFilter(self)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self.rubber_band.hide()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is not self.viewport_widget or not self.enabled:
            return False

        if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            self.rubber_band.setGeometry(QRect(self.origin, self.origin))
            self.rubber_band.show()
            return True

        if event.type() == QEvent.Type.MouseMove and self.rubber_band.isVisible():
            current = event.position().toPoint()
            if self.direction == "x":
                top_left = QPoint(min(self.origin.x(), current.x()), 0)
                bottom_right = QPoint(max(self.origin.x(), current.x()), self.viewport_widget.height())
            else:
                top_left = QPoint(0, min(self.origin.y(), current.y()))
                bottom_right = QPoint(self.viewport_widget.width(), max(self.origin.y(), current.y()))
            self.rubber_band.setGeometry(QRect(top_left, bottom_right).normalized())
            return True

        if event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
            if self.rubber_band.isVisible():
                self.rubber_band.hide()
                current = event.position().toPoint()
                start_value = self._map_view_value(self.origin)
                end_value = self._map_view_value(current)
                self.on_selected(start_value, end_value)
            return True

        return False

    def _map_view_value(self, point: QPoint) -> float:
        scene_point = self.plot_widget.mapToScene(point)
        view_point = self.plot_widget.getPlotItem().getViewBox().mapSceneToView(scene_point)
        return float(view_point.x() if self.direction == "x" else view_point.y())


class PyQtLabGraphToolbar(QToolBar):
    """PyQtGraph toolbar for PyQtLabGraphWidget."""

    def __init__(
        self,
        plot_widget: pg.PlotWidget,
        parent: QWidget | None = None,
        on_x_span_selected: Callable[[float, float], None] | None = None,
        on_y_span_selected: Callable[[float, float], None] | None = None,
        on_autoscale_x_changed: Callable[[bool], None] | None = None,
        on_autoscale_y_changed: Callable[[bool], None] | None = None,
        on_rolling_changed: Callable[[bool], None] | None = None,
        on_rolling_window_selected: Callable[[float], None] | None = None,
        get_current_x_window_seconds: Callable[[], float] | None = None,
        on_home_requested: Callable[[], None] | None = None,
        on_manual_navigation_started: Callable[[], None] | None = None,
        on_customize_requested: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.plot_widget = plot_widget
        self.on_x_span_selected = on_x_span_selected
        self.on_y_span_selected = on_y_span_selected
        self.on_autoscale_x_changed = on_autoscale_x_changed
        self.on_autoscale_y_changed = on_autoscale_y_changed
        self.on_rolling_changed = on_rolling_changed
        self.on_rolling_window_selected = on_rolling_window_selected
        self.get_current_x_window_seconds = get_current_x_window_seconds
        self.on_home_requested = on_home_requested
        self.on_manual_navigation_started = on_manual_navigation_started
        self.on_customize_requested = on_customize_requested
        self.dark_mode_enabled = False
        self._themed_icon_actions: list[tuple[QAction, str, QIcon | None]] = []

        self.setMovable(False)
        self.setIconSize(QPixmap(24, 24).size())

        self.home_action = self._add_action("reset_zoom.png", "Home", self.home)
        self.pan_action = self._add_action("pan.png", "Pan", self.pan, checkable=True)
        self.zoom_action = self._add_action("zoom_area.png", "Zoom", self.zoom, checkable=True)
        self.addSeparator()
        self.x_zoom_action = self._add_action("x-zoom.png", "X-Zoom", self.set_x_zoom_enabled, checkable=True, fallback_icon=self._create_axis_zoom_icon("x"))
        self.y_zoom_action = self._add_action("y-zoom.png", "Y-Zoom", self.set_y_zoom_enabled, checkable=True, fallback_icon=self._create_axis_zoom_icon("y"))
        self.addSeparator()
        self.autoscale_x_action = self._add_action("autox.png", "Autoscale X", self._autoscale_x_toggled, checkable=True)
        self.autoscale_x_action.blockSignals(True)
        self.autoscale_x_action.setChecked(True)
        self.autoscale_x_action.blockSignals(False)
        self.autoscale_y_action = self._add_action("autoy.png", "Autoscale Y", self._autoscale_y_toggled, checkable=True)
        self.autoscale_y_action.blockSignals(True)
        self.autoscale_y_action.setChecked(True)
        self.autoscale_y_action.blockSignals(False)
        self.rolling_button = self._create_rolling_button()
        self.addWidget(self.rolling_button)
        self.addSeparator()
        self.customize_action = self._add_action("edit_params.png", "Customize", self.customize)
        self.save_action = self._add_action("saveplot.png", "Save", self.save_figure)
        self.x_span_filter = AxisSpanZoomFilter(plot_widget, "x", self._apply_x_zoom, self)
        self.y_span_filter = AxisSpanZoomFilter(plot_widget, "y", self._apply_y_zoom, self)

    def home(self) -> None:
        self._disable_custom_zoom_actions()
        self.pan_action.setChecked(False)
        self.zoom_action.setChecked(False)
        self._set_mouse_mode(pg.ViewBox.PanMode)
        self.set_rolling_checked(False)
        self.set_autoscale_x_checked(True)
        self.set_autoscale_y_checked(True)
        if self.on_home_requested is not None:
            self.on_home_requested()

    def pan(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self._disable_custom_zoom_actions()
            self.zoom_action.setChecked(False)
            self._set_mouse_mode(pg.ViewBox.PanMode)

    def zoom(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self._disable_custom_zoom_actions()
            self.pan_action.setChecked(False)
            self._set_mouse_mode(pg.ViewBox.RectMode)
        else:
            self._set_mouse_mode(pg.ViewBox.PanMode)

    def customize(self) -> None:
        if self.on_customize_requested is not None:
            self.on_customize_requested()

    def save_figure(self) -> None:
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            "Save plot",
            str(Path.cwd() / "plot.png"),
            "PNG Images (*.png);;All Files (*)",
        )
        if not filename:
            return
        try:
            import pyqtgraph.exporters
            exporter = pyqtgraph.exporters.ImageExporter(self.plot_widget.getPlotItem())
            exporter.export(filename)
        except Exception as exc:
            raise RuntimeError(f"Could not save PyQtGraph plot to {filename}: {exc}") from exc

    def set_x_zoom_enabled(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self.y_zoom_action.setChecked(False)
            self.pan_action.setChecked(False)
            self.zoom_action.setChecked(False)
        self.x_span_filter.set_enabled(enabled)

    def set_y_zoom_enabled(self, enabled: bool) -> None:
        if enabled:
            self._notify_manual_navigation_started()
            self.x_zoom_action.setChecked(False)
            self.pan_action.setChecked(False)
            self.zoom_action.setChecked(False)
        self.y_span_filter.set_enabled(enabled)

    def set_autoscale_x_checked(self, checked: bool) -> None:
        self.autoscale_x_action.blockSignals(True)
        self.autoscale_x_action.setChecked(checked)
        self.autoscale_x_action.blockSignals(False)

    def set_autoscale_y_checked(self, checked: bool) -> None:
        self.autoscale_y_action.blockSignals(True)
        self.autoscale_y_action.setChecked(checked)
        self.autoscale_y_action.blockSignals(False)

    def set_rolling_checked(self, checked: bool) -> None:
        self.rolling_button.blockSignals(True)
        self.rolling_button.setChecked(checked)
        self.rolling_button.blockSignals(False)

    def mark_manual_navigation_started(self) -> None:
        self.set_autoscale_x_checked(False)
        self.set_autoscale_y_checked(False)
        self.set_rolling_checked(False)

    def set_dark_mode_enabled(self, enabled: bool) -> None:
        self.dark_mode_enabled = enabled
        for action, icon_filename, fallback_icon in self._themed_icon_actions:
            action.setIcon(self._themed_icon(icon_filename, fallback_icon))
        if hasattr(self, "rolling_button"):
            self.rolling_button.setIcon(self._themed_icon("rolling.png"))

    def _apply_x_zoom(self, xmin: float, xmax: float) -> None:
        if xmin != xmax and self.on_x_span_selected is not None:
            self.on_x_span_selected(xmin, xmax)
        self.set_autoscale_x_checked(False)
        self.set_rolling_checked(False)
        self.x_zoom_action.setChecked(False)

    def _apply_y_zoom(self, ymin: float, ymax: float) -> None:
        if ymin != ymax and self.on_y_span_selected is not None:
            self.on_y_span_selected(ymin, ymax)
        self.set_autoscale_y_checked(False)
        self.y_zoom_action.setChecked(False)

    def _autoscale_x_toggled(self, enabled: bool) -> None:
        if enabled:
            self.set_rolling_checked(False)
            if self.on_rolling_changed is not None:
                self.on_rolling_changed(False)
        if self.on_autoscale_x_changed is not None:
            self.on_autoscale_x_changed(enabled)

    def _autoscale_y_toggled(self, enabled: bool) -> None:
        if self.on_autoscale_y_changed is not None:
            self.on_autoscale_y_changed(enabled)

    def _rolling_toggled(self, enabled: bool) -> None:
        if enabled:
            self.set_autoscale_x_checked(False)
            if self.on_autoscale_x_changed is not None:
                self.on_autoscale_x_changed(False)
        if self.on_rolling_changed is not None:
            self.on_rolling_changed(enabled)

    def _enable_rolling_window(self, seconds: float) -> None:
        if self.on_rolling_window_selected is not None:
            self.on_rolling_window_selected(seconds)
        self.set_rolling_checked(True)
        self._rolling_toggled(True)

    def _enable_current_x_rolling_window(self) -> None:
        if self.get_current_x_window_seconds is not None:
            self._enable_rolling_window(self.get_current_x_window_seconds())

    def _enable_custom_rolling_window(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Rolling Window")
        spin_box = QDoubleSpinBox(dialog)
        spin_box.setRange(1.0, 86400.0)
        spin_box.setDecimals(1)
        spin_box.setSuffix(" s")
        spin_box.setValue(300.0)
        layout = QFormLayout(dialog)
        layout.addRow("Seconds:", spin_box)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, dialog)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._enable_rolling_window(spin_box.value())

    def _create_rolling_button(self) -> QToolButton:
        button = QToolButton(self)
        button.setText("Rolling")
        button.setIcon(self._themed_icon("rolling.png"))
        button.setToolTip("Rolling window")
        button.setCheckable(True)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        button.toggled.connect(self._rolling_toggled)
        menu = QMenu(button)
        current_x_action = QAction("Current X", menu)
        current_x_action.triggered.connect(self._enable_current_x_rolling_window)
        menu.addAction(current_x_action)
        five_min_action = QAction("5 min", menu)
        five_min_action.triggered.connect(lambda: self._enable_rolling_window(300.0))
        menu.addAction(five_min_action)
        thirty_min_action = QAction("30 min", menu)
        thirty_min_action.triggered.connect(lambda: self._enable_rolling_window(1800.0))
        menu.addAction(thirty_min_action)
        custom_action = QAction("Custom", menu)
        custom_action.triggered.connect(self._enable_custom_rolling_window)
        menu.addAction(custom_action)
        button.setMenu(menu)
        return button

    def _notify_manual_navigation_started(self) -> None:
        self.mark_manual_navigation_started()
        if self.on_manual_navigation_started is not None:
            self.on_manual_navigation_started()

    def _disable_custom_zoom_actions(self) -> None:
        if self.x_zoom_action.isChecked():
            self.x_zoom_action.setChecked(False)
        if self.y_zoom_action.isChecked():
            self.y_zoom_action.setChecked(False)

    def _set_mouse_mode(self, mode: int) -> None:
        self.plot_widget.getPlotItem().getViewBox().setMouseMode(mode)

    def _add_action(self, icon_filename: str, text: str, slot: Callable, checkable: bool = False, fallback_icon: QIcon | None = None) -> QAction:
        icon = self._themed_icon(icon_filename, fallback_icon)
        action = QAction(icon, text, self)
        action.setToolTip(text)
        action.setCheckable(checkable)
        if checkable:
            action.toggled.connect(slot)
        else:
            action.triggered.connect(slot)
        self.addAction(action)
        if icon_filename:
            self._themed_icon_actions.append((action, icon_filename, fallback_icon))
        return action

    def _themed_icon(self, filename: str, fallback_icon: QIcon | None = None) -> QIcon:
        if not filename:
            return fallback_icon or QIcon()
        icon = self._recolored_png_icon(filename, QColor("#e5e7eb")) if self.dark_mode_enabled else self._png_icon(filename)
        if icon.isNull() and fallback_icon is not None:
            return fallback_icon
        return icon

    @staticmethod
    def _png_icon(filename: str) -> QIcon:
        icon_path = Path(__file__).resolve().parent / "assets" / filename
        return QIcon(str(icon_path))

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

    @staticmethod
    def _create_axis_zoom_icon(axis: str) -> QIcon:
        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame_pen = QPen(QColor("#5f6368"), 1.4)
        accent_color = QColor("#1f77b4") if axis == "x" else QColor("#ff7f0e")
        accent_pen = QPen(accent_color, 2.0)
        marker_pen = QPen(accent_color, 1.2)
        painter.setPen(frame_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(QRectF(4.5, 4.5, 14.0, 14.0))
        painter.setPen(marker_pen)
        if axis == "x":
            painter.drawLine(QPointF(7.0, 6.0), QPointF(7.0, 17.0))
            painter.drawLine(QPointF(17.0, 6.0), QPointF(17.0, 17.0))
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(7.0, 12.0), QPointF(17.0, 12.0))
            painter.drawLine(QPointF(7.0, 12.0), QPointF(10.0, 9.0))
            painter.drawLine(QPointF(7.0, 12.0), QPointF(10.0, 15.0))
            painter.drawLine(QPointF(17.0, 12.0), QPointF(14.0, 9.0))
            painter.drawLine(QPointF(17.0, 12.0), QPointF(14.0, 15.0))
        else:
            painter.drawLine(QPointF(6.0, 7.0), QPointF(17.0, 7.0))
            painter.drawLine(QPointF(6.0, 17.0), QPointF(17.0, 17.0))
            painter.setPen(accent_pen)
            painter.drawLine(QPointF(12.0, 7.0), QPointF(12.0, 17.0))
            painter.drawLine(QPointF(12.0, 7.0), QPointF(9.0, 10.0))
            painter.drawLine(QPointF(12.0, 7.0), QPointF(15.0, 10.0))
            painter.drawLine(QPointF(12.0, 17.0), QPointF(9.0, 14.0))
            painter.drawLine(QPointF(12.0, 17.0), QPointF(15.0, 14.0))
        painter.setFont(QFont("Sans Serif", 7, QFont.Weight.Bold))
        painter.setPen(QPen(accent_color, 1.0))
        painter.drawText(QRectF(14.0, 13.0, 9.0, 9.0), Qt.AlignmentFlag.AlignCenter, axis.upper())
        painter.end()
        return QIcon(pixmap)
