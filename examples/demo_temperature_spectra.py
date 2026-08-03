"""Color spectra by temperature with a continuous gradient."""

from __future__ import annotations

import sys

import numpy as np
from _demo_theme import install_demo_theme_toggle
from PySide6.QtWidgets import QApplication, QMainWindow

from pyqtlabgraph import PyQtLabGraphWidget


def main() -> int:
    app = QApplication(sys.argv)
    window = QMainWindow()
    plot = PyQtLabGraphWidget(plot_identifier="temperature-spectra")
    window.setCentralWidget(plot)
    theme_action = install_demo_theme_toggle(window, plot)
    frequencies = np.linspace(0.0, 10.0, 1200)
    temperatures = (20.0, 35.0, 50.0, 65.0, 80.0)
    values: dict[str, float] = {}
    for temperature in temperatures:
        key = f"{temperature:.0f}C"
        spectrum = np.exp(-((frequencies - temperature / 10.0) ** 2) / 0.8)
        plot.plot(key, frequencies, spectrum, label=f"{temperature:.0f} °C")
        values[key] = temperature

    def apply_temperature_colors() -> None:
        plot.apply_curve_gradient("viridis", values=values, value_range=(20.0, 80.0))

    apply_temperature_colors()
    theme_action.toggled.connect(apply_temperature_colors)
    plot.set_axis_labels("Frequency", "Amplitude", x_units="Hz")
    window.resize(900, 560)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
