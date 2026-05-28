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
from pyqt_lab_graph import (
    PyQtLabGraphWidget,
    CurveStyle,
    PyQtLabGraphTheme,
)
from pyqt_lab_graph.themes import resolve_theme
from pyqt_lab_graph.styles import resolve_plot_style


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    # Ensure there is a QApplication running in offscreen mode
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_version() -> None:
    from pyqt_lab_graph import __version__
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
    print("basic tests ok")
