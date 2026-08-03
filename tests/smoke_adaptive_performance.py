from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import CurveStyle, PyQtLabGraphWidget


def main() -> None:
    app = QApplication.instance() or QApplication([])

    plot_container = QWidget()
    toolbar_container = QWidget()
    legend_container = QWidget()
    for widget in (plot_container, toolbar_container, legend_container):
        widget.setLayout(QVBoxLayout())

    graph = PyQtLabGraphWidget(
        plot_identifier="adaptive-performance",
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
    graph.plot(
        "marker-only",
        [float(index) for index in range(20)],
        [float(index % 5) for index in range(20)],
        style=CurveStyle(
            line_enabled=False,
            marker_enabled=True,
            marker_symbol="o",
            marker_size=5,
        ),
    )

    curve = graph._curve_manager.curves["dense"]
    marker_only_curve = graph._curve_manager.curves["marker-only"]
    graph._render_optimizer.threshold = 5
    graph._render_optimizer.restore_threshold = 5

    graph.apply_manual_x_limits(0.0, 19.0)
    assert graph._render_optimizer.active is True
    assert curve.item.opts["symbol"] is None
    assert marker_only_curve.item.opts["symbol"] is None
    assert marker_only_curve.item.opts["pen"].style() != Qt.PenStyle.NoPen
    assert graph._render_optimizer.effective_antialiasing_enabled() is False

    graph.apply_manual_x_limits(0.0, 1.0)
    assert graph._render_optimizer.active is False
    assert curve.item.opts["symbol"] == "s"
    assert marker_only_curve.item.opts["symbol"] == "o"
    assert marker_only_curve.item.opts["pen"].style() == Qt.PenStyle.NoPen
    assert graph._render_optimizer.effective_antialiasing_enabled() is True

    graph.set_adaptive_performance_enabled(False)
    graph.apply_manual_x_limits(0.0, 19.0)
    assert graph._render_optimizer.active is False
    assert curve.item.opts["symbol"] == "s"
    assert marker_only_curve.item.opts["symbol"] == "o"
    assert marker_only_curve.item.opts["pen"].style() == Qt.PenStyle.NoPen

    log_container = QWidget()
    log_container.setLayout(QVBoxLayout())
    log_graph = PyQtLabGraphWidget(
        plot_identifier="adaptive-performance-log-x",
    )
    log_graph.plot(
        "dense",
        [float(index) for index in range(1, 101)],
        [float(index % 3) for index in range(1, 101)],
        style=CurveStyle(
            marker_enabled=True,
            marker_symbol="s",
            marker_size=5,
        ),
    )
    log_curve = log_graph._curve_manager.curves["dense"]
    log_graph._render_optimizer.threshold = 5
    log_graph._render_optimizer.restore_threshold = 5

    log_graph.apply_manual_x_limits(1.0, 100.0)
    assert log_graph._render_optimizer.active is True
    assert log_curve.item.opts["symbol"] is None

    log_graph.set_x_log(True)
    assert log_graph.get_x_range() == (0.0, 2.0)
    assert log_graph._render_optimizer.active is True
    assert log_curve.item.opts["symbol"] is None

    log_graph.apply_manual_x_limits(0.0, 0.1)
    assert log_graph._render_optimizer.active is False
    assert log_curve.item.opts["symbol"] == "s"

    app.processEvents()
    print("adaptive performance smoke ok")


if __name__ == "__main__":
    main()
