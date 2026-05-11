from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pyqtgraph as pg
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QFrame, QVBoxLayout, QWidget


def main() -> None:
    pg.setConfigOptions(antialias=False)
    assert pg.getConfigOption("antialias") is False

    from pyqt_lab_graph import CurveStyle, PyQtLabGraphWidget

    assert pg.getConfigOption("antialias") is False

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
        plot_identifier="public-api-cleanup",
        show_toolbar=False,
        show_legend=False,
        theme="light",
    )
    graph.plot(
        "sensor",
        np.array([0.0, 1.0, 2.0]),
        np.array([3.0, 2.0, 1.0]),
        style=CurveStyle(
            line_color="#123456",
            line_width=2.5,
            marker_enabled=True,
            marker_symbol="d",
            marker_size=9,
            marker_filled=True,
            marker_outline_width=1.5,
        ),
    )
    graph.add_curve("y_only")
    graph.set_data("y_only", [4.0, 5.0])
    y_only_x, y_only_y = graph.curve_data("y_only")
    assert y_only_x.tolist() == [0, 1]
    assert y_only_y.tolist() == [4.0, 5.0]

    sensor_x, sensor_y = graph.curve_data("sensor")
    assert isinstance(sensor_x, np.ndarray)
    assert isinstance(sensor_y, np.ndarray)
    assert sensor_x.tolist() == [0.0, 1.0, 2.0]
    assert sensor_y.tolist() == [3.0, 2.0, 1.0]

    assert graph.native_plot_widget is graph.plot_widget
    assert graph.native_plot_item is graph.plot_item
    assert graph.native_view_box is graph.view_box
    assert graph.native_plot_widget.frameShape() == QFrame.Shape.NoFrame
    sensor_item = graph.curve_item("sensor")
    assert isinstance(sensor_item, pg.PlotDataItem)
    assert sensor_item is graph.curves["sensor"].item
    sensor_item.setData([10.0, 11.0], [12.0, 13.0])
    sensor_x, sensor_y = graph.curve_data("sensor")
    assert sensor_x.tolist() == [10.0, 11.0]
    assert sensor_y.tolist() == [12.0, 13.0]

    graph.add_curve("dense")
    graph._set_x_range(0.0, 10.0)
    graph.set_data(
        "dense",
        np.arange(1.0, 10_001.0),
        np.ones(10_000),
    )
    graph.plot("negative_x", np.array([-5.0, -1.0]), np.array([0.0, 0.0]))
    dense_x, dense_y = graph.curve_data("dense")
    assert len(dense_x) == 10_000
    assert len(dense_y) == 10_000
    graph.request_show_all()
    assert graph.get_x_range() == (-5.0, 10_000.0)

    host_palette = app.palette()
    host_palette.setColor(QPalette.ColorRole.WindowText, QColor("#445566"))
    app.setPalette(host_palette)
    app.processEvents()

    before_style = graph.curve_style("sensor")

    graph.set_theme("dark")
    after_dark_style = graph.curve_style("sensor")
    assert "QGraphicsView#pyqtLabGraphPlotWidget" in graph.plot_widget.styleSheet()
    assert "border: none" in graph.plot_widget.styleSheet()
    graph.set_theme("light-solarized")
    app.processEvents()
    after_light_solarized_style = graph.curve_style("sensor")
    assert graph.plot_widget.backgroundBrush().color().alpha() == 0
    assert graph.view_box.background.rect().right() > graph.view_box.rect().right()
    assert graph.view_box.background.rect().bottom() > graph.view_box.rect().bottom()
    assert graph.bottom_axis.pen().color().name().lower() == "#445566"
    assert graph.bottom_axis.tickPen().color().name().lower() == "#445566"
    assert graph.bottom_axis.textPen().color().name().lower() == "#445566"
    assert graph.left_axis.pen().color().name().lower() == "#445566"

    graph.set_theme("dark-solarized")
    after_dark_solarized_style = graph.curve_style("sensor")
    assert graph.bottom_axis.pen().color().name().lower() == "#445566"
    assert graph.bottom_axis.tickPen().color().name().lower() == "#445566"
    assert graph.bottom_axis.textPen().color().name().lower() == "#445566"
    assert graph.left_axis.pen().color().name().lower() == "#445566"

    assert after_dark_style == before_style
    assert after_light_solarized_style == before_style
    assert after_dark_solarized_style == before_style
    assert graph.curves["sensor"].item.opts["pen"].color().name().lower() == "#123456"

    app.processEvents()
    print("public api cleanup smoke ok")


if __name__ == "__main__":
    main()
