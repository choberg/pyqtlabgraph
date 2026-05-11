from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from pyqt_lab_graph import CurveStyle, LayoutFileError, PyQtLabGraphWidget
from pyqt_lab_graph import dialogs


def _container() -> QWidget:
    widget = QWidget()
    widget.setLayout(QVBoxLayout())
    return widget


def _child(dialog: QDialog, widget_type: type, name: str):
    widget = dialog.findChild(widget_type, name)
    assert widget is not None, f"Missing dialog control: {name}"
    return widget


def _set_combo_data(combo: QComboBox, data: object) -> None:
    index = combo.findData(data)
    assert index >= 0, f"Missing combo data: {data!r}"
    combo.setCurrentIndex(index)


def _graph(identifier: str, layout_path: Path | None = None) -> PyQtLabGraphWidget:
    return PyQtLabGraphWidget(
        _container(),
        plot_identifier=identifier,
        layout_path=layout_path,
        show_toolbar=False,
        show_legend=False,
    )


def main() -> None:
    app = QApplication.instance() or QApplication([])

    try:
        PyQtLabGraphWidget(_container())
    except TypeError:
        pass
    else:
        raise AssertionError("plot_identifier should be required")

    with TemporaryDirectory() as temp_dir:
        layout_path = Path(temp_dir) / "plot-layout.json"

        source = _graph("primary", layout_path)
        assert source.load_layout() is False
        source.plot(
            "sensor",
            [0.0, 1.0, 2.0],
            [3.0, 2.0, 1.0],
            style=CurveStyle(line_color="#123456", marker_symbol="o"),
        )
        source.plot("reference", [0.0, 1.0], [1.0, 3.0])
        source.set_axis_labels("Elapsed", "Signal", "s", "V", x_mode="time", y_mode="linear")
        source.set_grid_visible(False)
        source.set_antialiasing_enabled(False)
        source.set_downsampling_enabled(False)
        source.set_clip_to_view_enabled(False)
        source.set_adaptive_performance_enabled(False)
        source.set_theme("dark")
        source.set_plot_style("dark")
        source.set_curve_visible("sensor", False)
        source.set_curve_style(
            "sensor",
            CurveStyle(
                line_enabled=False,
                line_color="#abcdef",
                line_width=3.0,
                marker_symbol="d",
                marker_size=12,
                marker_outline_width=2.0,
                marker_enabled=True,
                marker_filled=True,
            ),
        )
        source.apply_manual_x_limits(4.0, 8.0)
        source.apply_manual_y_limits(-2.0, 6.0)
        source.save_layout(include_x_range=False, include_y_range=True)

        secondary = _graph("secondary", layout_path)
        secondary.set_axis_labels("Other X", "Other Y")
        secondary.save_layout()

        document = json.loads(layout_path.read_text(encoding="utf-8"))
        assert document["version"] == 2
        assert sorted(document["plots"]) == ["primary", "secondary"]
        primary_layout = document["plots"]["primary"]
        assert primary_layout["restore_view_state_on_load"] is True
        assert primary_layout["interaction"]["autoscale_x"] is False
        assert primary_layout["interaction"]["autoscale_y"] is False
        assert primary_layout["interaction"]["rolling_x"] is False
        assert "x" not in primary_layout["ranges"]
        assert primary_layout["ranges"]["y"] == [-2.0, 6.0]

        primary_layout["curves"]["ghost"] = {
            "visible": False,
            "style": {"line_color": "#000000"},
        }
        layout_path.write_text(json.dumps(document), encoding="utf-8")

        target = _graph("primary", layout_path)
        target.plot("sensor", [0.0, 1.0], [1.0, 2.0])
        target.plot("reference", [0.0, 1.0], [2.0, 1.0])
        assert target.load_layout() is True
        assert target.x_label_text == "Elapsed"
        assert target.y_label_text == "Signal"
        assert target.x_label_units == "s"
        assert target.y_label_units == "V"
        assert target.grid_item.isVisible() is False
        assert target.antialiasing_enabled is False
        assert target.downsampling_enabled is False
        assert target.clip_to_view_enabled is False
        assert target.adaptive_performance_enabled is False
        assert target.theme.name == "dark"
        assert target.plot_style.name == "dark"
        assert target.curves["sensor"].visible is False
        assert target.curve_style("sensor").line_color == "#abcdef"
        assert target.curve_style("sensor").line_enabled is False
        assert target.curve_style("sensor").marker_symbol == "d"
        assert target.get_y_range() == (-2.0, 6.0)
        assert target.interaction_state.autoscale_y is False

        document["plots"]["primary"]["restore_view_state_on_load"] = False
        layout_path.write_text(json.dumps(document), encoding="utf-8")

        view_state_target = _graph("primary", layout_path)
        view_state_target.plot("sensor", [0.0, 1.0], [1.0, 2.0])
        view_state_target.plot("reference", [0.0, 1.0], [2.0, 1.0])
        view_state_target.apply_manual_y_limits(10.0, 20.0)
        assert view_state_target.load_layout() is True
        assert view_state_target.theme.name == "dark"
        assert view_state_target.get_y_range() == (10.0, 20.0)

        assert _graph("missing", layout_path).load_layout() is False

        malformed_path = Path(temp_dir) / "malformed.json"
        malformed_path.write_text("{broken", encoding="utf-8")
        try:
            _graph("primary", malformed_path).load_layout()
        except LayoutFileError:
            pass
        else:
            raise AssertionError("Malformed layout JSON should raise LayoutFileError")

        dialog_layout_path = Path(temp_dir) / "dialog-layout.json"
        dialog_graph = _graph("dialog", dialog_layout_path)
        dialog_graph.plot("sensor", [0.0, 1.0], [1.0, 2.0])

        original_show = dialogs.QDialog.show

        def apply_and_save(dialog: QDialog) -> None:
            _child(dialog, QLineEdit, "pyqtLabGraphXLabelEdit").setText("Dialog X")
            _set_combo_data(_child(dialog, QComboBox, "pyqtLabGraphPlotBackgroundCombo"), "dark")
            _child(
                dialog,
                QCheckBox,
                "pyqtLabGraphRestoreViewStateOnLoadCheckbox",
            ).setChecked(False)
            assert dialog.findChild(QCheckBox, "pyqtLabGraphApplyXRangeCheckbox") is None
            assert dialog.findChild(QCheckBox, "pyqtLabGraphApplyYRangeCheckbox") is None
            _child(dialog, QDoubleSpinBox, "pyqtLabGraphYMinSpin").setValue(-4.0)
            _child(dialog, QDoubleSpinBox, "pyqtLabGraphYMaxSpin").setValue(4.0)
            assert dialog_graph.get_y_range() != (-4.0, 4.0)
            _child(dialog, QPushButton, "pyqtLabGraphApplyYRangeButton").click()
            assert dialog_graph.get_y_range() == (-4.0, 4.0)
            _child(dialog, QPushButton, "pyqtLabGraphApplyAndSaveLayoutButton").click()
            dialog.reject()

        dialogs.QDialog.show = apply_and_save
        try:
            dialogs.show_customize_dialog(dialog_graph)
        finally:
            dialogs.QDialog.show = original_show

        dialog_document = json.loads(dialog_layout_path.read_text(encoding="utf-8"))
        dialog_layout = dialog_document["plots"]["dialog"]
        assert dialog_layout["axes"]["x"]["label"] == "Dialog X"
        assert dialog_layout["theme"] == "dark"
        assert dialog_layout["restore_view_state_on_load"] is False
        assert "x" in dialog_layout["ranges"]
        assert dialog_layout["ranges"]["y"] == [-4.0, 4.0]
        assert dialog_graph.x_label_text == "Dialog X"
        assert dialog_graph.theme.name == "dark"
        assert dialog_graph.get_y_range() == (-4.0, 4.0)

    app.processEvents()
    print("layout persistence smoke ok")


if __name__ == "__main__":
    main()
