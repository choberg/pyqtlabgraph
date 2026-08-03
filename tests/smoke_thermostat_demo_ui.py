from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from demo_thermostat import ThermostatDemoWindow
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QPushButton, QWidget


def main() -> None:
    app = QApplication.instance() or QApplication([])
    ui_path = Path(__file__).resolve().parents[1] / "examples" / "demo_thermostat.ui"
    with TemporaryDirectory() as directory:
        layout_path = Path(directory) / "thermostat.layout.json"
        window = ThermostatDemoWindow(ui_path, layout_path=layout_path)

        for widget_name in ("plotContainer", "toolbarContainer", "legendContainer"):
            assert window.window.findChild(QWidget, widget_name) is not None
        for button_name in ("startButton", "stopButton", "addPointsButton"):
            assert window.window.findChild(QPushButton, button_name) is not None

        assert window.live_plot.plot_identifier == "thermostat-live"
        assert window.toolbar.plot is window.live_plot
        assert window.legend.plot is window.live_plot
        dark_mode_action = window.window.findChild(QAction, "demoDarkModeAction")
        assert dark_mode_action is not None
        assert not hasattr(window.live_plot, "toolbar")
        assert not hasattr(window.live_plot, "legend")

        window.show()
        app.processEvents()
        dark_mode_action.setChecked(True)
        app.processEvents()
        assert window.live_plot.theme.name == "dark"
        assert window.live_plot.plot_style.name == "dark"

        window.window.close()
        app.processEvents()

    print("thermostat demo ui smoke ok")


if __name__ == "__main__":
    main()
