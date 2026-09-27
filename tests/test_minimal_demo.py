from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from demo_minimal import create_window
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication


def test_minimal_demo() -> None:
    app = QApplication.instance() or QApplication([])
    previous_directory = Path.cwd()
    with TemporaryDirectory() as directory:
        try:
            os.chdir(directory)
            window = create_window()
        finally:
            os.chdir(previous_directory)

        action = window.findChild(QAction, "demoDarkModeAction")
        assert action is not None
        assert window.graph.theme.name == "light"
        window.show()
        app.processEvents()
        action.setChecked(True)
        app.processEvents()
        assert window.graph.theme.name == "dark"
        assert window.graph.curve_palette.name == "default-dark"
        window.close()
        app.processEvents()
