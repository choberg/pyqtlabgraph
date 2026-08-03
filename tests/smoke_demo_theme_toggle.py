from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from _demo_theme import install_demo_theme_toggle
from PySide6.QtCore import QPoint
from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QDialog, QMainWindow, QVBoxLayout, QWidget

from pyqtlabgraph import (
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = QMainWindow()
    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)
    first_plot = PyQtLabGraphWidget(plot_identifier="theme-toggle-first")
    second_plot = PyQtLabGraphWidget(plot_identifier="theme-toggle-second")
    first_plot.add_curve("sensor", label="Sensor")
    toolbar = PyQtLabGraphToolbar(first_plot)
    legend = PyQtLabGraphLegend(first_plot)
    cursor_widget = PyQtLabGraphCursorWidget(first_plot)
    for component in (toolbar, first_plot, legend, cursor_widget, second_plot):
        layout.addWidget(component)
    window.setCentralWidget(central_widget)

    action = install_demo_theme_toggle(window, first_plot, second_plot)
    assert action is window.findChild(QAction, "demoDarkModeAction")
    assert not action.isChecked()
    assert first_plot.theme.name == "light"
    assert second_plot.plot_style.name == "light"
    assert app.palette().color(QPalette.ColorRole.Window) == QColor("#f1f3f5")
    assert app.palette().color(QPalette.ColorRole.Base) == QColor("#ffffff")
    window.resize(900, 900)
    window.show()
    app.processEvents()

    action.setChecked(True)
    app.processEvents()
    assert first_plot.theme.name == "dark"
    assert first_plot.plot_style.name == "dark"
    assert second_plot.theme.name == "dark"
    assert second_plot.plot_style.name == "dark"
    assert app.style().objectName() == "fusion"
    assert app.palette().color(QPalette.ColorRole.Window) == QColor("#28323c")
    assert toolbar.palette().color(QPalette.ColorRole.ButtonText) == QColor("#e6edf3")
    assert legend.palette().color(QPalette.ColorRole.Window) == QColor("#28323c")
    assert cursor_widget.palette().color(QPalette.ColorRole.Window) == QColor("#28323c")
    legend_label = legend.items_by_key["sensor"].label
    assert legend_label.palette().color(QPalette.ColorRole.WindowText) == QColor(
        "#e6edf3"
    )
    assert not toolbar.show_all_action.icon().isNull()

    show_all_button = toolbar.widgetForAction(toolbar.show_all_action)
    assert show_all_button is not None
    assert show_all_button.palette().color(QPalette.ColorRole.Button) == QColor("#34414d")
    QTest.mouseMove(show_all_button, QPoint(5, 5))
    app.processEvents()
    assert show_all_button.grab().toImage().pixelColor(5, 5).lightness() < 160

    label_color_before_cancel = legend_label.palette().color(
        QPalette.ColorRole.WindowText
    )
    first_plot.show_customize_dialog()
    app.processEvents()
    dialog = first_plot.findChild(QDialog, "pyqtLabGraphCustomizeDialog")
    assert dialog is not None
    dialog.reject()
    app.processEvents()
    assert legend_label.palette().color(QPalette.ColorRole.WindowText) == label_color_before_cancel

    action.setChecked(False)
    app.processEvents()
    assert first_plot.theme.name == "light"
    assert first_plot.plot_style.name == "light"
    assert second_plot.theme.name == "light"
    assert second_plot.plot_style.name == "light"
    assert app.palette().color(QPalette.ColorRole.Window) == QColor("#f1f3f5")
    assert app.palette().color(QPalette.ColorRole.Base) == QColor("#ffffff")
    assert toolbar.palette().color(QPalette.ColorRole.Button) == QColor("#e7ecf0")
    assert toolbar.palette().color(QPalette.ColorRole.ButtonText) == QColor("#202830")
    assert legend.palette().color(QPalette.ColorRole.Window) == QColor("#f1f3f5")
    assert legend_label.palette().color(QPalette.ColorRole.WindowText) == QColor(
        "#202830"
    )

    action.setChecked(True)
    app.processEvents()
    assert toolbar.palette().color(QPalette.ColorRole.ButtonText) == QColor("#e6edf3")
    assert legend_label.palette().color(QPalette.ColorRole.WindowText) == QColor("#e6edf3")

    window.close()
    app.processEvents()
    print("demo theme toggle smoke ok")


if __name__ == "__main__":
    main()
