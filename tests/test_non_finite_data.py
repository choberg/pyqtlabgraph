from __future__ import annotations

import math

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import PyQtLabGraphWidget


def _assert_finite_ranges(plot: PyQtLabGraphWidget) -> None:
    assert all(math.isfinite(value) for value in plot.get_x_range())
    assert all(math.isfinite(value) for value in plot.get_y_range())


@pytest.mark.parametrize("gap", [np.nan, np.inf, -np.inf])
def test_autoscale_ignores_non_finite_y_values(qapp: QApplication, gap: float) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="non-finite-y")
    plot.plot("signal", [0.0, 1.0, 2.0, 3.0], [1.0, gap, 3.0, 5.0])

    assert plot.get_x_range() == pytest.approx((0.0, 3.0))
    assert plot.get_y_range() == pytest.approx((0.6, 5.4))


@pytest.mark.parametrize("gap", [np.nan, np.inf, -np.inf])
def test_autoscale_ignores_non_finite_x_values(qapp: QApplication, gap: float) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="non-finite-x")
    plot.plot("signal", [gap, 1.0, 2.0, 4.0], [1.0, 2.0, 3.0, 4.0])

    assert plot.get_x_range() == pytest.approx((1.0, 4.0))
    _assert_finite_ranges(plot)


def test_all_non_finite_data_keeps_current_range(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="all-nan")
    before_x, before_y = plot.get_x_range(), plot.get_y_range()
    plot.plot("signal", [np.nan, np.nan], [np.nan, np.inf])

    assert plot.get_x_range() == pytest.approx(before_x)
    assert plot.get_y_range() == pytest.approx(before_y)


def test_rolling_window_ignores_non_finite_x_values(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="rolling-nan", rolling_window_size=2.0)
    plot.plot("signal", [0.0, 5.0, np.inf, np.nan], [1.0, 2.0, 3.0, 4.0])
    plot.request_rolling_x(True)

    assert plot.get_x_range() == pytest.approx((3.0, 5.0))


def test_log_autoscale_ignores_non_finite_and_non_positive_values(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="log-nan")
    plot.plot("signal", [1.0, 10.0, 100.0, 1000.0], [np.nan, -1.0, 10.0, 1000.0])
    plot.set_x_log(True)
    plot.set_y_log(True)

    assert plot.get_x_range() == pytest.approx((0.0, 3.0))
    assert plot.get_y_range() == pytest.approx((0.8, 3.2))
    _assert_finite_ranges(plot)


def test_add_point_accepts_nan_gap(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="add-point-nan")
    plot.add_curve("signal")
    for x_value, y_value in ((0.0, 1.0), (1.0, np.nan), (2.0, 3.0)):
        plot.add_point("signal", x_value, y_value)

    assert plot.get_y_range() == pytest.approx((0.8, 3.2))
