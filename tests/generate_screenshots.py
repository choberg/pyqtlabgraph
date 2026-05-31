# /// script
# dependencies = [
#   "pyqtdarktheme",
#   "numpy",
#   "pyside6",
#   "pyqtgraph",
# ]
# ///

import sys
import os
import numpy as np
from pathlib import Path
import qdarktheme
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt
from pyqtlabgraph import PyQtLabGraphWidget, CurveStyle

def generate():
    app = QApplication(sys.argv)
    
    # Apply a real dark theme to the host application
    app.setStyleSheet(qdarktheme.load_stylesheet("dark"))
    
    # Set up main window
    window = QMainWindow()
    central = QWidget(window)
    layout = QVBoxLayout(central)
    window.setCentralWidget(central)
    
    plot_container = QWidget()
    toolbar_container = QWidget()
    legend_container = QWidget()
    
    layout.addWidget(toolbar_container)
    layout.addWidget(plot_container)
    layout.addWidget(legend_container)
    
    # Initialize widget with horizontal legend
    plot = PyQtLabGraphWidget(
        plot_container=plot_container,
        toolbar_container=toolbar_container,
        legend_container=legend_container,
        plot_identifier="screenshot_gen",
        theme="dark",
        plot_style="dark",
        show_toolbar=True,
        show_legend=True,
        legend_orientation=Qt.Orientation.Horizontal,
    )
    
    # Add mockup data curves
    x = np.linspace(0, 10, 500)
    y_sine = np.sin(x)
    y_cosine = np.cos(x) * 0.7
    np.random.seed(42)
    y_noise = np.sin(2 * x) * 0.2 + np.random.normal(0, 0.04, 500)
    
    plot.plot("sine", x, y_sine, label="Sensor A (Temp)")
    plot.plot("cosine", x, y_cosine, label="Sensor B (Pressure)")
    plot.plot("noise", x, y_noise, label="Sensor C (Noise)")
    
    plot.set_axis_labels("Time", "Measurement", "s", "V")
    
    # Resize and layout
    window.resize(900, 600)
    window.show()
    
    docs_dir = Path(__file__).parent.parent / "docs"
    docs_dir.mkdir(exist_ok=True)
    
    # Process events to allow painting
    QApplication.processEvents()
    
    # 1. Dark theme screenshot
    pixmap = window.grab()
    pixmap.save(str(docs_dir / "screenshot_dark.png"))
    
    # 2. Customize Dialog screenshot
    plot.show_customize_dialog()
    if plot._customize_dialogs:
        dialog = plot._customize_dialogs[0]
        dialog.show()
        QApplication.processEvents()
        dialog_pixmap = dialog.grab()
        dialog_pixmap.save(str(docs_dir / "screenshot_customize_dialog.png"))
        dialog.close()
    
    # 3. Light theme (white background + light styles) screenshot
    # Switch host application style sheet to light
    app.setStyleSheet(qdarktheme.load_stylesheet("light"))
    plot.set_theme("light")
    plot.apply_plot_style("light")
    QApplication.processEvents()
    pixmap = window.grab()
    pixmap.save(str(docs_dir / "screenshot_light.png"))
    
    # Close main window before alternative layout
    window.close()
    
    # 4. Alternative layout screenshot (light theme, vertical legend on right, toolbar below)
    window_alt = QMainWindow()
    central_alt = QWidget(window_alt)
    layout_alt = QVBoxLayout(central_alt)
    window_alt.setCentralWidget(central_alt)
    
    middle_widget = QWidget()
    middle_layout = QHBoxLayout(middle_widget)
    middle_layout.setContentsMargins(0, 0, 0, 0)
    middle_layout.setSpacing(8)
    
    plot_container_alt = QWidget()
    legend_container_alt = QWidget()
    toolbar_container_alt = QWidget()
    
    middle_layout.addWidget(plot_container_alt, stretch=1)
    middle_layout.addWidget(legend_container_alt)
    
    layout_alt.addWidget(middle_widget, stretch=1)
    layout_alt.addWidget(toolbar_container_alt)
    
    plot_alt = PyQtLabGraphWidget(
        plot_container=plot_container_alt,
        toolbar_container=toolbar_container_alt,
        legend_container=legend_container_alt,
        plot_identifier="screenshot_alt",
        theme="light",
        plot_style="light",
        show_toolbar=True,
        show_legend=True,
        legend_orientation=Qt.Orientation.Vertical,
    )
    
    # Define custom curve styles
    # 1. Line + Marker
    style1 = CurveStyle(
        line_enabled=True,
        line_color="#1f77b4",
        line_width=2.0,
        marker_enabled=True,
        marker_filled=True,
        marker_symbol="o",
        marker_size=9,
        marker_outline_width=1.0
    )
    # 2. Only Marker
    style2 = CurveStyle(
        line_enabled=False,
        line_color="#ff7f0e",
        line_width=2.0,
        marker_enabled=True,
        marker_filled=True,
        marker_symbol="s",
        marker_size=9,
        marker_outline_width=1.0
    )
    # 3. Only Line
    style3 = CurveStyle(line_enabled=True, line_color="#2ca02c", line_width=2.0, marker_enabled=False)
    # 4. Only Line
    style4 = CurveStyle(line_enabled=True, line_color="#d62728", line_width=2.0, marker_enabled=False)
    # 5. Only Line
    style5 = CurveStyle(line_enabled=True, line_color="#9467bd", line_width=2.0, marker_enabled=False)
    
    x_alt = np.linspace(0, 10, 100)
    plot_alt.plot("curve1", x_alt, np.sin(x_alt), label="System A (Temp)", style=style1)
    plot_alt.plot("curve2", x_alt, np.cos(x_alt) * 0.7, label="System B (Pressure)", style=style2)
    plot_alt.plot("curve3", x_alt, np.sin(x_alt * 0.5) * 0.5 - 0.2, label="System C (Flow)", style=style3)
    plot_alt.plot("curve4", x_alt, np.cos(x_alt * 0.5) * 0.3 - 0.5, label="System D (Level)", style=style4)
    plot_alt.plot("curve5", x_alt, np.sin(x_alt * 2.0) * 0.15 + 0.5, label="System E (Humidity)", style=style5)
    
    plot_alt.set_axis_labels("Time", "Value", "s", "V")
    
    window_alt.resize(950, 600)
    window_alt.show()
    
    QApplication.processEvents()
    pixmap_alt = window_alt.grab()
    pixmap_alt.save(str(docs_dir / "screenshot_alternative_layout.png"))
    window_alt.close()
    
    print(f"All screenshots generated and saved successfully under {docs_dir}/!")

if __name__ == "__main__":
    generate()
