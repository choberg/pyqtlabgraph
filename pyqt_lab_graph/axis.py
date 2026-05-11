from __future__ import annotations

from enum import Enum

import pyqtgraph as pg


_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 60 * _SECONDS_PER_MINUTE
_SECONDS_PER_DAY = 24 * _SECONDS_PER_HOUR

_SUBSECOND_SPACING = 1.0
_CENTISECOND_SPACING = 0.01
_MILLISECOND_SPACING = 0.001


class AxisMode(str, Enum):
    AUTO = "auto"
    LINEAR = "linear"
    TIME = "time"


def resolve_axis_mode(mode: str | AxisMode) -> AxisMode:
    if isinstance(mode, AxisMode):
        return mode

    try:
        return AxisMode(mode)
    except ValueError as exc:
        available = ", ".join(axis_mode.value for axis_mode in AxisMode)
        raise ValueError(
            f'Unknown PyQtLabGraph axis mode "{mode}". '
            f"Available axis modes: {available}."
        ) from exc


class SmartAxisItem(pg.AxisItem):
    """Axis item with support for relative time formatting and raw linear units."""

    def __init__(self, orientation: str, *args: object, **kwargs: object) -> None:
        self._mode = AxisMode.AUTO
        self._custom_units = ""
        super().__init__(orientation, *args, **kwargs)

    def set_mode(self, mode: str | AxisMode) -> None:
        self._mode = resolve_axis_mode(mode)
        if self._mode == AxisMode.LINEAR:
            self.enableAutoSIPrefix(False)
        elif self._mode == AxisMode.TIME:
            self.enableAutoSIPrefix(False)
        else:
            self.enableAutoSIPrefix(True)
        self.readjust_labels()

    def set_units(self, units: str | None) -> None:
        self._custom_units = units or ""
        # If in time mode, we don't use the standard unit display in the label
        # because the unit is attached to each tick.
        if self._mode == AxisMode.TIME:
            super().setLabel(units=None)
        else:
            super().setLabel(units=units)

    def setLabel(self, text: str | None = None, units: str | None = None, **args: object) -> None:
        self._custom_units = units or ""
        if self._mode == AxisMode.TIME:
            super().setLabel(text=text, units=None, **args)
        else:
            super().setLabel(text=text, units=units, **args)

    def readjust_labels(self) -> None:
        # Trigger a refresh of the labels by re-setting the unit
        self.setLabel(units=self._custom_units)

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        if self._mode != AxisMode.TIME:
            return super().tickStrings(values, scale, spacing)

        return [self._format_time(value, spacing) for value in values]

    def _format_time(self, seconds: float, spacing: float) -> str:
        if seconds < 0:
            return f"-{self._format_time(-seconds, spacing)}"

        s = int(seconds)
        ms = seconds - s
        
        days = s // _SECONDS_PER_DAY
        hours = (s % _SECONDS_PER_DAY) // _SECONDS_PER_HOUR
        minutes = (s % _SECONDS_PER_HOUR) // _SECONDS_PER_MINUTE
        secs = s % _SECONDS_PER_MINUTE

        parts = []
        if days > 0:
            parts.append(f"{days} d")
        if hours > 0:
            parts.append(f"{hours} h")
        if minutes > 0:
            parts.append(f"{minutes} min")
        
        if spacing < _SUBSECOND_SPACING:
            if spacing < _MILLISECOND_SPACING:
                fmt = f"{secs + ms:.3f}"
            elif spacing < _CENTISECOND_SPACING:
                fmt = f"{secs + ms:.2f}"
            else:
                fmt = f"{secs + ms:.1f}"
            parts.append(f"{fmt} s")
        elif secs > 0 or not parts:
            parts.append(f"{secs} s")

        return " ".join(parts)
