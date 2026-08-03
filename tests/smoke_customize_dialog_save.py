from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customize_smoke_helpers import child, graph, set_combo_data, show_with_callback
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
)

from pyqtlabgraph import dialogs


def main() -> None:
    QApplication.instance() or QApplication([])
    with TemporaryDirectory() as directory:
        layout_path = Path(directory) / "customize.layout.json"
        plot = graph("customize-save", layout_path=layout_path)
        plot.plot("sensor", [0.0, 1.0], [1.0, 2.0])

        def save_then_cancel(dialog: QDialog) -> None:
            finished: list[int] = []
            dialog.finished.connect(finished.append)
            child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Saved X")
            set_combo_data(child(dialog, QComboBox, "pyqtLabGraphPlotBackgroundCombo"), "dark")
            child(dialog, QCheckBox, "pyqtLabGraphRestoreViewStateOnLoadCheckbox").setChecked(False)
            child(dialog, QDoubleSpinBox, "pyqtLabGraphYMinSpin").setValue(-4.0)
            child(dialog, QDoubleSpinBox, "pyqtLabGraphYMaxSpin").setValue(4.0)
            child(dialog, QPushButton, "pyqtLabGraphSaveLayoutButton").click()
            assert finished == []
            child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Unsaved X")
            set_combo_data(child(dialog, QComboBox, "pyqtLabGraphPlotBackgroundCombo"), "light")
            dialog.reject()

        show_with_callback(plot, save_then_cancel)
        saved = json.loads(layout_path.read_text(encoding="utf-8"))["plots"]["customize-save"]
        assert saved["axes"]["x"]["label"] == "Saved X"
        assert saved["theme"] == "dark"
        assert saved["ranges"]["y"] == [-4.0, 4.0]
        assert saved["restore_view_state_on_load"] is False
        assert plot.x_label_text == "Saved X"
        assert plot.theme.name == "dark"
        assert plot.get_y_range() == (-4.0, 4.0)

    failing = graph("customize-save-failure")
    original_label = failing.x_label_text
    original_critical = dialogs.QMessageBox.critical
    errors: list[str] = []
    dialogs.QMessageBox.critical = lambda _parent, _title, text: errors.append(str(text))

    def fail_save(dialog: QDialog) -> None:
        child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Preview only")
        child(dialog, QPushButton, "pyqtLabGraphSaveLayoutButton").click()
        dialog.reject()

    try:
        show_with_callback(failing, fail_save)
    finally:
        dialogs.QMessageBox.critical = original_critical
    assert errors
    assert failing.x_label_text == original_label
    print("customize dialog save smoke ok")


if __name__ == "__main__":
    main()
