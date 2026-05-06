from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class PyQtLabGraphTheme:
    outer: str
    plot: str
    axis: str
    text: str
    grid: QColor
    button: str
    button_hover: str
    button_disabled: str
    button_disabled_text: str
    border: str
    highlight: str
    frame: str
    legend_disabled_text: str
    toolbar_icon: str


LIGHT_THEME = PyQtLabGraphTheme(
    outer="#f3f4f6",
    plot="#ffffff",
    axis="#000000",
    text="#202124",
    grid=QColor(156, 163, 175, 70),
    button="#f8fafc",
    button_hover="#e5e7eb",
    button_disabled="#e5e7eb",
    button_disabled_text="#9ca3af",
    border="#c8ced6",
    highlight="#ffffff",
    frame="#f3f4f6",
    legend_disabled_text="#9ca3af",
    toolbar_icon="#111827",
)

DARK_THEME = PyQtLabGraphTheme(
    outer="#1f2329",
    plot="#181c20",
    axis="#d8dee9",
    text="#d8dee9",
    grid=QColor(216, 222, 233, 38),
    button="#272c33",
    button_hover="#343b44",
    button_disabled="#1b1f24",
    button_disabled_text="#6b7280",
    border="#3a4048",
    highlight="#4b5563",
    frame="#1f2329",
    legend_disabled_text="#6b7280",
    toolbar_icon="#e5e7eb",
)


def theme_for_dark_mode(enabled: bool) -> PyQtLabGraphTheme:
    return DARK_THEME if enabled else LIGHT_THEME


def legend_style(theme: PyQtLabGraphTheme) -> str:
    return f"""
    QWidget#livePlotLegend {{
        background-color: {theme.frame};
        color: {theme.text};
    }}
    """


def frame_style(theme: PyQtLabGraphTheme) -> str:
    return f"""
        QFrame#plotFrame,
        QFrame#toolbarFrame,
        QFrame#legendFrame {{
            background-color: {theme.frame};
            border: 1px solid {theme.border};
            border-top-color: {theme.highlight};
            border-left-color: {theme.highlight};
            border-radius: 6px;
        }}
        QToolBar {{
            background-color: {theme.frame};
            border: none;
            spacing: 2px;
        }}
        QToolButton,
        QPushButton {{
            background-color: {theme.button};
            color: {theme.text};
            border: 1px solid {theme.border};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QToolButton:hover,
        QPushButton:hover {{
            background-color: {theme.button_hover};
        }}
        QToolButton:checked {{
            background-color: {theme.button_hover};
            border-color: {theme.highlight};
        }}
        QPushButton:disabled {{
            background-color: {theme.button_disabled};
            color: {theme.button_disabled_text};
        }}
        QMenu {{
            background-color: {theme.frame};
            color: {theme.text};
            border: 1px solid {theme.border};
        }}
        QMenu::item:selected {{
            background-color: {theme.button_hover};
        }}
    """
