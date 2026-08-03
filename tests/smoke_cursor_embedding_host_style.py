from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cursor_smoke_helpers import container
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import (
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    cursor_container = container()
    plot = PyQtLabGraphWidget(plot_identifier="cursor-embedded")
    plot.add_curve("sensor", label="Sensor")
    toolbar = PyQtLabGraphToolbar(plot)
    legend = PyQtLabGraphLegend(plot)
    embedded = PyQtLabGraphCursorWidget(plot)
    cursor_container.layout().addWidget(toolbar)
    cursor_container.layout().addWidget(legend)
    cursor_container.layout().addWidget(embedded)
    cursor_container.show()
    app.processEvents()

    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#25313c"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#f1f3f5"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#dde7ef"))
    app.setPalette(palette)
    app.processEvents()

    assert cursor_container.layout().itemAt(2).widget() is embedded
    assert toolbar.styleSheet() == ""
    assert legend.styleSheet() == ""
    assert embedded.styleSheet() == ""
    assert toolbar.palette().color(QPalette.ColorRole.ButtonText) == QColor("#dde7ef")
    assert legend.items_by_key["sensor"].label.palette().color(
        QPalette.ColorRole.WindowText
    ) == QColor("#f1f3f5")
    assert embedded.palette().color(QPalette.ColorRole.WindowText) == QColor("#f1f3f5")
    assert not hasattr(plot, "cursor_widget")

    suppressed_container = container()
    suppressed = PyQtLabGraphWidget(plot_identifier="cursor-without-panel")
    assert suppressed_container.layout().count() == 0
    assert not hasattr(suppressed, "cursor_widget")

    frameless_container = container()
    frameless_plot = PyQtLabGraphWidget(plot_identifier="cursor-frameless")
    frameless = PyQtLabGraphCursorWidget(frameless_plot, show_frame=False)
    frameless_container.layout().addWidget(frameless)
    assert frameless.styleSheet() == ""
    assert frameless_container.layout().itemAt(0).widget() is frameless
    cursor_container.close()
    app.processEvents()
    print("cursor embedding and host-style smoke ok")


if __name__ == "__main__":
    main()
