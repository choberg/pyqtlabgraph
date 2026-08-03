from __future__ import annotations

from PySide6.QtGui import QAction, QColor, QPalette
from PySide6.QtWidgets import QApplication, QMainWindow

from pyqtlabgraph import PyQtLabGraphWidget


def install_demo_theme_toggle(
    window: QMainWindow,
    *plots: PyQtLabGraphWidget,
) -> QAction:
    """Add one application-wide Light/Dark switch to a demo window."""
    app = QApplication.instance()
    if app is None:
        raise RuntimeError("Create QApplication before installing the demo theme toggle.")

    view_menu = window.menuBar().addMenu("&View")
    view_menu.setObjectName("demoViewMenu")
    action = QAction("Dark mode", window)
    action.setObjectName("demoDarkModeAction")
    action.setCheckable(True)
    view_menu.addAction(action)

    def apply_theme(dark_mode: bool) -> None:
        apply_demo_theme(app, *plots, dark_mode=dark_mode)

    action.toggled.connect(apply_theme)
    apply_theme(False)
    return action


def apply_demo_theme(
    app: QApplication,
    *plots: PyQtLabGraphWidget,
    dark_mode: bool,
) -> None:
    theme_name = "dark" if dark_mode else "light"
    _apply_application_theme(app, dark_mode)
    for plot in plots:
        plot.set_theme(theme_name)
        plot.set_plot_style(theme_name)


def _apply_application_theme(app: QApplication, dark_mode: bool) -> None:
    app.setStyle("Fusion")
    palette = app.style().standardPalette()
    palette = _dark_palette(palette) if dark_mode else _light_palette(palette)
    app.setPalette(palette)


def _light_palette(palette: QPalette) -> QPalette:
    colors = {
        QPalette.ColorRole.Window: "#f1f3f5",
        QPalette.ColorRole.WindowText: "#202830",
        QPalette.ColorRole.Base: "#ffffff",
        QPalette.ColorRole.AlternateBase: "#e9edf2",
        QPalette.ColorRole.ToolTipBase: "#ffffff",
        QPalette.ColorRole.ToolTipText: "#202830",
        QPalette.ColorRole.Text: "#202830",
        QPalette.ColorRole.Button: "#e7ecf0",
        QPalette.ColorRole.ButtonText: "#202830",
        QPalette.ColorRole.BrightText: "#ffffff",
        QPalette.ColorRole.Light: "#ffffff",
        QPalette.ColorRole.Midlight: "#d9e0e6",
        QPalette.ColorRole.Mid: "#aeb9c3",
        QPalette.ColorRole.Dark: "#788896",
        QPalette.ColorRole.Shadow: "#4f5e6b",
        QPalette.ColorRole.Highlight: "#4f8fbd",
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.Link: "#1d6fa5",
        QPalette.ColorRole.LinkVisited: "#7758a6",
        QPalette.ColorRole.PlaceholderText: "#6f7c87",
        QPalette.ColorRole.Accent: "#4f8fbd",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))

    disabled = QPalette.ColorGroup.Disabled
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.PlaceholderText,
    ):
        palette.setColor(disabled, role, QColor("#8a959f"))
    palette.setColor(disabled, QPalette.ColorRole.Highlight, QColor("#c3ccd4"))
    palette.setColor(disabled, QPalette.ColorRole.HighlightedText, QColor("#687683"))
    return palette


def _dark_palette(palette: QPalette) -> QPalette:
    colors = {
        QPalette.ColorRole.Window: "#28323c",
        QPalette.ColorRole.WindowText: "#e6edf3",
        QPalette.ColorRole.Base: "#202830",
        QPalette.ColorRole.AlternateBase: "#303b46",
        QPalette.ColorRole.ToolTipBase: "#34414d",
        QPalette.ColorRole.ToolTipText: "#e6edf3",
        QPalette.ColorRole.Text: "#e6edf3",
        QPalette.ColorRole.Button: "#34414d",
        QPalette.ColorRole.ButtonText: "#e6edf3",
        QPalette.ColorRole.BrightText: "#ffffff",
        QPalette.ColorRole.Light: "#566879",
        QPalette.ColorRole.Midlight: "#43515f",
        QPalette.ColorRole.Mid: "#526270",
        QPalette.ColorRole.Dark: "#1c242c",
        QPalette.ColorRole.Shadow: "#10161c",
        QPalette.ColorRole.Highlight: "#6ea8d9",
        QPalette.ColorRole.HighlightedText: "#101820",
        QPalette.ColorRole.Link: "#7db7e8",
        QPalette.ColorRole.LinkVisited: "#b5a0e6",
        QPalette.ColorRole.PlaceholderText: "#9aa7b4",
        QPalette.ColorRole.Accent: "#6ea8d9",
    }
    for role, color in colors.items():
        palette.setColor(role, QColor(color))

    disabled = QPalette.ColorGroup.Disabled
    for role in (
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.Text,
        QPalette.ColorRole.ButtonText,
        QPalette.ColorRole.PlaceholderText,
    ):
        palette.setColor(disabled, role, QColor("#8996a3"))
    palette.setColor(disabled, QPalette.ColorRole.Highlight, QColor("#43515f"))
    palette.setColor(disabled, QPalette.ColorRole.HighlightedText, QColor("#a5b0bb"))
    return palette
