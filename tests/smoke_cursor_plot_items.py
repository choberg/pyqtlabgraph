from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import numpy as np

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import CursorLineStyle, CursorStyle, PyQtLabGraphWidget


def _container() -> QWidget:
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


def _cursor_item(graph: PyQtLabGraphWidget, cursor_key: str):
    cursor_plot_item = graph._cursor_controller.presenter.cursor_items[cursor_key]
    return cursor_plot_item.item


def _cursor_plot_item(graph: PyQtLabGraphWidget, cursor_key: str):
    return graph._cursor_controller.presenter.cursor_items[cursor_key]


def _label_scene_rect(graph: PyQtLabGraphWidget, cursor_key: str) -> QRectF:
    label = _cursor_plot_item(graph, cursor_key).label
    return label.mapRectToScene(label.boundingRect())


def _view_scene_rect(graph: PyQtLabGraphWidget) -> QRectF:
    view_rect = graph.native_view_box.viewRect()
    points = [
        graph.native_view_box.mapViewToScene(point)
        for point in (
            view_rect.topLeft(),
            view_rect.topRight(),
            view_rect.bottomLeft(),
            view_rect.bottomRight(),
        )
    ]
    return QRectF(
        QPointF(min(point.x() for point in points), min(point.y() for point in points)),
        QPointF(max(point.x() for point in points), max(point.y() for point in points)),
    )


def _x_line_scene_x(graph: PyQtLabGraphWidget, x_value: float) -> float:
    y_middle = graph.native_view_box.viewRect().center().y()
    return graph.native_view_box.mapViewToScene(QPointF(x_value, y_middle)).x()


def _y_line_scene_y(graph: PyQtLabGraphWidget, y_value: float) -> float:
    x_middle = graph.native_view_box.viewRect().center().x()
    return graph.native_view_box.mapViewToScene(QPointF(x_middle, y_value)).y()


def _assert_inside(inner: QRectF, outer: QRectF) -> None:
    assert inner.left() >= outer.left()
    assert inner.right() <= outer.right()
    assert inner.top() >= outer.top()
    assert inner.bottom() <= outer.bottom()


def main() -> None:
    app = QApplication.instance() or QApplication([])

    graph = PyQtLabGraphWidget(
        plot_identifier="cursor-plot-items",
    )
    graph.plot("sensor", np.array([1.0, 2.0, 3.0]), np.array([10.0, 20.0, 30.0]))

    x_key = graph.add_cursor("x", value=2.0)
    y_key = graph.add_cursor("y", value=20.0, label_visible=True)
    x_line = _cursor_item(graph, x_key)
    y_line = _cursor_item(graph, y_key)
    y_label = _cursor_plot_item(graph, y_key).label

    assert x_line.angle == 90
    assert y_line.angle == 0
    assert x_line.value() == 2.0
    assert y_line.value() == 20.0
    assert x_line.movable is True
    assert y_line.movable is True
    assert x_line.markers == []
    assert y_line.markers == []
    assert x_line.movement_cursor == Qt.CursorShape.SizeHorCursor
    assert y_line.movement_cursor == Qt.CursorShape.SizeVerCursor
    assert x_line in graph.native_plot_item.items
    assert y_line in graph.native_plot_item.items
    assert y_label in graph.native_plot_item.items
    assert y_label.isVisible() is True
    assert y_label.toPlainText() == "Y Cursor 1: 20"

    graph.add_cursor("x", key="outside_x", value=1000.0)
    graph.add_cursor("y", key="outside_y", value=1000.0)
    graph.request_show_all()
    x_range = graph.get_x_range()
    y_range = graph.get_y_range()
    assert x_range[0] <= 1.0 and x_range[1] < 10.0
    assert y_range[0] <= 10.0 and y_range[1] < 100.0

    graph.set_cursor_value(x_key, 3.0)
    assert x_line.value() == 3.0

    pair_x_a = graph.add_cursor("x", key="pair_x_a", value=1.0)
    pair_x_b = graph.add_cursor("x", key="pair_x_b", value=2.0)
    pair_key = graph.add_cursor_pair(pair_x_a, pair_x_b)
    pair_item = graph._cursor_controller.presenter.pair_items[pair_key]
    assert pair_item.line in graph.native_plot_item.items
    assert pair_item.region in graph.native_plot_item.items
    assert pair_item.region.isVisible() is True
    assert pair_item.region.zValue() < x_line.zValue()
    assert pair_item.line.isVisible() is True
    assert pair_item.label.toPlainText() == "Δx = 1"
    assert pair_item.label.border.style() == Qt.PenStyle.NoPen
    assert pair_item.label.fill.style() == Qt.BrushStyle.NoBrush
    graph.set_cursor_value(pair_x_b, 4.0)
    assert pair_item.label.toPlainText() == "Δx = 3"
    graph.set_cursor_pair_measurement_visible(pair_key, False)
    assert pair_item.line.isVisible() is False
    assert pair_item.region.isVisible() is False
    graph.set_cursor_pair_measurement_visible(pair_key, True)
    assert pair_item.line.isVisible() is True
    graph.set_cursor_pair_annotation_position(pair_key, 0.5)
    assert graph.cursor_pair_state(pair_key).annotation_position == 0.5
    assert math.isclose(float(pair_item.line.yData[0]), graph.native_view_box.viewRect().center().y())
    scene_position = graph.native_view_box.mapViewToScene(QPointF(2.0, graph.native_view_box.viewRect().bottom()))
    graph._cursor_controller.presenter.handle_pair_annotation_moved(pair_key, scene_position)
    assert 0.97 <= graph.cursor_pair_state(pair_key).annotation_position <= 0.98

    pair_y_a = graph.add_cursor("y", key="pair_y_a", value=5.0)
    pair_y_b = graph.add_cursor("y", key="pair_y_b", value=15.0)
    pair_y_key = graph.add_cursor_pair(pair_y_a, pair_y_b)
    pair_y_item = graph._cursor_controller.presenter.pair_items[pair_y_key]
    assert pair_y_item.label.toPlainText() == "Δy = 10"
    assert pair_y_item.line.isVisible() is True

    graph.set_cursor_style(
        x_key,
        CursorStyle(
            line_color="#abcdef",
            line_width=2.5,
            line_style=CursorLineStyle.DASH,
        ),
    )
    assert x_line.pen.color().name().lower() == "#abcdef"
    assert x_line.pen.widthF() == 2.5
    assert x_line.pen.style() == Qt.PenStyle.DashLine

    graph.apply_manual_x_limits(0.0, 10.0)
    graph.apply_manual_y_limits(0.0, 40.0)
    graph.set_cursor_value(x_key, 5.0)
    x_label = _cursor_plot_item(graph, x_key).label
    assert x_label.isVisible() is False
    graph.set_cursor_label_visible(x_key, True)
    assert x_label.isVisible() is True
    assert x_label.toPlainText() == "X Cursor 1: 5"
    assert x_label.textItem.defaultTextColor().name().lower() == "#111111"
    assert x_label.border.color().name().lower() == "#abcdef"
    graph.set_cursor_name(x_key, "Renamed X")
    assert x_label.toPlainText() == "Renamed X: 5"
    graph.set_theme("dark")
    assert x_label.textItem.defaultTextColor().name().lower() == "#f5f5f5"
    graph.set_theme("light")
    x_label_position = x_label.pos()
    x_label_rect = _label_scene_rect(graph, x_key)
    y_label_rect = _label_scene_rect(graph, y_key)
    view_scene_rect = _view_scene_rect(graph)
    assert x_label_rect.left() > _x_line_scene_x(graph, x_line.value())
    assert y_label_rect.bottom() < _y_line_scene_y(graph, y_line.value())
    _assert_inside(x_label_rect, view_scene_rect)
    _assert_inside(y_label_rect, view_scene_rect)
    graph.apply_manual_y_limits(-100.0, 100.0)
    app.processEvents()
    assert _cursor_plot_item(graph, x_key).label.pos().y() != x_label_position.y()

    graph.set_cursor_value(x_key, 9.95)
    app.processEvents()
    edge_label_rect = _label_scene_rect(graph, x_key)
    _assert_inside(edge_label_rect, _view_scene_rect(graph))
    assert edge_label_rect.right() < _x_line_scene_x(graph, x_line.value())

    overlap_graph = PyQtLabGraphWidget(
        plot_identifier="cursor-overlap-labels",
    )
    overlap_graph.plot("sensor", np.array([0.0, 10.0]), np.array([0.0, 10.0]))
    overlap_graph.apply_manual_x_limits(0.0, 10.0)
    overlap_graph.apply_manual_y_limits(0.0, 10.0)
    first_overlap_key = overlap_graph.add_cursor("x", value=5.0, name="First", label_visible=True)
    second_overlap_key = overlap_graph.add_cursor("x", value=5.1, name="Second", label_visible=True)
    y_overlap_key = overlap_graph.add_cursor("y", value=9.9, name="Horizontal", label_visible=True)
    app.processEvents()
    first_rect = _label_scene_rect(overlap_graph, first_overlap_key)
    second_rect = _label_scene_rect(overlap_graph, second_overlap_key)
    y_overlap_rect = _label_scene_rect(overlap_graph, y_overlap_key)
    assert not first_rect.intersects(second_rect)
    assert not first_rect.intersects(y_overlap_rect)
    assert not second_rect.intersects(y_overlap_rect)
    assert second_rect.top() > first_rect.top()
    _assert_inside(first_rect, _view_scene_rect(overlap_graph))
    _assert_inside(second_rect, _view_scene_rect(overlap_graph))
    _assert_inside(y_overlap_rect, _view_scene_rect(overlap_graph))

    snap_key = graph.add_cursor(
        "x",
        key="snap",
        value=2.8,
        snap_target_curve_key="sensor",
    )
    snap_line = _cursor_item(graph, snap_key)
    assert snap_line.value() == 3.0
    graph.set_data("sensor", np.array([4.0, 6.0]), np.array([40.0, 60.0]))
    assert graph.cursor_state(snap_key).value == 4.0
    assert snap_line.value() == 4.0

    follow_key = graph.add_cursor(
        "x",
        key="follow",
        value=4.0,
        snap_target_curve_key="sensor",
        follow_target_visibility=True,
    )
    follow_line = _cursor_item(graph, follow_key)
    assert follow_line.isVisible() is True
    graph.set_curve_visible("sensor", False)
    assert follow_line.isVisible() is False
    graph.set_cursor_label_visible(follow_key, True)
    assert _cursor_plot_item(graph, follow_key).label.isVisible() is False
    graph.set_curve_visible("sensor", True)
    assert follow_line.isVisible() is True
    assert _cursor_plot_item(graph, follow_key).label.isVisible() is True

    graph.remove_cursor(y_key)
    assert y_key not in graph._cursor_controller.presenter.cursor_items
    assert y_line not in graph.native_plot_item.items
    assert y_label not in graph.native_plot_item.items

    log_graph = PyQtLabGraphWidget(
        plot_identifier="cursor-log-plot-items",
    )
    log_graph.plot("positive", np.array([1.0, 10.0, 100.0]), np.array([1.0, 10.0, 100.0]))
    log_x_key = log_graph.add_cursor("x", value=10.0, label_visible=True)
    log_y_key = log_graph.add_cursor("y", value=10.0)
    log_graph.set_x_log(True)
    log_graph.set_y_log(True)
    assert math.isclose(_cursor_item(log_graph, log_x_key).value(), 1.0)
    assert math.isclose(_cursor_item(log_graph, log_y_key).value(), 1.0)
    assert _cursor_plot_item(log_graph, log_x_key).label.isVisible() is True
    assert _label_scene_rect(log_graph, log_x_key).left() > _x_line_scene_x(log_graph, 1.0)
    _assert_inside(_label_scene_rect(log_graph, log_x_key), _view_scene_rect(log_graph))

    log_graph.set_cursor_value(log_x_key, -5.0)
    assert _cursor_item(log_graph, log_x_key).isVisible() is False
    assert _cursor_plot_item(log_graph, log_x_key).label.isVisible() is False
    log_graph.set_cursor_value(log_x_key, 10.0)
    assert _cursor_item(log_graph, log_x_key).isVisible() is True
    assert math.isclose(_cursor_item(log_graph, log_x_key).value(), 1.0)
    assert _cursor_plot_item(log_graph, log_x_key).label.isVisible() is True

    time_graph = PyQtLabGraphWidget(
        plot_identifier="cursor-time-pair",
    )
    time_graph.plot("time", np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    time_a = time_graph.add_cursor("x", value=0.0)
    time_b = time_graph.add_cursor("x", value=0.25)
    time_pair = time_graph.add_cursor_pair(time_a, time_b)
    assert time_graph._cursor_controller.presenter.pair_items[time_pair].label.toPlainText() == "Δx = 0.25"
    time_graph.set_axis_labels("Time", "Value", x_mode="time")
    assert time_graph._cursor_controller.presenter.pair_items[time_pair].label.toPlainText() == "Δt = 0.25 s   f = 4 Hz"

    app.processEvents()
    print("cursor plot items smoke ok")


if __name__ == "__main__":
    main()
