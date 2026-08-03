from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customize_smoke_helpers import child, graph, group_sections, show_with_callback
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QPushButton


def main() -> None:
    QApplication.instance() or QApplication([])
    plot = graph("customize-structure")
    plot.plot("sensor", [0.0, 1.0], [1.0, 2.0])
    plot.plot("reference", [0.0, 1.0], [2.0, 1.0])
    captured: list[QDialog] = []

    def inspect(dialog: QDialog) -> None:
        captured.append(dialog)
        assert dialog.objectName() == "pyqtLabGraphCustomizeDialog"
        assert dialog.isModal() is False
        assert dialog.windowModality() == Qt.WindowModality.NonModal
        assert [dialog.tabs.tabText(index) for index in range(dialog.tabs.count())] == [
            "Global",
            "sensor",
            "reference",
        ]
        assert group_sections(dialog, 0) == [
            ("Axes", ["X label:", "X units:", "X mode:", "X logarithmic:",
                       "Y label:", "Y units:", "Y mode:", "Y logarithmic:"]),
            ("View ranges", ["X range:", "Y range:"]),
            ("Appearance", ["Plot background:", "Plot style:", "Grid:"]),
            ("Rendering", ["Anti-aliasing:", "Downsampling:", "Clip to view:",
                            "Adaptive rendering:"]),
            ("Layout saving", ["Restore view on load:"]),
        ]
        assert group_sections(dialog, 1) == [
            ("Curve", ["Visibility:"]),
            ("Line", ["Line:", "Line color:", "Line width:"]),
            ("Markers", ["Markers:", "Marker shape:", "Marker size:",
                          "Filled markers:", "Marker outline width:"]),
        ]
        assert child(dialog, QPushButton, "pyqtLabGraphApplyAndCloseButton").text() == "Apply && Close"
        assert child(dialog, QPushButton, "pyqtLabGraphSaveLayoutButton").text() == "Save Layout"
        assert child(dialog, QPushButton, "pyqtLabGraphPreviewXRangeButton").text() == "Preview Range"
        assert child(dialog, QPushButton, "pyqtLabGraphPreviewYRangeButton").text() == "Preview Range"
        hint = child(dialog, QLabel, "pyqtLabGraphCustomizePreviewHint")
        assert "previewed live" in hint.text()
        assert "Cancel restores" in hint.text()
        assert hint.styleSheet() == ""
        assert dialog.styleSheet() == ""
        assert dialog.findChild(QPushButton, "pyqtLabGraphApplyAndSaveLayoutButton") is None
        assert dialog.findChild(QPushButton, "pyqtLabGraphApplyXRangeButton") is None

    show_with_callback(plot, inspect)
    assert not hasattr(plot, "_pyqt_lab_graph_customize_dialogs")
    dialog = captured[0]
    assert plot.findChild(QDialog, "pyqtLabGraphCustomizeDialog") is dialog
    plot.show_customize_dialog("reference")
    assert dialog.tabs.currentIndex() == 2
    assert len(captured) == 1
    dialog.reject()

    empty = graph("customize-empty")
    show_with_callback(empty, assert_empty)
    print("customize dialog structure smoke ok")


def assert_empty(dialog: QDialog) -> None:
    assert dialog.tabs.count() == 1
    dialog.reject()


if __name__ == "__main__":
    main()
