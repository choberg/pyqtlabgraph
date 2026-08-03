from __future__ import annotations

import os

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import (
    CurveStyle,
    PyQtLabGraphTheme,
    PyQtLabGraphWidget,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    # Ensure there is a QApplication running in offscreen mode
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_version() -> None:
    from pyqtlabgraph import __version__
    assert __version__ != ""


def test_widget_creation(qapp: QApplication) -> None:
    container = QWidget()
    container.setLayout(QVBoxLayout())
    widget = PyQtLabGraphWidget(
        plot_identifier="test-plot",
    )
    assert widget.plot_identifier == "test-plot"
    assert len(widget._curve_manager.curves) == 0


def test_styles_validation() -> None:
    # Test valid styles
    style = CurveStyle(line_color="#123456")
    assert style.line_color == "#123456"

    # Test invalid color raises ValueError
    with pytest.raises(ValueError, match="Invalid line_color color"):
        CurveStyle(line_color="invalid-color")


def test_themes_validation() -> None:
    theme = PyQtLabGraphTheme(
        name="test",
        plot_background="#ffffff",
        grid=QColor(0, 0, 0),
        border="#000000",
    )
    assert theme.name == "test"

    with pytest.raises(ValueError, match="Invalid plot_background color"):
        PyQtLabGraphTheme(
            name="test",
            plot_background="invalid",
            grid=QColor(0, 0, 0),
            border="#000000",
        )


def test_logarithmic_axes(qapp: QApplication) -> None:
    container = QWidget()
    container.setLayout(QVBoxLayout())
    widget = PyQtLabGraphWidget(
        plot_identifier="test-log-plot",
    )
    # Test initial states
    assert not widget.x_log
    assert not widget.y_log

    # Test setting log mode
    widget.set_x_log(True)
    widget.set_y_log(True)
    assert widget.x_log
    assert widget.y_log

    # Test underlying plot log mode
    assert widget.native_plot_item.getViewBox().state['logMode'] == [True, True]

    # Test plotting data and autoscale in log mode
    widget.add_curve("curve1")
    widget.set_data("curve1", [10, 100, 1000], [10, 100, 1000])
    widget.request_autoscale_x(True)
    widget.request_autoscale_y(True)
    
    # Range should be in log10 space
    x_range = widget.get_x_range()
    y_range = widget.get_y_range()
    
    # log10(10) = 1.0, log10(1000) = 3.0
    assert x_range[0] <= 1.05 and x_range[1] >= 2.95
    assert y_range[0] <= 1.05 and y_range[1] >= 2.95

    # Test layout persistence
    from pyqtlabgraph.runtime_state import PlotSnapshot
    snapshot = PlotSnapshot.capture(widget)
    assert snapshot.x_log
    assert snapshot.y_log

    # Revert log state on a new widget using the layout
    widget2 = PyQtLabGraphWidget(
        plot_identifier="test-log-plot-2",
    )
    widget2.add_curve("curve1")
    assert not widget2.x_log
    widget2.restore_snapshot(snapshot)
    assert widget2.x_log
    assert widget2.y_log
