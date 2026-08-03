from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import PyQtLabGraphWidget


def _container() -> QWidget:
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


def main() -> None:
    _app = QApplication.instance() or QApplication([])
    graph = PyQtLabGraphWidget(
        plot_identifier="cursor-refresh",
    )
    graph.plot("signal", list(range(20)), list(range(20)))
    for index in range(5):
        graph.add_cursor(
            "x",
            value=index + 0.2,
            snap_target_curve_key="signal",
        )

    provider_calls = 0
    manager = graph._cursor_controller.manager
    original_provider = manager._curve_data_provider

    def counted_provider(curve_key: str):  # type: ignore[no-untyped-def]
        nonlocal provider_calls
        provider_calls += 1
        assert original_provider is not None
        return original_provider(curve_key)

    manager._curve_data_provider = counted_provider
    graph.set_data("signal", list(range(30)), list(range(30)))
    assert provider_calls == 1

    graph._cursor_controller.nudge_cursor_group(
        graph.cursor_states()[0].key,
        selected_cursor_keys=[],
        direction=1,
        step_ratio=0.01,
    )
    assert provider_calls == 1

    print("cursor refresh smoke ok")


if __name__ == "__main__":
    main()
