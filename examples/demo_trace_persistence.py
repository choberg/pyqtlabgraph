"""Repeated oscilloscope-like acquisitions with alpha trace persistence."""

from __future__ import annotations

import sys

import numpy as np
from _demo_theme import install_demo_theme_toggle
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMainWindow

from pyqtlabgraph import PyQtLabGraphWidget, TracePersistenceConfig


def main() -> int:
    app = QApplication(sys.argv)
    window = QMainWindow()
    plot = PyQtLabGraphWidget(plot_identifier="trace-persistence")
    x_values = np.linspace(0.0, 4.0 * np.pi, 4000)
    plot.plot("signal", x_values, np.sin(x_values), label="Signal")
    plot.set_curve_persistence("signal", TracePersistenceConfig(history_length=16))

    phase = 0.0

    def acquire() -> None:
        nonlocal phase
        phase += 0.14
        plot.set_data("signal", x_values, np.sin(x_values + phase))

    timer = QTimer(window)
    timer.timeout.connect(acquire)
    timer.start(140)
    window.setCentralWidget(plot)
    install_demo_theme_toggle(window, plot)
    window.resize(900, 560)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
