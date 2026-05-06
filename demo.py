from __future__ import annotations

import sys
import time
from math import sin
from pathlib import Path
from random import uniform
from typing import TypeVar

from PySide6.QtCore import QFile, QObject, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QCheckBox, QMainWindow, QPushButton, QWidget

from pyqt_lab_graph import PyQtLabGraphWidget


WidgetType = TypeVar("WidgetType", bound=QWidget)


class ThermostatDemoWindow(QObject):
    """Loads the Qt Designer UI and demonstrates the reusable PyQtGraph live plot."""

    def __init__(self, ui_path: Path) -> None:
        super().__init__()
        self.window = self._load_ui(ui_path)
        self.plot_container = self._find_required_widget("matplotlibContainer")
        self.toolbar_container = self._find_required_widget("toolbarContainer")
        self.legend_container = self._find_required_widget("legendContainer")
        self.start_button = self._find_required_widget("StartButton", QPushButton)
        self.stop_button = self._find_required_widget("StopButton", QPushButton)
        self.dark_mode_checkbox = self._find_required_widget("DarkModeCheckBox", QCheckBox)

        self.live_plot = PyQtLabGraphWidget(
            self.plot_container,
            self.toolbar_container,
            self.legend_container,
            show_toolbar=True,
            rolling_window_seconds=300.0,
            legend_orientation=Qt.Orientation.Horizontal,
        )
        self.live_plot.set_axis_labels("Messzeit", "Temperatur", "s", "deg C", x_mode="time", y_mode="linear")
        self.live_plot.add_curve(
            "process_temperature",
            label="Prozesstemperatur",
            color="#1f77b4",
            style={"marker_symbol": "o", "marker_size": 5},
        )
        self.live_plot.add_curve(
            "bath_temperature",
            label="Badtemperatur",
            color="#ff7f0e",
            style={"marker_symbol": "s", "marker_size": 5, "marker_filled": False},
        )

        self.accumulated_elapsed_seconds = 0.0
        self.acquisition_start_time: float | None = None

        self.live_timer = QTimer(self)
        self.live_timer.setInterval(1000)
        self.live_timer.timeout.connect(self.add_simulated_measurements)
        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button.clicked.connect(self.stop_acquisition)
        self.dark_mode_checkbox.toggled.connect(self.set_dark_mode_enabled)
        self.set_dark_mode_enabled(False)
        self._set_acquisition_running(False)

    def show(self) -> None:
        self.window.show()

    def start_acquisition(self) -> None:
        if not self.live_timer.isActive():
            self.acquisition_start_time = time.monotonic()
            self.live_timer.start()
            self.add_simulated_measurements()
        self._set_acquisition_running(True)

    def stop_acquisition(self) -> None:
        self.live_timer.stop()
        if self.acquisition_start_time is not None:
            self.accumulated_elapsed_seconds = self.get_current_elapsed_seconds()
            self.acquisition_start_time = None
        self._set_acquisition_running(False)

    def get_current_elapsed_seconds(self) -> float:
        if self.acquisition_start_time is None:
            return self.accumulated_elapsed_seconds
        return self.accumulated_elapsed_seconds + (
            time.monotonic() - self.acquisition_start_time
        )

    def add_simulated_measurements(self) -> None:
        elapsed = self.get_current_elapsed_seconds()
        process_temperature = 22.0 + 0.8 * sin(elapsed / 35.0)
        process_temperature += 0.2 * sin(elapsed / 7.0) + uniform(-0.05, 0.05)
        bath_temperature = 21.5 + 0.45 * sin((elapsed + 18.0) / 48.0)
        bath_temperature += 0.12 * sin(elapsed / 11.0) + uniform(-0.035, 0.035)
        self.live_plot.add_point("process_temperature", elapsed, process_temperature)
        self.live_plot.add_point("bath_temperature", elapsed, bath_temperature)

    def _set_acquisition_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

    def set_dark_mode_enabled(self, enabled: bool) -> None:
        self.live_plot.set_dark_mode_enabled(enabled)
        if enabled:
            colors = {
                "window": "#1b1f24",
                "panel": "#1f2329",
                "border": "#3a4048",
                "text": "#d8dee9",
                "button": "#272c33",
                "button_hover": "#343b44",
                "button_disabled": "#1b1f24",
                "button_disabled_text": "#6b7280",
            }
        else:
            colors = {
                "window": "#f3f4f6",
                "panel": "#f3f4f6",
                "border": "#c8ced6",
                "text": "#202124",
                "button": "#f8fafc",
                "button_hover": "#e5e7eb",
                "button_disabled": "#e5e7eb",
                "button_disabled_text": "#9ca3af",
            }

        self.window.setStyleSheet(
            f"""
            QMainWindow,
            QWidget#centralwidget {{
                background-color: {colors['window']};
                color: {colors['text']};
            }}
            QGroupBox {{
                background-color: {colors['panel']};
                color: {colors['text']};
                border: 1px solid {colors['border']};
                border-radius: 6px;
                margin-top: 8px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
            QPushButton,
            QCheckBox {{
                color: {colors['text']};
            }}
            QPushButton {{
                background-color: {colors['button']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: {colors['button_hover']};
            }}
            QPushButton:disabled {{
                background-color: {colors['button_disabled']};
                color: {colors['button_disabled_text']};
            }}
            QMenuBar,
            QStatusBar {{
                background-color: {colors['window']};
                color: {colors['text']};
            }}
            """
        )

    def _load_ui(self, ui_path: Path) -> QMainWindow:
        if not ui_path.exists():
            raise FileNotFoundError(f"Qt Designer UI file not found: {ui_path}")

        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.ReadOnly):
            raise RuntimeError(f"Could not open Qt Designer UI file: {ui_path}")

        try:
            loaded_widget = QUiLoader().load(ui_file)
        finally:
            ui_file.close()

        if loaded_widget is None:
            raise RuntimeError(f"Could not load Qt Designer UI file: {ui_path}")
        if not isinstance(loaded_widget, QMainWindow):
            raise TypeError(
                f"Expected top-level QMainWindow in {ui_path}, "
                f"got {type(loaded_widget).__name__}."
            )
        return loaded_widget

    def _find_required_widget(
        self,
        object_name: str,
        widget_type: type[WidgetType] = QWidget,
    ) -> WidgetType:
        widget = self.window.findChild(widget_type, object_name)
        if widget is None:
            raise RuntimeError(
                f'Required {widget_type.__name__} "{object_name}" was not found in maingui.ui. '
                "Please check the objectName in Qt Designer."
            )
        return widget


AutoPlotterWindow = ThermostatDemoWindow


def main() -> int:
    app = QApplication(sys.argv)
    ui_path = Path(__file__).resolve().parent / "maingui.ui"
    window = ThermostatDemoWindow(ui_path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
