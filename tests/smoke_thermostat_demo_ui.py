from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import QApplication, QPushButton, QWidget

from demo_thermostat import ThermostatDemoWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    ui_path = Path(__file__).resolve().parents[1] / "demo_thermostat.ui"
    window = ThermostatDemoWindow(ui_path)

    for widget_name in ("plotContainer", "toolbarContainer", "legendContainer"):
        assert window.window.findChild(QWidget, widget_name) is not None
    for button_name in ("startButton", "stopButton", "addPointsButton"):
        assert window.window.findChild(QPushButton, button_name) is not None

    assert window.live_plot.plot_identifier == "thermostat-live"
    assert window.live_plot.toolbar is not None
    assert window.live_plot.legend is not None

    window.window.close()
    app.processEvents()
    print("thermostat demo ui smoke ok")


if __name__ == "__main__":
    main()
