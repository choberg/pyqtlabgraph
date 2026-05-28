from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication

from pyqtlabgraph import AxisMode
from pyqtlabgraph.axis import SmartAxisItem, resolve_axis_mode


def main() -> None:
    app = QApplication.instance() or QApplication([])

    axis = SmartAxisItem("bottom")
    axis.set_mode("time")
    assert axis.tickStrings([5.0], scale=1.0, spacing=1.0) == ["5 s"]

    axis.set_mode(AxisMode.TIME)
    assert resolve_axis_mode("time") == AxisMode.TIME
    assert resolve_axis_mode(AxisMode.LINEAR) == AxisMode.LINEAR
    try:
        resolve_axis_mode("log")
    except ValueError as exc:
        assert "Unknown PyQtLabGraph axis mode" in str(exc)
    else:
        raise AssertionError("resolve_axis_mode should reject unknown modes")
    try:
        axis.set_mode("log")
    except ValueError as exc:
        assert "Unknown PyQtLabGraph axis mode" in str(exc)
    else:
        raise AssertionError("SmartAxisItem.set_mode should reject unknown modes")

    assert axis.tickStrings([0.0, 5.0], scale=1.0, spacing=1.0) == ["0 s", "5 s"]
    assert axis.tickStrings(
        [65.0, 3661.0, 90061.0],
        scale=1.0,
        spacing=1.0,
    ) == [
        "1 min 5 s",
        "1 h 1 min 1 s",
        "1 d 1 h 1 min 1 s",
    ]
    assert axis.tickStrings([-5.0, -65.0], scale=1.0, spacing=1.0) == [
        "-5 s",
        "-1 min 5 s",
    ]
    assert axis.tickStrings([1.25], scale=1.0, spacing=0.1) == ["1.2 s"]
    assert axis.tickStrings([1.25], scale=1.0, spacing=0.005) == ["1.25 s"]
    assert axis.tickStrings([1.25], scale=1.0, spacing=0.0005) == ["1.250 s"]

    axis.set_mode(AxisMode.LINEAR)
    assert len(axis.tickStrings([0.0, 1.0], scale=1.0, spacing=1.0)) == 2

    app.processEvents()
    print("axis formatting smoke ok")


if __name__ == "__main__":
    main()
