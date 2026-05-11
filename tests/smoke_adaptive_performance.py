from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqt_lab_graph import CurveStyle, PyQtLabGraphWidget


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
        plot_identifier="adaptive-performance",
        show_toolbar=True,
        show_legend=True,
    )
    graph.plot(
        "dense",
        [float(index) for index in range(20)],
        [float(index % 3) for index in range(20)],
        style=CurveStyle(
            marker_enabled=True,
            marker_symbol="s",
            marker_size=5,
            marker_filled=False,
        ),
    )

    curve = graph.curves["dense"]
    graph.adaptive_performance_threshold = 5
    graph.adaptive_performance_restore_threshold = 3

    graph._set_x_range(0.0, 19.0)
    graph._update_adaptive_performance(force=True)
    assert graph.adaptive_performance_active is True
    assert curve.item.opts["symbol"] is None
    assert graph._effective_antialiasing_enabled() is False

    graph._set_x_range(0.0, 1.0)
    graph._update_adaptive_performance(force=True)
    assert graph.adaptive_performance_active is False
    assert curve.item.opts["symbol"] == "s"
    assert graph._effective_antialiasing_enabled() is True

    graph.set_adaptive_performance_enabled(False)
    graph._set_x_range(0.0, 19.0)
    graph._update_adaptive_performance(force=True)
    assert graph.adaptive_performance_active is False
    assert curve.item.opts["symbol"] == "s"

    app.processEvents()
    print("adaptive performance smoke ok")


if __name__ == "__main__":
    main()
