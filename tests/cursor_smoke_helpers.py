from __future__ import annotations

from PySide6.QtCore import QItemSelectionModel
from PySide6.QtWidgets import QVBoxLayout, QWidget

from pyqtlabgraph import PyQtLabGraphCursorWidget, PyQtLabGraphWidget


def container() -> QWidget:
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


def graph(
    identifier: str,
    *,
    cursor_container: QWidget | None = None,
    **kwargs: object,
) -> PyQtLabGraphWidget:
    show_frame = bool(kwargs.pop("show_component_frames", True))
    create_cursor_widget = bool(kwargs.pop("show_cursor_widget", cursor_container is not None))
    plot = PyQtLabGraphWidget(
        plot_identifier=identifier,
        **kwargs,
    )
    if create_cursor_widget:
        widget = PyQtLabGraphCursorWidget(plot, show_frame=show_frame)
        if cursor_container is not None:
            cursor_container.layout().addWidget(widget)
            plot._test_cursor_container = cursor_container
        plot._test_cursor_widget = widget
    return plot


def select_rows(widget: PyQtLabGraphCursorWidget, *rows: int) -> None:
    selection = widget.list.selectionModel()
    selection.clearSelection()
    for position, row in enumerate(rows):
        index = widget.model.index(row, 0)
        selection.select(index, QItemSelectionModel.SelectionFlag.Select)
        if position == 0:
            selection.setCurrentIndex(index, QItemSelectionModel.SelectionFlag.NoUpdate)
