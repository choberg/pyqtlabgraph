from __future__ import annotations

import math
import re
from typing import Callable

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget

_RANGE_EDITOR_DECIMALS = 3
_RANGE_EDITOR_MARGIN = 6
_RANGE_EDITOR_SPACING = 6
_RANGE_EDITOR_OFFSET = QPoint(8, 8)
_RANGE_EDITOR_VALUE_PATTERN = re.compile(
    r"^\s*"
    r"([+-]?(?:(?:\d+(?:\.\d*)?)|(?:\.\d+))(?:[eE][+-]?\d+)?)"
    r"\s*([A-Za-zµμ]*)"
    r"\s*$"
)
_RANGE_EDITOR_SUFFIX_FACTORS = {
    "": 1.0,
    "T": 1e12,
    "G": 1e9,
    "M": 1e6,
    "k": 1e3,
    "m": 1e-3,
    "u": 1e-6,
    "µ": 1e-6,
    "μ": 1e-6,
    "n": 1e-9,
    "p": 1e-12,
    "s": 1.0,
    "min": 60.0,
    "h": 3600.0,
    "d": 86400.0,
}
_RANGE_EDITOR_ERROR_STYLE = "QLineEdit { border: 1px solid #c2410c; }"


def _format_range_editor_value(value: float) -> str:
    return f"{value:.{_RANGE_EDITOR_DECIMALS}f}"


def _parse_range_editor_value(text: str) -> float:
    match = _RANGE_EDITOR_VALUE_PATTERN.match(text)
    if match is None:
        raise ValueError(f'Invalid range value "{text}".')

    suffix = match.group(2)
    if suffix not in _RANGE_EDITOR_SUFFIX_FACTORS:
        raise ValueError(f'Unknown range value suffix "{suffix}".')

    value = float(match.group(1)) * _RANGE_EDITOR_SUFFIX_FACTORS[suffix]
    if not math.isfinite(value):
        raise ValueError(f'Range value "{text}" is not finite.')
    return value


class _AxisRangePopup(QWidget):
    """Small popup editor for manually entering one axis range."""

    def __init__(
        self,
        axis_label: str,
        minimum: float,
        maximum: float,
        on_apply: Callable[[float, float], None],
        parent: QWidget,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.on_apply = on_apply
        self.setObjectName("pyqtLabGraphAxisRangePopup")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            _RANGE_EDITOR_MARGIN,
            _RANGE_EDITOR_MARGIN,
            _RANGE_EDITOR_MARGIN,
            _RANGE_EDITOR_MARGIN,
        )
        layout.setSpacing(_RANGE_EDITOR_SPACING)
        layout.addWidget(QLabel(f"{axis_label} min:", self))
        self.minimum_edit = self._create_line_edit(minimum, "pyqtLabGraphAxisMinEdit")
        layout.addWidget(self.minimum_edit)
        layout.addWidget(QLabel(f"{axis_label} max:", self))
        self.maximum_edit = self._create_line_edit(maximum, "pyqtLabGraphAxisMaxEdit")
        layout.addWidget(self.maximum_edit)

        for widget in (self.minimum_edit, self.maximum_edit):
            widget.installEventFilter(self)

    def focus_first_field(self) -> None:
        self.minimum_edit.setFocus(Qt.FocusReason.PopupFocusReason)
        self.minimum_edit.selectAll()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.KeyPress:
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
                self._apply_and_close()
                return True
            if event.key() == Qt.Key.Key_Escape:
                self.close()
                return True
        return super().eventFilter(watched, event)

    def _apply_and_close(self) -> None:
        minimum = self._parse_editor_value(self.minimum_edit)
        maximum = self._parse_editor_value(self.maximum_edit)
        if minimum is None or maximum is None:
            if minimum is None:
                self.minimum_edit.setFocus(Qt.FocusReason.OtherFocusReason)
                self.minimum_edit.selectAll()
            else:
                self.maximum_edit.setFocus(Qt.FocusReason.OtherFocusReason)
                self.maximum_edit.selectAll()
            return

        self.on_apply(minimum, maximum)
        self.close()

    def _create_line_edit(self, value: float, object_name: str) -> QLineEdit:
        line_edit = QLineEdit(_format_range_editor_value(value), self)
        line_edit.setObjectName(object_name)
        line_edit.textEdited.connect(lambda _text, editor=line_edit: editor.setStyleSheet(""))
        return line_edit

    def _parse_editor_value(self, line_edit: QLineEdit) -> float | None:
        try:
            value = _parse_range_editor_value(line_edit.text())
        except ValueError:
            line_edit.setStyleSheet(_RANGE_EDITOR_ERROR_STYLE)
            return None

        line_edit.setStyleSheet("")
        return value
