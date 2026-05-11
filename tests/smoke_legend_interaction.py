from __future__ import annotations

import os
import sys
from pathlib import Path
from types import MethodType

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqt_lab_graph import PyQtLabGraphWidget


LEGEND_CLICK_DELAY_MS = 220


def main() -> None:
    app = QApplication.instance() or QApplication([])

    plot_container = QWidget()
    toolbar_container = QWidget()
    legend_container = QWidget()
    for widget in (plot_container, toolbar_container, legend_container):
        widget.setLayout(QVBoxLayout())

    graph = PyQtLabGraphWidget(
        plot_container,
        toolbar_container,
        legend_container,
        plot_identifier="legend-interaction",
        show_toolbar=False,
        show_legend=True,
        theme="light",
    )
    graph.plot("sensor", [0.0, 1.0], [2.0, 3.0], label="Sensor")
    assert graph.legend is not None
    assert "sensor" in graph.legend.items_by_key

    legend_item = graph.legend.items_by_key["sensor"]
    assert graph.curves["sensor"].visible is True
    assert graph.curves["sensor"].item.isVisible() is True

    QTest.mouseClick(legend_item, Qt.MouseButton.LeftButton)
    QTest.qWait(LEGEND_CLICK_DELAY_MS + 50)
    app.processEvents()

    assert graph.curves["sensor"].visible is False
    assert graph.curves["sensor"].item.isVisible() is False
    assert legend_item.sample.opacity < 1.0

    QTest.mouseClick(legend_item, Qt.MouseButton.LeftButton)
    QTest.qWait(LEGEND_CLICK_DELAY_MS + 50)
    app.processEvents()

    assert graph.curves["sensor"].visible is True
    assert graph.curves["sensor"].item.isVisible() is True
    assert legend_item.sample.opacity == 1.0

    customize_requests: list[str | None] = []

    def record_customize_request(
        self: PyQtLabGraphWidget,
        curve_key: str | None = None,
    ) -> None:
        customize_requests.append(curve_key)

    graph.show_customize_dialog = MethodType(record_customize_request, graph)

    QTest.mouseDClick(legend_item, Qt.MouseButton.LeftButton)
    QTest.qWait(LEGEND_CLICK_DELAY_MS + 50)
    app.processEvents()

    assert customize_requests == ["sensor"]
    assert graph.curves["sensor"].visible is True
    assert graph.curves["sensor"].item.isVisible() is True

    print("legend interaction smoke ok")


if __name__ == "__main__":
    main()
