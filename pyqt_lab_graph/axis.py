from __future__ import annotations

import pyqtgraph as pg


class AxisMode:
    AUTO = "auto"
    LINEAR = "linear"
    TIME = "time"


class SmartAxisItem(pg.AxisItem):
    """Axis item with support for relative time formatting and raw linear units."""

    def __init__(self, orientation: str, *args: object, **kwargs: object) -> None:
        self._mode = AxisMode.AUTO
        self._custom_units = ""
        super().__init__(orientation, *args, **kwargs)

    def set_mode(self, mode: str) -> None:
        self._mode = mode
        if mode == AxisMode.LINEAR:
            self.enableAutoSIPrefix(False)
        elif mode == AxisMode.TIME:
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

        # Time formatting logic
        result = []
        for v in values:
            result.append(self._format_time(v, spacing))
        return result

    def _format_time(self, seconds: float, spacing: float) -> str:
        if seconds < 0:
            return f"-{self._format_time(-seconds, spacing)}"

        s = int(seconds)
        ms = seconds - s
        
        days = s // 86400
        hours = (s % 86400) // 3600
        minutes = (s % 3600) // 60
        secs = s % 60

        parts = []
        if days > 0:
            parts.append(f"{days} d")
        if hours > 0:
            parts.append(f"{hours} h")
        if minutes > 0:
            parts.append(f"{minutes} min")
        
        # Determine if we should show seconds or sub-seconds
        # If spacing is small enough, show decimals
        if spacing < 1.0:
            # How many decimals?
            if spacing < 0.001:
                fmt = f"{secs + ms:.3f}"
            elif spacing < 0.01:
                fmt = f"{secs + ms:.2f}"
            else:
                fmt = f"{secs + ms:.1f}"
            parts.append(f"{fmt} s")
        elif secs > 0 or not parts:
            parts.append(f"{secs} s")

        return " ".join(parts)


