from __future__ import annotations

import sys
import time
from math import sin
from pathlib import Path
from random import uniform
from typing import TypeVar

import numpy as np
from _demo_theme import install_demo_theme_toggle
from PySide6.QtCore import QFile, QObject, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget

from pyqtlabgraph import PyQtLabGraphLegend, PyQtLabGraphToolbar, PyQtLabGraphWidget

WidgetType = TypeVar("WidgetType", bound=QWidget)


class ThermostatDemoWindow(QObject):
    """Loads the Qt Designer UI and demonstrates a reusable thermostat live plot."""

    def __init__(
        self,
        ui_path: Path,
        layout_path: Path | None = None,
    ) -> None:
        super().__init__()
        self.window = self._load_ui(ui_path)
        self.plot_container = self._find_required_widget("plotContainer")
        self.toolbar_container = self._find_required_widget("toolbarContainer")
        self.legend_container = self._find_required_widget("legendContainer")
        self.start_button = self._find_required_widget("startButton", QPushButton)
        self.stop_button = self._find_required_widget("stopButton", QPushButton)
        self.add_points_button = self._find_required_widget("addPointsButton", QPushButton)

        actual_layout_path = layout_path or Path.cwd() / "demo_thermostat.layout.json"

        self.live_plot = PyQtLabGraphWidget(
            plot_identifier="thermostat-live",
            layout_path=actual_layout_path,
            rolling_window_size=300.0,
        )
        self.toolbar = PyQtLabGraphToolbar(self.live_plot)
        self.legend = PyQtLabGraphLegend(
            self.live_plot,
            orientation=Qt.Orientation.Horizontal,
        )
        self._embed(self.plot_container, self.live_plot)
        self._embed(self.toolbar_container, self.toolbar)
        self._embed(self.legend_container, self.legend)
        self.window.setWindowTitle("PyQtLabGraph Thermostat Demo")
        self.live_plot.set_axis_labels("Elapsed time", "Temperature", "s", "deg C", x_mode="time", y_mode="linear")
        self.live_plot.add_curve("process_temperature", label="Process temperature")
        self.live_plot.add_curve("bath_temperature", label="Bath temperature")
        self.live_plot.load_layout()

        self.accumulated_elapsed_seconds = 0.0
        self.acquisition_start_time: float | None = None

        self.live_timer = QTimer(self)
        self.live_timer.setInterval(1000)
        self.live_timer.timeout.connect(self.add_simulated_measurements)
        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button.clicked.connect(self.stop_acquisition)
        self.add_points_button.clicked.connect(self.add_bulk_test_points)
        self._set_acquisition_running(False)
        install_demo_theme_toggle(self.window, self.live_plot)

    @staticmethod
    def _embed(container: QWidget, component: QWidget) -> None:
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(component)

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
        process_temperature, bath_temperature = self._simulated_temperatures(elapsed)
        self.live_plot.add_point("process_temperature", elapsed, process_temperature)
        self.live_plot.add_point("bath_temperature", elapsed, bath_temperature)

    def add_bulk_test_points(self) -> None:
        point_count = 10_000
        start_elapsed = self._latest_plotted_elapsed_seconds()
        process_x = []
        process_y = []
        bath_x = []
        bath_y = []

        for offset in range(1, point_count + 1):
            elapsed = start_elapsed + float(offset)
            process_temperature, bath_temperature = self._simulated_temperatures(elapsed)
            process_x.append(elapsed)
            process_y.append(process_temperature)
            bath_x.append(elapsed)
            bath_y.append(bath_temperature)

        current_process_x, current_process_y = self.live_plot.curve_data("process_temperature")
        current_bath_x, current_bath_y = self.live_plot.curve_data("bath_temperature")
        self.live_plot.set_data(
            "process_temperature",
            np.concatenate((current_process_x, np.array(process_x))),
            np.concatenate((current_process_y, np.array(process_y))),
        )
        self.live_plot.set_data(
            "bath_temperature",
            np.concatenate((current_bath_x, np.array(bath_x))),
            np.concatenate((current_bath_y, np.array(bath_y))),
        )
        self.accumulated_elapsed_seconds = start_elapsed + float(point_count)
        self.acquisition_start_time = time.monotonic() if self.live_timer.isActive() else None

    def _latest_plotted_elapsed_seconds(self) -> float:
        latest_values = []
        for curve_key in ("process_temperature", "bath_temperature"):
            x_values, _y_values = self.live_plot.curve_data(curve_key)
            if len(x_values) > 0:
                latest_values.append(float(np.max(x_values)))
        if latest_values:
            return max(latest_values)
        return self.get_current_elapsed_seconds()

    def _simulated_temperatures(self, elapsed: float) -> tuple[float, float]:
        process_temperature = 22.0 + 0.8 * sin(elapsed / 35.0)
        process_temperature += 0.2 * sin(elapsed / 7.0) + uniform(-0.05, 0.05)
        bath_temperature = 21.5 + 0.45 * sin((elapsed + 18.0) / 48.0)
        bath_temperature += 0.12 * sin(elapsed / 11.0) + uniform(-0.035, 0.035)
        return process_temperature, bath_temperature

    def _set_acquisition_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

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
                f'Required {widget_type.__name__} "{object_name}" was not found in demo_thermostat.ui. '
                "Please check the objectName in Qt Designer."
            )
        return widget


def main() -> int:
    app = QApplication(sys.argv)
    ui_path = Path(__file__).resolve().parent / "demo_thermostat.ui"
    window = ThermostatDemoWindow(ui_path)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
