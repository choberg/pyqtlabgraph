from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyqtgraph as pg
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QVBoxLayout, QWidget

from pyqt_lab_graph import PyQtLabGraphWidget
from pyqt_lab_graph.models import InteractionTool


class WheelEventStub:
    def __init__(self, *, modifiers: Qt.KeyboardModifier = Qt.KeyboardModifier.NoModifier) -> None:
        self._modifiers = modifiers
        self.accepted = False
        self.ignored = False

    def delta(self) -> int:
        return 120

    def pos(self) -> QPointF:
        return QPointF(0.0, 0.0)

    def modifiers(self) -> Qt.KeyboardModifier:
        return self._modifiers

    def accept(self) -> None:
        self.accepted = True

    def ignore(self) -> None:
        self.ignored = True


class AxisDoubleClickEventStub:
    def __init__(self, scene_pos: QPointF) -> None:
        self._scene_pos = scene_pos
        self.accepted = False

    def button(self) -> Qt.MouseButton:
        return Qt.MouseButton.LeftButton

    def scenePos(self) -> QPointF:
        return self._scene_pos

    def accept(self) -> None:
        self.accepted = True


def ranges_differ(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return any(abs(left - right) > 1e-9 for left, right in zip(first, second))


def ranges_close(first: tuple[float, float], second: tuple[float, float]) -> bool:
    return all(abs(left - right) <= 1e-12 for left, right in zip(first, second))


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
        plot_identifier="toolbar-interaction",
        show_toolbar=True,
        show_legend=False,
    )
    assert graph.toolbar is not None
    toolbar = graph.toolbar

    assert not hasattr(toolbar, "plot_widget")
    assert not hasattr(toolbar, "x_span_filter")
    assert not hasattr(toolbar, "y_span_filter")
    assert not hasattr(toolbar, "theme")
    assert hasattr(graph, "toolbar_frame")
    assert not toolbar.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert "background: transparent" in toolbar.styleSheet()
    assert toolbar.rolling_button.testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert toolbar.rolling_button.menu().testAttribute(Qt.WidgetAttribute.WA_StyledBackground)
    assert "border-radius: 6px" in graph.plot_frame.styleSheet()
    assert "border-radius: 6px" in graph.toolbar_frame.styleSheet()
    assert graph.view_box.state["mouseMode"] == pg.ViewBox.PanMode

    frameless_plot_container = QWidget()
    frameless_toolbar_container = QWidget()
    frameless_legend_container = QWidget()
    for widget in (frameless_plot_container, frameless_toolbar_container, frameless_legend_container):
        widget.setLayout(QVBoxLayout())
    frameless_graph = PyQtLabGraphWidget(
        frameless_plot_container,
        frameless_toolbar_container,
        frameless_legend_container,
        plot_identifier="toolbar-frameless-components",
        show_toolbar=True,
        show_legend=True,
        show_component_frames=False,
    )
    assert frameless_graph.plot_frame is None
    assert frameless_graph.toolbar_frame is None
    assert frameless_graph.legend_frame is None
    assert frameless_plot_container.layout().itemAt(0).widget() is frameless_graph.plot_widget
    assert frameless_toolbar_container.layout().itemAt(0).widget() is frameless_graph.toolbar
    assert frameless_legend_container.layout().itemAt(0).widget() is frameless_graph.legend

    styled_plot_container = QWidget()
    styled_plot_container.setLayout(QVBoxLayout())
    styled_plot_container.setStyleSheet(
        "QFrame#pyqtLabGraphPlotFrame { border: 2px solid red; border-radius: 9px; }"
    )
    styled_graph = PyQtLabGraphWidget(
        styled_plot_container,
        plot_identifier="toolbar-styled",
        show_toolbar=False,
    )
    assert styled_graph.plot_frame.styleSheet() == ""

    palette = toolbar.palette()
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ff00ff"))
    toolbar.setPalette(palette)
    toolbar.refresh_icons()
    assert not toolbar.show_all_action.icon().isNull()

    toolbar.zoom_action.trigger()
    assert graph.interaction_state.active_tool == InteractionTool.RECT_ZOOM
    assert graph.interaction_state.autoscale_x is False
    assert graph.interaction_state.autoscale_y is False
    assert graph.interaction_state.rolling_x is False
    assert graph.view_box.state["mouseMode"] == pg.ViewBox.RectMode
    assert toolbar.zoom_action.isChecked() is True

    toolbar.x_zoom_action.trigger()
    assert graph.interaction_state.active_tool == InteractionTool.X_ZOOM
    assert graph.view_box.state["mouseMode"] == pg.ViewBox.PanMode
    assert graph.x_span_filter.enabled is True
    assert graph.y_span_filter.enabled is False
    assert toolbar.zoom_action.isChecked() is False
    assert toolbar.x_zoom_action.isChecked() is True

    toolbar.y_zoom_action.trigger()
    assert graph.interaction_state.active_tool == InteractionTool.Y_ZOOM
    assert graph.x_span_filter.enabled is False
    assert graph.y_span_filter.enabled is True
    assert toolbar.x_zoom_action.isChecked() is False
    assert toolbar.y_zoom_action.isChecked() is True

    save_requests = 0

    def record_save_request() -> None:
        nonlocal save_requests
        save_requests += 1

    toolbar.on_save_requested = record_save_request
    toolbar.save_action.trigger()
    assert save_requests == 1

    assert toolbar.show_all_action.text() == "Show All"
    assert toolbar.show_all_action.toolTip() == "Show All"
    toolbar.show_all_action.trigger()
    assert graph.interaction_state.active_tool == InteractionTool.NONE
    assert graph.interaction_state.autoscale_x is True
    assert graph.interaction_state.autoscale_y is True
    assert graph.interaction_state.rolling_x is False
    assert graph.view_box.state["mouseMode"] == pg.ViewBox.PanMode
    assert graph.x_span_filter.enabled is False
    assert graph.y_span_filter.enabled is False
    assert toolbar.zoom_action.isChecked() is False
    assert toolbar.x_zoom_action.isChecked() is False
    assert toolbar.y_zoom_action.isChecked() is False

    graph.apply_manual_x_limits(0.0, 10.0)
    graph.apply_manual_y_limits(0.0, 20.0)
    x_before = graph.get_x_range()
    y_before = graph.get_y_range()
    wheel_event = WheelEventStub()
    graph.view_box.wheelEvent(wheel_event)
    assert wheel_event.accepted is True
    assert ranges_differ(x_before, graph.get_x_range())
    assert ranges_differ(y_before, graph.get_y_range())

    graph.apply_manual_x_limits(0.0, 10.0)
    graph.apply_manual_y_limits(0.0, 20.0)
    x_before = graph.get_x_range()
    y_before = graph.get_y_range()
    shift_wheel_event = WheelEventStub(modifiers=Qt.KeyboardModifier.ShiftModifier)
    graph.view_box.wheelEvent(shift_wheel_event)
    assert shift_wheel_event.accepted is True
    assert ranges_differ(x_before, graph.get_x_range())
    assert graph.get_y_range() == y_before
    assert graph.interaction_state.autoscale_x is False
    assert graph.interaction_state.autoscale_y is False
    assert graph.interaction_state.rolling_x is False

    graph.apply_manual_x_limits(0.0, 10.0)
    graph.apply_manual_y_limits(0.0, 20.0)
    axis_event = AxisDoubleClickEventStub(QPointF(10.0, 10.0))
    graph.bottom_axis.mouseDoubleClickEvent(axis_event)
    app.processEvents()
    assert axis_event.accepted is True
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    assert minimum_edit.text() == "0.000"
    assert maximum_edit.text() == "10.000"
    minimum_edit.setText("3")
    maximum_edit.setText("8")
    QTest.keyClick(maximum_edit, Qt.Key.Key_Return)
    app.processEvents()
    assert graph.get_x_range() == (3.0, 8.0)
    assert graph.interaction_state.autoscale_x is False
    assert graph.interaction_state.rolling_x is False

    graph.left_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("6")
    maximum_edit.setText("-2")
    QTest.keyClick(minimum_edit, Qt.Key.Key_Return)
    app.processEvents()
    assert graph.get_y_range() == (-2.0, 6.0)
    assert graph.interaction_state.autoscale_y is False

    graph.bottom_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("1k")
    maximum_edit.setText("2k")
    QTest.keyClick(maximum_edit, Qt.Key.Key_Return)
    app.processEvents()
    assert graph.get_x_range() == (1000.0, 2000.0)

    graph.left_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("1n")
    maximum_edit.setText("5n")
    QTest.keyClick(maximum_edit, Qt.Key.Key_Return)
    app.processEvents()
    assert ranges_close(graph.get_y_range(), (1e-9, 5e-9))

    graph.bottom_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("1h")
    maximum_edit.setText("2h")
    QTest.keyClick(maximum_edit, Qt.Key.Key_Return)
    app.processEvents()
    assert graph.get_x_range() == (3600.0, 7200.0)

    graph.bottom_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("abc")
    maximum_edit.setText("9k")
    QTest.keyClick(maximum_edit, Qt.Key.Key_Return)
    app.processEvents()
    assert graph._axis_range_popup is popup
    assert graph.get_x_range() == (3600.0, 7200.0)
    assert minimum_edit.styleSheet()
    popup.close()
    app.processEvents()

    graph.bottom_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("-5")
    maximum_edit.setText("50")
    QTest.keyClick(minimum_edit, Qt.Key.Key_Escape)
    app.processEvents()
    assert graph.get_x_range() == (3600.0, 7200.0)

    graph.bottom_axis.mouseDoubleClickEvent(AxisDoubleClickEventStub(QPointF(10.0, 10.0)))
    app.processEvents()
    assert graph._axis_range_popup is not None
    popup = graph._axis_range_popup
    minimum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMinEdit")
    maximum_edit = popup.findChild(QLineEdit, "pyqtLabGraphAxisMaxEdit")
    minimum_edit.setText("-10")
    maximum_edit.setText("100")
    popup.close()
    app.processEvents()
    assert graph.get_x_range() == (3600.0, 7200.0)

    app.processEvents()
    print("toolbar interaction smoke ok")


if __name__ == "__main__":
    main()
