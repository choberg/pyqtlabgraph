import sys
import os
import numpy as np
from pathlib import Path
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout
from pyqtlabgraph import PyQtLabGraphWidget

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
    
    # Initialize widget
    plot = PyQtLabGraphWidget(
        plot_container=plot_container,
        toolbar_container=toolbar_container,
        legend_container=legend_container,
        plot_identifier="screenshot_gen",
        theme="dark",
        plot_style="dark",
        show_toolbar=True,
        show_legend=True,
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
    
    # 3. Light solarized theme screenshot
    plot.set_theme("light-solarized")
    plot.apply_plot_style("solarized")
    QApplication.processEvents()
    pixmap = window.grab()
    pixmap.save(str(docs_dir / "screenshot_light_solarized.png"))
    
    print(f"All screenshots generated and saved successfully under {docs_dir}/!")

if __name__ == "__main__":
    generate()
