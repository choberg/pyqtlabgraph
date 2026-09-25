from __future__ import annotations

from dataclasses import dataclass, replace

from PySide6.QtGui import QColor


@dataclass(frozen=True)
class CurveStyle:
    line_enabled: bool = True
    line_color: str = "#0072B2"
    line_width: float = 1.0
    marker_symbol: str = "s"
    marker_size: int = 5
    marker_outline_width: float = 1.0
    marker_enabled: bool = True
    marker_filled: bool = False

    def __post_init__(self) -> None:
        if not QColor(self.line_color).isValid():
            raise ValueError(f"Invalid line_color color: {self.line_color}")
        if self.line_width <= 0.0:
            raise ValueError("Curve line_width must be greater than zero.")
        if self.marker_size <= 0:
            raise ValueError("Curve marker_size must be greater than zero.")
        if self.marker_outline_width < 0.0:
            raise ValueError("Curve marker_outline_width must not be negative.")

    def with_overrides(self, **overrides: object) -> "CurveStyle":
        return replace(self, **overrides)  # type: ignore[arg-type]
