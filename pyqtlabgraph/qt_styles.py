from __future__ import annotations


def host_frame_fallback_style(object_name: str) -> str:
    return f"""
        QFrame#{object_name} {{
            background-color: palette(window);
            border: 1px solid palette(mid);
            border-radius: 6px;
        }}
    """


def plot_widget_chrome_style() -> str:
    return """
        QGraphicsView#pyqtLabGraphPlotWidget {
            background: transparent;
            border: none;
            border-radius: 0px;
        }
    """
