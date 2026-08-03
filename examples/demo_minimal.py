from __future__ import annotations

import random
import sys
from pathlib import Path

from _demo_theme import install_demo_theme_toggle
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from pyqtlabgraph import PyQtLabGraphLegend, PyQtLabGraphToolbar, PyQtLabGraphWidget


def create_window() -> QMainWindow:
    window = QMainWindow()
    window.setWindowTitle("PyQtLabGraph Minimal Demo")

    # PyQtLabGraph only needs normal Qt widgets as mounting points.
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)

    toolbar_container = QWidget()
    plot_container = QWidget()
    legend_container = QWidget()

    layout.addWidget(toolbar_container)
    layout.addWidget(plot_container, stretch=1)
    layout.addWidget(legend_container)
    window.setCentralWidget(central_widget)

    # Create independent components and embed them in the host layout.
    graph = PyQtLabGraphWidget(
        plot_identifier="minimal-main",
        layout_path=Path.cwd() / "demo_minimal.layout.json",
    )
    toolbar = PyQtLabGraphToolbar(graph)
    legend = PyQtLabGraphLegend(graph, orientation=Qt.Orientation.Horizontal)
    QVBoxLayout(toolbar_container).addWidget(toolbar)
    QVBoxLayout(plot_container).addWidget(graph)
    QVBoxLayout(legend_container).addWidget(legend)

    # Configure labels and plot one named curve.
    graph.set_axis_labels("Index", "Value")

    # Provide all data at once using pyqtgraph-style data arguments.
    rng = random.Random(42)
    x_values = list(range(100))
    y_values = [rng.random() for _ in x_values]
    y_values2 = [rng.random() for _ in x_values]
    graph.plot("random_values", x_values, y_values, label="Random Values 1")
    graph.plot("random_values2", x_values, y_values2, label="Random Values 2")
    graph.load_layout()

    # Keep a reference to the graph for the lifetime of the window.
    window.graph = graph
    window.toolbar = toolbar
    window.legend = legend
    install_demo_theme_toggle(window, graph)
    window.resize(900, 600)
    return window


def main() -> int:
    app = QApplication(sys.argv)
    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
