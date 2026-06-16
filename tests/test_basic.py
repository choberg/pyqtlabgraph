from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import pytest
except ImportError:
    class MockPytest:
        @staticmethod
        def fixture(scope: str | None = None) -> object:
            def decorator(func: object) -> object:
                return func
            return decorator
    pytest = MockPytest()  # type: ignore

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtGui import QColor
from pyqtlabgraph import (
    PyQtLabGraphWidget,
    CurveStyle,
    PyQtLabGraphTheme,
)
from pyqtlabgraph.themes import resolve_theme
from pyqtlabgraph.styles import resolve_plot_style


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
        container,
        plot_identifier="test-plot",
        show_toolbar=False,
        show_legend=False,
    )
    assert widget.plot_identifier == "test-plot"
    assert len(widget.curve_manager.curves) == 0


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


def test_resolve_plot_style() -> None:
    style = resolve_plot_style("dark")
    assert style.name == "dark"

    with pytest.raises(ValueError, match="Unknown PyQtLabGraph plot style"):
        resolve_plot_style("nonexistent")


def test_resolve_theme() -> None:
    theme = resolve_theme("dark")
    assert theme.name == "dark"

    with pytest.raises(ValueError, match="Unknown PyQtLabGraph theme"):
        resolve_theme("nonexistent")


def test_logarithmic_axes(qapp: QApplication) -> None:
    container = QWidget()
    container.setLayout(QVBoxLayout())
    widget = PyQtLabGraphWidget(
        container,
        plot_identifier="test-log-plot",
        show_toolbar=False,
        show_legend=False,
    )
    # Test initial states
    assert not widget.x_log
    assert not widget.y_log

    # Test setting log mode
    widget.x_log = True
    widget.y_log = True
    assert widget.x_log
    assert widget.y_log

    # Test underlying plot log mode
    assert widget.plot_item.getViewBox().state['logMode'] == [True, True]

    # Test plotting data and autoscale in log mode
    widget.add_curve("curve1")
    widget.curve_manager.set_data("curve1", [10, 100, 1000], [10, 100, 1000])
    widget.request_autoscale_x(True)
    widget.request_autoscale_y(True)
    
    # Range should be in log10 space
    x_range = widget.get_x_range()
    y_range = widget.get_y_range()
    
    # log10(10) = 1.0, log10(1000) = 3.0
    assert x_range[0] <= 1.05 and x_range[1] >= 2.95
    assert y_range[0] <= 1.05 and y_range[1] >= 2.95

    # Test layout persistence
    from pyqtlabgraph.layouts import PlotLayoutState
    layout_state = PlotLayoutState.from_widget(widget, include_x_range=True, include_y_range=True)
    assert layout_state.x_log
    assert layout_state.y_log

    # Revert log state on a new widget using the layout
    widget2 = PyQtLabGraphWidget(
        container,
        plot_identifier="test-log-plot-2",
        show_toolbar=False,
        show_legend=False,
    )
    assert not widget2.x_log
    layout_state.apply_to_widget(widget2)
    assert widget2.x_log
    assert widget2.y_log


if __name__ == "__main__":
    # Emulate pytest.raises for standalone execution
    class MockRaises:
        def __init__(self, expected_exc: type[Exception], match: str | None = None) -> None:
            self.expected_exc = expected_exc
            self.match = match
        def __enter__(self) -> MockRaises:
            return self
        def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object) -> bool:
            if exc_type is None:
                raise AssertionError(f"Expected exception {self.expected_exc.__name__} was not raised")
            if not issubclass(exc_type, self.expected_exc):
                return False
            if self.match and self.match not in str(exc_val):
                raise AssertionError(f"Exception message '{exc_val}' did not match pattern '{self.match}'")
            return True

    pytest.raises = MockRaises  # type: ignore

    print("Running basic tests...")
    q = qapp()
    test_version()
    test_widget_creation(q)
    test_styles_validation()
    test_themes_validation()
    test_resolve_plot_style()
    test_resolve_theme()
    test_logarithmic_axes(q)
    print("basic tests ok")
