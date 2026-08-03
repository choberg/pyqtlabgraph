from __future__ import annotations

import os

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import PyQtLabGraphWidget
from pyqtlabgraph.models import InteractionTool


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("tool", "axis_name", "drag_delta", "range_getter"),
    [
        (InteractionTool.X_ZOOM, "bottom", QPoint(60, 0), "get_x_range"),
        (InteractionTool.Y_ZOOM, "left", QPoint(0, 60), "get_y_range"),
    ],
)
def test_span_zoom_filter_does_not_block_axis_dragging(
    qapp: QApplication,
    tool: InteractionTool,
    axis_name: str,
    drag_delta: QPoint,
    range_getter: str,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier=f"{tool.value}-axis-drag")
    plot.resize(800, 500)
    plot.show()
    qapp.processEvents()
    plot.request_tool(tool, True)

    plot_widget = plot.native_plot_widget
    viewport = plot_widget.viewport()
    axis = plot.native_plot_item.getAxis(axis_name)
    start = plot_widget.mapFromScene(axis.sceneBoundingRect().center())
    before = getattr(plot, range_getter)()

    QTest.mousePress(viewport, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(viewport, start + drag_delta, delay=20)
    QTest.mouseRelease(viewport, Qt.MouseButton.LeftButton, pos=start + drag_delta)
    qapp.processEvents()

    after = getattr(plot, range_getter)()
    assert after != pytest.approx(before)
    assert (after[1] - after[0]) == pytest.approx(before[1] - before[0])
    assert not plot.interaction_state.autoscale_x
    assert not plot.interaction_state.autoscale_y
    plot.close()
