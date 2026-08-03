# /// script
# dependencies = [
#   "numpy",
#   "pyside6",
#   "pyqtgraph",
# ]
# ///

import sys
from pathlib import Path

import numpy as np
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QMainWindow, QVBoxLayout, QWidget

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))

from _demo_theme import apply_demo_theme
from demo_cursor import create_window as create_cursor_demo_window

from pyqtlabgraph import (
    CurveStyle,
    PyQtLabGraphLegend,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)


def generate():
    app = QApplication(sys.argv)
    
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
        plot_identifier="screenshot_gen",
        theme="dark",
        plot_style="dark",
    )
    toolbar = PyQtLabGraphToolbar(plot)
    legend = PyQtLabGraphLegend(plot, orientation=Qt.Orientation.Horizontal)
    QVBoxLayout(plot_container).addWidget(plot)
    QVBoxLayout(toolbar_container).addWidget(toolbar)
    QVBoxLayout(legend_container).addWidget(legend)
    
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
    apply_demo_theme(app, plot, dark_mode=True)
    
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
    dialog = plot.findChild(QDialog, "pyqtLabGraphCustomizeDialog")
    if dialog is not None:
        dialog.show()
        QApplication.processEvents()
        dialog_pixmap = dialog.grab()
        dialog_pixmap.save(str(docs_dir / "screenshot_customize_dialog.png"))
        dialog.close()
    
    # 3. Light theme (white background + light styles) screenshot
    apply_demo_theme(app, plot, dark_mode=False)
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
        plot_identifier="screenshot_alt",
        theme="light",
        plot_style="light",
    )
    toolbar_alt = PyQtLabGraphToolbar(plot_alt)
    legend_alt = PyQtLabGraphLegend(plot_alt, orientation=Qt.Orientation.Vertical)
    QVBoxLayout(plot_container_alt).addWidget(plot_alt)
    QVBoxLayout(toolbar_container_alt).addWidget(toolbar_alt)
    QVBoxLayout(legend_container_alt).addWidget(legend_alt)
    
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
    
    # Save clean alternative layout screenshot
    pixmap_alt = window_alt.grab()
    pixmap_alt.save(str(docs_dir / "screenshot_alternative_layout.png"))
    
    # Save labeled screenshot with outlines and badges
    # Grab a fresh copy for drawing
    pixmap_labeled = window_alt.grab()
    painter = QPainter(pixmap_labeled)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    # Determine widget coordinates relative to window
    # Map coordinates from widget space to window space
    plot_pos = plot_container_alt.mapTo(window_alt, QPoint(0, 0))
    plot_w, plot_h = plot_container_alt.width(), plot_container_alt.height()
    
    legend_pos = legend_container_alt.mapTo(window_alt, QPoint(0, 0))
    legend_w, legend_h = legend_container_alt.width(), legend_container_alt.height()
    
    toolbar_pos = toolbar_container_alt.mapTo(window_alt, QPoint(0, 0))
    toolbar_w, toolbar_h = toolbar_container_alt.width(), toolbar_container_alt.height()
    
    # Draw blue outlines (slightly padded inwards or outwards to align nicely)
    outline_pen = QPen(QColor("#3b82f6"), 4) # Modern blue highlight
    painter.setPen(outline_pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    
    painter.drawRect(plot_pos.x(), plot_pos.y(), plot_w, plot_h)
    painter.drawRect(legend_pos.x(), legend_pos.y(), legend_w, legend_h)
    painter.drawRect(toolbar_pos.x(), toolbar_pos.y(), toolbar_w, toolbar_h)
    
    # Helper to draw circular badge with bold number
    def draw_badge(number, x, y):
        # Draw background shadow circle
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
        painter.drawEllipse(x + 2, y + 2, 32, 32)
        
        # Draw blue circle
        painter.setBrush(QBrush(QColor("#3b82f6")))
        painter.drawEllipse(x, y, 32, 32)
        
        # Draw white bold number
        painter.setPen(QPen(Qt.GlobalColor.white))
        font = QFont("Helvetica", 14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(x, y, 32, 32, Qt.AlignmentFlag.AlignCenter, number)

    # Place badges in top-left corners of the widgets
    draw_badge("1", plot_pos.x() + 12, plot_pos.y() + 12)
    draw_badge("2", legend_pos.x() + 12, legend_pos.y() + 12)
    draw_badge("3", toolbar_pos.x() + 12, toolbar_pos.y() + 12)
    
    painter.end()
    pixmap_labeled.save(str(docs_dir / "screenshot_layout_labeled.png"))
    
    window_alt.close()

    # 5. Cursor inspector with a paired X measurement
    cursor_window = create_cursor_demo_window(load_saved_layout=False)
    cursor_window.graph.add_cursor_pair(
        "free_x",
        "signal_snap",
        key="screenshot_pair",
    )
    cursor_window.show()
    QApplication.processEvents()
    cursor_window.grab().save(str(docs_dir / "screenshot_cursor_widget.png"))
    cursor_window.close()

    print(f"All screenshots generated and saved successfully under {docs_dir}/!")

if __name__ == "__main__":
    generate()
