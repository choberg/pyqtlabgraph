from __future__ import annotations

import sys
from pathlib import Path

import qdarktheme
from PySide6.QtWidgets import QApplication

from demo_thermostat import ThermostatDemoWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    ui_path = Path(__file__).resolve().parent / "demo_thermostat.ui"
    window = ThermostatDemoWindow(
        ui_path,
        plot_identifier="thermostat-live-qdarktheme",
        layout_path=Path.cwd() / "demo_thermostat_qdarktheme.layout.json",
        theme="dark",
        plot_style="dark",
        window_title="PyQtLabGraph Thermostat Demo - PyQtDarkTheme",
    )
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
