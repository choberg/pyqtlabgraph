from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pyqtgraph as pg
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import PyQtLabGraphToolbar, PyQtLabGraphWidget
from pyqtlabgraph.interaction import (
    _ZOOM_CURSOR_CENTER,
    _ZOOM_CURSOR_CROSS_HALF_SIZE,
    _render_zoom_cursor_pixmap,
)
from pyqtlabgraph.models import InteractionTool


def _assert_pixel_thin_cursor_rendering() -> None:
    center = _ZOOM_CURSOR_CENTER
    for ratio in (1.0, 2.0):
        pixmap = _render_zoom_cursor_pixmap(
            InteractionTool.RECT_ZOOM,
            QColor(Qt.GlobalColor.black),
            ratio,
        )
        image = pixmap.toImage()
        sample_x = round(
            (_ZOOM_CURSOR_CENTER - _ZOOM_CURSOR_CROSS_HALF_SIZE + 1) * ratio
        )
        opaque_rows = [
            y
            for y in range(image.height())
            if image.pixelColor(sample_x, y).alpha() != 0
        ]
        assert len(opaque_rows) == 1
        assert opaque_rows[0] == round(center * ratio)

    rect_image = _render_zoom_cursor_pixmap(
        InteractionTool.RECT_ZOOM,
        QColor(Qt.GlobalColor.black),
        1.0,
    ).toImage()
    x_image = _render_zoom_cursor_pixmap(
        InteractionTool.X_ZOOM,
        QColor(Qt.GlobalColor.black),
        1.0,
    ).toImage()
    y_image = _render_zoom_cursor_pixmap(
        InteractionTool.Y_ZOOM,
        QColor(Qt.GlobalColor.black),
        1.0,
    ).toImage()
    cross_start = _ZOOM_CURSOR_CENTER - _ZOOM_CURSOR_CROSS_HALF_SIZE
    cross_end = _ZOOM_CURSOR_CENTER + _ZOOM_CURSOR_CROSS_HALF_SIZE
    assert rect_image.pixelColor(cross_start, _ZOOM_CURSOR_CENTER).alpha() != 0
    assert rect_image.pixelColor(cross_end, _ZOOM_CURSOR_CENTER).alpha() != 0
    assert rect_image.pixelColor(cross_start - 1, _ZOOM_CURSOR_CENTER).alpha() == 0
    assert rect_image.pixelColor(cross_end + 1, _ZOOM_CURSOR_CENTER).alpha() == 0

    assert rect_image.pixelColor(22, 7).alpha() == 0
    assert all(x_image.pixelColor(x, 7).alpha() != 0 for x in range(22, 29))
    assert x_image.pixelColor(24, 5).alpha() != 0
    assert x_image.pixelColor(24, 9).alpha() != 0

    assert rect_image.pixelColor(24, 4).alpha() == 0
    assert all(y_image.pixelColor(24, y).alpha() != 0 for y in range(4, 11))
    assert y_image.pixelColor(22, 6).alpha() != 0
    assert y_image.pixelColor(26, 6).alpha() != 0


def _cursor_center_color(plot: PyQtLabGraphWidget) -> QColor:
    image = plot.native_plot_widget.viewport().cursor().pixmap().toImage()
    return image.pixelColor(_ZOOM_CURSOR_CENTER, _ZOOM_CURSOR_CENTER)


def main() -> None:
    app = QApplication.instance() or QApplication([])
    _assert_pixel_thin_cursor_rendering()
    plot = PyQtLabGraphWidget(plot_identifier="toolbar-interaction")
    toolbar = PyQtLabGraphToolbar(plot)
    placeholder = QWidget()
    layout = QVBoxLayout(placeholder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(toolbar)
    layout.addWidget(plot)
    placeholder.resize(640, 520)
    placeholder.show()
    app.processEvents()

    assert toolbar.plot is plot
    assert not hasattr(plot, "toolbar")
    assert toolbar.styleSheet() == ""
    assert toolbar.contentsMargins().left() == 4
    assert plot.native_view_box.state["mouseMode"] == pg.ViewBox.PanMode

    palette = toolbar.palette()
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ff00ff"))
    toolbar.setPalette(palette)
    toolbar.refresh_icons()
    assert not toolbar.show_all_action.icon().isNull()

    toolbar.zoom_action.trigger()
    assert plot.interaction_state.active_tool is InteractionTool.RECT_ZOOM
    assert plot.native_view_box.state["mouseMode"] == pg.ViewBox.RectMode
    assert toolbar.zoom_action.isChecked()
    plot_rect = plot.x_span_filter._plot_rect()
    data_point = plot_rect.center()
    viewport = plot.native_plot_widget.viewport()
    QTest.mouseMove(viewport, data_point)
    app.processEvents()
    assert not viewport.cursor().pixmap().isNull()
    assert viewport.cursor().hotSpot() == QPoint(
        _ZOOM_CURSOR_CENTER,
        _ZOOM_CURSOR_CENTER,
    )
    assert _cursor_center_color(plot) == QColor(Qt.GlobalColor.black)

    axis_point = QPoint(data_point.x(), plot_rect.bottom() + 10)
    QTest.mouseMove(viewport, axis_point)
    app.processEvents()
    assert viewport.cursor().shape() == Qt.CursorShape.ArrowCursor

    toolbar.x_zoom_action.trigger()
    assert plot.interaction_state.active_tool is InteractionTool.X_ZOOM
    assert plot.x_span_filter.enabled
    assert not toolbar.zoom_action.isChecked()
    cursor_key = plot.add_cursor("x", value=0.5)
    app.processEvents()
    cursor_scene_point = plot.native_view_box.mapViewToScene(QPointF(0.5, 0.5))
    cursor_viewport_point = plot.native_plot_widget.mapFromScene(cursor_scene_point)
    plot.request_tool(InteractionTool.X_ZOOM, False)
    cursor_item = plot._cursor_controller.presenter.cursor_items[cursor_key].item
    cursor_item.setCursor(Qt.CursorShape.SizeHorCursor)
    viewport.setCursor(cursor_item.cursor())
    assert viewport.cursor().shape() == Qt.CursorShape.SizeHorCursor
    plot.request_tool(InteractionTool.X_ZOOM, True)
    QTest.mouseMove(viewport, axis_point)
    app.processEvents()
    QTest.mouseMove(viewport, cursor_viewport_point)
    app.processEvents()
    assert not viewport.cursor().pixmap().isNull()

    plot.set_theme("dark")
    QTest.mouseMove(viewport, cursor_viewport_point)
    app.processEvents()
    assert _cursor_center_color(plot) == QColor(Qt.GlobalColor.white)
    plot.set_theme("light")
    QTest.mouseMove(viewport, cursor_viewport_point)
    app.processEvents()
    assert _cursor_center_color(plot) == QColor(Qt.GlobalColor.black)

    toolbar.y_zoom_action.trigger()
    assert plot.interaction_state.active_tool is InteractionTool.Y_ZOOM
    assert plot.y_span_filter.enabled
    assert not toolbar.x_zoom_action.isChecked()

    toolbar.autoscale_x_action.trigger()
    assert plot.interaction_state.autoscale_x
    assert toolbar.autoscale_x_action.isChecked()

    toolbar.show_all_action.trigger()
    assert plot.interaction_state.active_tool is InteractionTool.NONE
    QTest.mouseMove(viewport, cursor_viewport_point)
    app.processEvents()
    assert viewport.cursor().pixmap().isNull()
    assert viewport.cursor().shape() != Qt.CursorShape.BitmapCursor

    frameless = PyQtLabGraphToolbar(plot, show_frame=False)
    assert frameless.styleSheet() == ""
    assert frameless.contentsMargins().left() == 0
    assert not hasattr(frameless, "on_tool_requested")
    app.processEvents()
    print("toolbar interaction smoke ok")


if __name__ == "__main__":
    main()
