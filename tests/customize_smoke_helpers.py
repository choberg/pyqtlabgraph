from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QVBoxLayout,
    QWidget,
)

from pyqtlabgraph import PyQtLabGraphWidget, dialogs


def container() -> QWidget:
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


def graph(identifier: str, *, layout_path: Path | None = None) -> PyQtLabGraphWidget:
    return PyQtLabGraphWidget(
        plot_identifier=identifier,
        layout_path=layout_path,
    )


def child(dialog: QDialog, widget_type: type, name: str):
    widget = dialog.findChild(widget_type, name)
    assert widget is not None, f"Missing dialog control: {name}"
    return widget


def set_combo_data(combo: QComboBox, data: object) -> None:
    index = combo.findData(data)
    assert index >= 0, f"Missing combo data: {data!r}"
    combo.setCurrentIndex(index)


def show_with_callback(
    plot: PyQtLabGraphWidget,
    callback: Callable[[QDialog], None],
    *,
    curve_key: str | None = None,
) -> None:
    original_show = dialogs.QDialog.show
    dialogs.QDialog.show = callback
    try:
        plot.show_customize_dialog(curve_key)
    finally:
        dialogs.QDialog.show = original_show


def group_sections(dialog: QDialog, tab_index: int) -> list[tuple[str, list[str]]]:
    layout = dialog.tabs.widget(tab_index).layout()
    assert isinstance(layout, QVBoxLayout)
    sections: list[tuple[str, list[str]]] = []
    for index in range(layout.count()):
        widget = layout.itemAt(index).widget()
        if widget is None:
            continue
        assert isinstance(widget, QGroupBox)
        form = widget.layout()
        assert isinstance(form, QFormLayout)
        labels: list[str] = []
        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            label = item.widget() if item is not None else None
            labels.append(label.text() if label is not None else "")
        sections.append((widget.title(), labels))
    return sections
