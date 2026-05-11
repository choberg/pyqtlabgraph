from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import TypeVar

import numpy as np
from PySide6.QtCore import QFile, QObject, Qt, QTimer
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QWidget

from pyqt_lab_graph import PyQtLabGraphWidget


WidgetType = TypeVar("WidgetType", bound=QWidget)


class TimeFftDemoWindow(QObject):
    """Loads the Qt Designer UI and demonstrates a time signal with its FFT."""

    sample_rate_hz = 100.0
    samples_per_tick = 10

    def __init__(self, ui_path: Path | None = None) -> None:
        super().__init__()
        self.window = self._load_ui(
            ui_path or Path(__file__).resolve().parent / "demo_time_fft.ui"
        )
        self.start_button = self._find_required_widget("startButton", QPushButton)
        self.stop_button = self._find_required_widget("stopButton", QPushButton)
        self.reset_button = self._find_required_widget("resetButton", QPushButton)

        self.sample_index = 0
        self.time_values = np.array([], dtype=float)
        self.signal_values = np.array([], dtype=float)

        self.time_plot = self._create_plot(
            plot_container_name="timePlotContainer",
            toolbar_container_name="timeToolbarContainer",
            legend_container_name="timeLegendContainer",
            plot_identifier="time-fft-time-domain",
        )
        self.fft_plot = self._create_plot(
            plot_container_name="fftPlotContainer",
            toolbar_container_name="fftToolbarContainer",
            legend_container_name="fftLegendContainer",
            plot_identifier="time-fft-frequency-domain",
        )

        self.time_plot.set_axis_labels(
            "Elapsed time",
            "Amplitude",
            "s",
            "V",
            x_mode="time",
            y_mode="linear",
        )
        self.time_plot.add_curve("input_signal", label="Input signal")
        self.time_plot.load_layout()

        self.fft_plot.set_axis_labels(
            "Frequency",
            "Magnitude",
            "Hz",
            "V",
            x_mode="linear",
            y_mode="linear",
        )
        self.fft_plot.add_curve("spectrum", label="Spectrum")
        self.fft_plot.load_layout()

        self.timer = QTimer(self)
        self.timer.setInterval(int(1000 * self.samples_per_tick / self.sample_rate_hz))
        self.timer.timeout.connect(self.add_samples)

        self.start_button.clicked.connect(self.start_acquisition)
        self.stop_button.clicked.connect(self.stop_acquisition)
        self.reset_button.clicked.connect(self.reset_data)
        self.append_samples(int(4.0 * self.sample_rate_hz))
        self._set_acquisition_running(False)

    def show(self) -> None:
        self.window.show()

    def close(self) -> None:
        self.window.close()

    def start_acquisition(self) -> None:
        if not self.timer.isActive():
            self.timer.start()
            self.add_samples()
        self._set_acquisition_running(True)

    def stop_acquisition(self) -> None:
        self.timer.stop()
        self._set_acquisition_running(False)

    def reset_data(self) -> None:
        self.sample_index = 0
        self.time_values = np.array([], dtype=float)
        self.signal_values = np.array([], dtype=float)
        self.time_plot.set_data("input_signal", self.time_values, self.signal_values)
        self.fft_plot.set_data("spectrum", np.array([], dtype=float), np.array([], dtype=float))

    def add_samples(self) -> None:
        self.append_samples(self.samples_per_tick)

    def append_samples(self, sample_count: int) -> None:
        indices = np.arange(
            self.sample_index,
            self.sample_index + sample_count,
            dtype=float,
        )
        new_time_values = indices / self.sample_rate_hz
        new_signal_values = self._signal(new_time_values)

        self.sample_index += sample_count
        self.time_values = np.concatenate((self.time_values, new_time_values))
        self.signal_values = np.concatenate((self.signal_values, new_signal_values))

        self.time_plot.set_data("input_signal", self.time_values, self.signal_values)
        frequency_values, magnitude_values = self._fft(self.signal_values)
        self.fft_plot.set_data("spectrum", frequency_values, magnitude_values)

    def _create_plot(
        self,
        *,
        plot_container_name: str,
        toolbar_container_name: str,
        legend_container_name: str,
        plot_identifier: str,
    ) -> PyQtLabGraphWidget:
        return PyQtLabGraphWidget(
            plot_container=self._find_required_widget(plot_container_name),
            toolbar_container=self._find_required_widget(toolbar_container_name),
            legend_container=self._find_required_widget(legend_container_name),
            plot_identifier=plot_identifier,
            layout_path=Path.cwd() / "demo_time_fft.layout.json",
            rolling_window_size=10.0,
            legend_orientation=Qt.Orientation.Vertical,
            theme="light",
            plot_style="light",
            show_component_frames=False,
        )

    def _signal(self, time_values: np.ndarray) -> np.ndarray:
        base = np.sin(2.0 * math.pi * 5.0 * time_values)
        harmonic = 0.45 * np.sin(2.0 * math.pi * 13.0 * time_values)
        slow_drift = 0.2 * np.sin(2.0 * math.pi * 0.35 * time_values)
        return base + harmonic + slow_drift

    def _fft(self, signal_values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if len(signal_values) < 2:
            return np.array([], dtype=float), np.array([], dtype=float)

        window = np.hanning(len(signal_values))
        centered_values = signal_values - float(np.mean(signal_values))
        spectrum = np.fft.rfft(centered_values * window)
        frequency_values = np.fft.rfftfreq(len(signal_values), d=1.0 / self.sample_rate_hz)
        magnitude_values = 2.0 * np.abs(spectrum) / max(float(np.sum(window)), 1.0)
        return frequency_values, magnitude_values

    def _set_acquisition_running(self, running: bool) -> None:
        self.start_button.setEnabled(not running)
        self.stop_button.setEnabled(running)

    def _load_ui(self, ui_path: Path) -> QMainWindow:
        if not ui_path.exists():
            raise FileNotFoundError(f"Qt Designer UI file not found: {ui_path}")

        ui_file = QFile(str(ui_path))
        if not ui_file.open(QFile.OpenModeFlag.ReadOnly):
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
                f'Required {widget_type.__name__} "{object_name}" was not found '
                "in demo_time_fft.ui. Please check the objectName in Qt Designer."
            )
        return widget


def main() -> int:
    app = QApplication(sys.argv)
    window = TimeFftDemoWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
