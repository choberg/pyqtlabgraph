from __future__ import annotations


DEFAULT_CURVE_COLORS = [
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
]

DEFAULT_CURVE_COLOR_BY_THEME = {
    False: "#1f77b4",
    True: "#4db6ff",
}

AXIS_ZOOM_COLOR_BY_AXIS = {
    "x": "#1f77b4",
    "y": "#ff7f0e",
}


def default_curve_style(color: str) -> dict[str, object]:
    return {
        "line_enabled": True,
        "line_color": color,
        "line_width": 1.2,
        "marker_symbol": "o",
        "marker_size": 5,
        "marker_enabled": True,
        "marker_filled": True,
    }
