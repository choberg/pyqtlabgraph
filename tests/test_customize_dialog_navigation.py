from __future__ import annotations

import pytest
from customize_helpers import child, graph, show_with_callback
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
)

_ZOOM_X = (2.0, 4.0)
_ZOOM_Y = (1.0, 1.5)


def _navigate(plot) -> None:  # type: ignore[no-untyped-def]
    """Zoom like a mouse interaction in the plot, outside the dialog."""
    plot.native_view_box.setRange(xRange=_ZOOM_X, yRange=_ZOOM_Y, padding=0.0)


def _finish(dialog: QDialog, action: str) -> None:
    if action == "apply":
        child(dialog, QPushButton, "pyqtLabGraphApplyButton").click()
        dialog.reject()
    elif action == "apply_and_close":
        dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
    else:
        dialog.reject()


@pytest.mark.parametrize("action", ["apply", "apply_and_close", "cancel"])
def test_plot_navigation_while_customizing_is_kept(qapp: QApplication, action: str) -> None:
    plot = graph(f"customize-navigation-{action}")
    plot.plot("sensor", [0.0, 10.0], [0.0, 2.0])

    def navigate_then_finish(dialog: QDialog) -> None:
        child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Edited")
        _navigate(plot)
        _finish(dialog, action)

    show_with_callback(plot, navigate_then_finish)

    assert plot.get_x_range() == pytest.approx(_ZOOM_X)
    assert plot.get_y_range() == pytest.approx(_ZOOM_Y)
    assert not plot.interaction_state.autoscale_x
    assert plot.x_label == ("X" if action == "cancel" else "Edited")


def test_apply_updates_range_fields_to_the_navigated_view(qapp: QApplication) -> None:
    plot = graph("customize-navigation-fields")
    plot.plot("sensor", [0.0, 10.0], [0.0, 2.0])

    def navigate_then_apply(dialog: QDialog) -> None:
        _navigate(plot)
        child(dialog, QPushButton, "pyqtLabGraphApplyButton").click()
        assert child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").value() == pytest.approx(2.0)
        assert child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin").value() == pytest.approx(4.0)
        dialog.reject()

    show_with_callback(plot, navigate_then_apply)
    assert plot.get_x_range() == pytest.approx(_ZOOM_X)


def test_edited_range_fields_are_still_applied(qapp: QApplication) -> None:
    plot = graph("customize-edited-range")
    plot.plot("sensor", [0.0, 10.0], [0.0, 2.0])

    def edit_range_then_accept(dialog: QDialog) -> None:
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").setValue(5.0)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin").setValue(6.0)
        dialog.accept()

    show_with_callback(plot, edit_range_then_accept)
    assert plot.get_x_range() == pytest.approx((5.0, 6.0))


def test_cancel_reverts_a_range_the_dialog_previewed(qapp: QApplication) -> None:
    plot = graph("customize-preview-range-cancel")
    plot.plot("sensor", [0.0, 10.0], [0.0, 2.0])
    before_x = plot.get_x_range()

    def preview_range_then_cancel(dialog: QDialog) -> None:
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").setValue(5.0)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin").setValue(6.0)
        child(dialog, QPushButton, "pyqtLabGraphPreviewXRangeButton").click()
        assert plot.get_x_range() == pytest.approx((5.0, 6.0))
        dialog.reject()

    show_with_callback(plot, preview_range_then_cancel)
    assert plot.get_x_range() == pytest.approx(before_x)
    assert plot.interaction_state.autoscale_x


def test_cancel_after_log_preview_restores_the_linear_view(qapp: QApplication) -> None:
    plot = graph("customize-log-cancel")
    plot.plot("sensor", [1.0, 100.0], [1.0, 2.0])
    before_x = plot.get_x_range()

    def log_then_navigate_then_cancel(dialog: QDialog) -> None:
        child(dialog, QCheckBox, "pyqtLabGraphXLogCheckbox").setChecked(True)
        plot.native_view_box.setXRange(0.5, 1.5, padding=0.0)
        dialog.reject()

    show_with_callback(plot, log_then_navigate_then_cancel)
    assert not plot.x_log
    assert plot.get_x_range() == pytest.approx(before_x)


def test_cancel_keeps_y_navigation_after_x_range_preview(qapp: QApplication) -> None:
    plot = graph("customize-preview-x-keeps-y")
    plot.plot("sensor", [0.0, 10.0], [0.0, 2.0])

    def navigate_y_then_preview_x_then_cancel(dialog: QDialog) -> None:
        plot.native_view_box.setYRange(*_ZOOM_Y, padding=0.0)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMinSpin").setValue(5.0)
        child(dialog, QDoubleSpinBox, "pyqtLabGraphXMaxSpin").setValue(6.0)
        child(dialog, QPushButton, "pyqtLabGraphPreviewXRangeButton").click()
        dialog.reject()

    show_with_callback(plot, navigate_y_then_preview_x_then_cancel)
    assert plot.get_x_range() == pytest.approx((0.0, 10.0))
    assert plot.get_y_range() == pytest.approx(_ZOOM_Y)
