from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from _demo_theme import install_demo_theme_toggle
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyqtlabgraph import (
    CursorLineStyle,
    CursorStyle,
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)

_FREE_X_INITIAL_VALUE = 3.0
_FREE_X_DEMO_VALUE = 4.5
_FREE_Y_INITIAL_VALUE = 0.5
_FREE_Y_DEMO_VALUE = -0.35
_SNAP_INITIAL_VALUE = 7.25
_SNAP_DEMO_VALUE = 8.12


def create_window(*, load_saved_layout: bool = True) -> QMainWindow:
    window = QMainWindow()
    window.setWindowTitle("PyQtLabGraph Cursor Demo")

    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)

    toolbar_container = QWidget()
    controls_container = QWidget()
    content_container = QWidget()
    plot_column = QWidget()
    plot_container = QWidget()
    legend_container = QWidget()
    cursor_container = QWidget()
    cursor_container.setObjectName("cursorDemoInspectorContainer")
    cursor_container.setMinimumWidth(270)
    cursor_container.setMaximumWidth(320)

    layout.addWidget(toolbar_container)
    layout.addWidget(controls_container)
    layout.addWidget(content_container, stretch=1)
    window.setCentralWidget(central_widget)

    content_layout = QHBoxLayout(content_container)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.addWidget(plot_column, stretch=1)
    content_layout.addWidget(cursor_container)

    plot_layout = QVBoxLayout(plot_column)
    plot_layout.setContentsMargins(0, 0, 0, 0)
    plot_layout.addWidget(plot_container, stretch=1)
    plot_layout.addWidget(legend_container)

    graph = PyQtLabGraphWidget(
        plot_identifier="cursor-demo-main",
        layout_path=Path.cwd() / "demo_cursor.layout.json",
    )
    toolbar = PyQtLabGraphToolbar(graph)
    legend = PyQtLabGraphLegend(graph, orientation=Qt.Orientation.Horizontal)
    cursor_widget = PyQtLabGraphCursorWidget(graph)
    QVBoxLayout(toolbar_container).addWidget(toolbar)
    QVBoxLayout(plot_container).addWidget(graph)
    QVBoxLayout(legend_container).addWidget(legend)
    QVBoxLayout(cursor_container).addWidget(cursor_widget)
    graph.set_axis_labels("Time", "Signal", "s", "V", x_mode="linear", y_mode="linear")

    x_values = np.linspace(0.0, 12.0, 241)
    sine_values = np.sin(x_values)
    reference_values = 0.45 * np.cos(1.7 * x_values) + 0.2
    graph.plot("signal", x_values, sine_values, label="Signal")
    graph.plot("reference", x_values, reference_values, label="Reference")

    x_cursor_key = graph.add_cursor(
        "x",
        key="free_x",
        name="Free X",
        value=_FREE_X_INITIAL_VALUE,
        style=CursorStyle(line_color="#0072B2", line_width=2.0),
    )
    y_cursor_key = graph.add_cursor(
        "y",
        key="free_y",
        name="Free Y",
        value=_FREE_Y_INITIAL_VALUE,
        style=CursorStyle(
            line_color="#D55E00",
            line_width=2.0,
            line_style=CursorLineStyle.DASH,
        ),
    )
    snap_cursor_key = graph.add_cursor(
        "x",
        key="signal_snap",
        name="Signal Snap",
        value=_SNAP_INITIAL_VALUE,
        style=CursorStyle(
            line_color="#009E73",
            line_width=2.0,
            line_style=CursorLineStyle.DOT,
        ),
        snap_target_curve_key="signal",
        follow_target_visibility=True,
    )

    cursor_keys = (x_cursor_key, y_cursor_key, snap_cursor_key)

    controls_layout = QHBoxLayout(controls_container)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    move_free_x_button = QPushButton("Move Free X")
    move_free_x_button.setObjectName("cursorDemoMoveFreeXButton")
    move_free_y_button = QPushButton("Move Free Y")
    move_free_y_button.setObjectName("cursorDemoMoveFreeYButton")
    move_snap_button = QPushButton("Move Snap Near Peak")
    move_snap_button.setObjectName("cursorDemoMoveSnapButton")
    reset_button = QPushButton("Reset Cursors")
    reset_button.setObjectName("cursorDemoResetButton")
    status_label = QLabel("Last cursor move: none")
    status_label.setObjectName("cursorDemoStatusLabel")

    controls_layout.addWidget(move_free_x_button)
    controls_layout.addWidget(move_free_y_button)
    controls_layout.addWidget(move_snap_button)
    controls_layout.addWidget(reset_button)
    controls_layout.addStretch(1)
    controls_layout.addWidget(status_label)

    def update_status(cursor_key: str, value: float) -> None:
        name = graph.cursor_state(cursor_key).name
        status_label.setText(f"Last cursor move: {name} = {value:.6g}")

    def reset_cursors() -> None:
        graph.set_cursor_value(x_cursor_key, _FREE_X_INITIAL_VALUE)
        graph.set_cursor_value(y_cursor_key, _FREE_Y_INITIAL_VALUE)
        graph.set_cursor_value(snap_cursor_key, _SNAP_INITIAL_VALUE)

    move_free_x_button.clicked.connect(lambda: graph.set_cursor_value(x_cursor_key, _FREE_X_DEMO_VALUE))
    move_free_y_button.clicked.connect(lambda: graph.set_cursor_value(y_cursor_key, _FREE_Y_DEMO_VALUE))
    move_snap_button.clicked.connect(lambda: graph.set_cursor_value(snap_cursor_key, _SNAP_DEMO_VALUE))
    reset_button.clicked.connect(reset_cursors)
    graph.cursor_moved.connect(update_status)

    if load_saved_layout:
        graph.load_layout()

    window.graph = graph
    window.cursor_keys = cursor_keys
    window.toolbar = toolbar
    window.legend = legend
    window.cursor_widget = cursor_widget
    window.cursor_container = cursor_container
    window.content_container = content_container
    window.plot_column = plot_column
    window.move_free_x_button = move_free_x_button
    window.move_free_y_button = move_free_y_button
    window.move_snap_button = move_snap_button
    window.reset_button = reset_button
    window.status_label = status_label
    install_demo_theme_toggle(window, graph)
    window.resize(1120, 680)
    return window


def main() -> int:
    app = QApplication(sys.argv)
    window = create_window()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
