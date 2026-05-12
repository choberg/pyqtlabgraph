from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from demo_time_fft import TimeFftDemoWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = TimeFftDemoWindow()
    required_widget_names = [
        "timePlotContainer",
        "timeLegendContainer",
        "timeToolbarContainer",
        "fftPlotContainer",
        "fftLegendContainer",
        "fftToolbarContainer",
    ]
    for widget_name in required_widget_names:
        assert window.window.findChild(QWidget, widget_name) is not None
    for button_name in ("startButton", "stopButton", "resetButton"):
        assert window.window.findChild(QPushButton, button_name) is not None

    assert window.time_plot.plot_frame is None
    assert window.time_plot.toolbar_frame is None
    assert window.time_plot.legend_frame is None
    assert window.fft_plot.plot_frame is None
    assert window.fft_plot.toolbar_frame is None
    assert window.fft_plot.legend_frame is None

    window.show()
    app.processEvents()
    time_section = window.window.findChild(QWidget, "timePlotSection")
    fft_section = window.window.findChild(QWidget, "fftPlotSection")
    assert time_section.sizePolicy().verticalStretch() == 1
    assert fft_section.sizePolicy().verticalStretch() == 1
    initial_time_height = time_section.height()
    initial_fft_height = fft_section.height()

    window.time_plot.show_customize_dialog()
    app.processEvents()
    time_dialog = getattr(window.time_plot, "_pyqt_lab_graph_customize_dialogs")[0]
    time_dialog.reject()
    app.processEvents()
    assert time_section.height() == initial_time_height
    assert fft_section.height() == initial_fft_height

    window.fft_plot.show_customize_dialog()
    app.processEvents()
    fft_dialog = getattr(window.fft_plot, "_pyqt_lab_graph_customize_dialogs")[0]
    fft_dialog.accept()
    app.processEvents()
    assert time_section.height() == initial_time_height
    assert fft_section.height() == initial_fft_height

    initial_count = len(window.time_values)
    window.append_samples(5_000)
    assert len(window.time_values) == initial_count + 5_000
    assert len(window.signal_values) == initial_count + 5_000

    x_values, y_values = window.time_plot.curve_data("input_signal")
    assert len(x_values) == len(window.time_values)
    assert len(y_values) == len(window.signal_values)
    assert x_values[0] == 0.0

    frequency_values, magnitude_values = window.fft_plot.curve_data("spectrum")
    assert len(frequency_values) == len(magnitude_values)
    assert len(frequency_values) > 0

    window.close()
    app.processEvents()
    print("time fft demo smoke ok")


if __name__ == "__main__":
    main()
