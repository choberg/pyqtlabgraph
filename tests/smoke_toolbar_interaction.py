from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqt_lab_graph import PyQtLabGraphWidget
from pyqt_lab_graph.models import InteractionTool


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

    app.processEvents()
    print("toolbar interaction smoke ok")


if __name__ == "__main__":
    main()
