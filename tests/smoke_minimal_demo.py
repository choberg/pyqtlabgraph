from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from demo_minimal import create_window
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication


def main() -> None:
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
        assert window.graph.plot_style.name == "dark"
        window.close()
        app.processEvents()

    print("minimal demo smoke ok")


if __name__ == "__main__":
    main()
