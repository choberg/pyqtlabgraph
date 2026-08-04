from __future__ import annotations

import json
import os
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QDialog, QTabWidget, QWidget

from pyqtlabgraph import (
    BUILTIN_COLOR_GRADIENTS,
    BUILTIN_CURVE_PALETTES,
    CurveStyle,
    LayoutFileError,
    PyQtLabGraphColorGradient,
    PyQtLabGraphCurvePalette,
    PyQtLabGraphStyleRegistry,
    PyQtLabGraphWidget,
    TracePersistenceConfig,
    customize_controls,
    dialogs,
)


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_palette_and_gradient_values_are_validated_and_frozen() -> None:
    with pytest.raises(ValueError):
        PyQtLabGraphCurvePalette("empty", ())
    with pytest.raises(ValueError):
        PyQtLabGraphCurvePalette("bad", ("not-a-color",))
    with pytest.raises(ValueError, match="strictly increasing"):
        PyQtLabGraphColorGradient("bad", (0.0, 0.0), ("#000000", "#ffffff"))
    with pytest.raises(ValueError, match="same length"):
        PyQtLabGraphColorGradient("bad", (0.0, 1.0), ("#000000",))
    palette = PyQtLabGraphCurvePalette("custom", ("#123456",))
    with pytest.raises(FrozenInstanceError):
        palette.name = "changed"  # type: ignore[misc]


def test_registry_exposes_ten_palettes_and_gradients() -> None:
    registry = PyQtLabGraphStyleRegistry()
    assert len(BUILTIN_CURVE_PALETTES) == 10
    assert len(BUILTIN_COLOR_GRADIENTS) == 10
    assert registry.resolve_curve_palette(" OKABE-ITO ").name == "okabe-ito"
    assert registry.resolve_color_gradient("ViRiDiS").name == "viridis"


def test_palette_cycles_and_preserves_non_color_style(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="palette")
    assert plot.curve_palette.name == "default-light"
    original = CurveStyle(line_color="#112233", line_width=3.0, marker_symbol="d", marker_size=9)
    plot.add_curve("first", style=original)
    for index in range(1, 9):
        plot.add_curve(str(index))
    plot.set_curve_palette("okabe-ito")

    updated = plot.curve_style("first")
    assert updated.line_color == "#e69f00"
    assert updated.line_width == original.line_width
    assert updated.marker_symbol == original.marker_symbol
    assert updated.marker_size == original.marker_size
    assert plot.curve_style("8").line_color == updated.line_color

    plot.set_theme("dark")
    assert plot.curve_palette.name == "okabe-ito"
    with pytest.raises(TypeError, match="palette"):
        plot.set_curve_palette(None)  # type: ignore[arg-type]


def test_palette_combo_shows_six_discrete_colors_and_full_tooltip(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="palette-combo")
    parent = QWidget()
    controls = customize_controls.build_global_tab(plot, parent, QTabWidget(parent))
    combo = controls.curve_palette
    index = combo.findData("plotly-safe")
    palette = BUILTIN_CURVE_PALETTES["plotly-safe"]

    assert index >= 0
    assert combo.currentData() == "default-light"
    assert not combo.itemIcon(index).isNull()
    image = combo.itemIcon(index).pixmap(combo.iconSize()).toImage()
    swatch_width = combo.iconSize().width() // 6
    for color_index, color in enumerate(palette.colors[:6]):
        sampled = image.pixelColor(
            color_index * swatch_width + swatch_width // 2,
            combo.iconSize().height() // 2,
        )
        assert sampled == QColor(color)
    tooltip = str(combo.itemData(index, Qt.ItemDataRole.ToolTipRole))
    assert tooltip.startswith("Colors: ")
    assert QColor(palette.colors[-1]).name() in tooltip


def test_gradient_combo_shows_continuous_gradients_and_reverses_icons(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="gradient-combo")
    parent = QWidget()
    controls = customize_controls.build_global_tab(plot, parent, QTabWidget(parent))
    combo = controls.gradient
    index = combo.findData("viridis")
    gradient = BUILTIN_COLOR_GRADIENTS["viridis"]

    assert index >= 0
    assert combo.itemText(index) == "Viridis"
    assert not combo.itemIcon(index).isNull()
    image = combo.itemIcon(index).pixmap(combo.iconSize()).toImage()
    left = image.pixelColor(0, combo.iconSize().height() // 2)
    right = image.pixelColor(combo.iconSize().width() - 1, combo.iconSize().height() // 2)
    assert _color_distance(left, QColor(gradient.colors[0])) <= 5
    assert _color_distance(right, QColor(gradient.colors[-1])) <= 5

    customize_controls._update_gradient_combo_icons(
        combo,
        plot.style_registry.color_gradients,
        reverse=True,
    )
    reversed_image = combo.itemIcon(index).pixmap(combo.iconSize()).toImage()
    reversed_left = reversed_image.pixelColor(0, combo.iconSize().height() // 2)
    reversed_right = reversed_image.pixelColor(
        combo.iconSize().width() - 1,
        combo.iconSize().height() // 2,
    )
    assert _color_distance(reversed_left, QColor(gradient.colors[-1])) <= 5
    assert _color_distance(reversed_right, QColor(gradient.colors[0])) <= 5


def _color_distance(first: QColor, second: QColor) -> int:
    return max(
        abs(first.red() - second.red()),
        abs(first.green() - second.green()),
        abs(first.blue() - second.blue()),
    )


def test_curve_color_methods_start_neutral_and_preview_live(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="curve-color-methods")
    for key in ("first", "second", "third"):
        plot.add_curve(key)
    dialog = dialogs._CustomizeDialog(plot, None)
    controls = dialog.global_controls

    assert not controls.curve_palette_method.isChecked()
    assert not controls.curve_gradient_method.isChecked()
    assert controls.curve_color_stack.currentIndex() == 0

    controls.curve_gradient_method.click()
    gradient = BUILTIN_COLOR_GRADIENTS["viridis"]
    assert controls.curve_color_stack.currentWidget() is controls.curve_gradient_page
    for index, key in enumerate(("first", "second", "third")):
        assert plot.curve_style(key).line_color == gradient.color_at(index / 2).name()

    controls.gradient_reverse.setChecked(True)
    for index, key in enumerate(("first", "second", "third")):
        assert plot.curve_style(key).line_color == gradient.color_at(
            index / 2,
            reverse=True,
        ).name()

    controls.curve_palette_method.click()
    assert controls.curve_color_stack.currentWidget() is controls.curve_palette_page
    assert not controls.curve_gradient_method.isChecked()
    for index, key in enumerate(("first", "second", "third")):
        assert plot.curve_style(key).line_color == plot.curve_palette.color(index).name()


def test_curve_color_menu_uses_color_swatch_icons_without_hex_labels(
    qapp: QApplication,
) -> None:
    palette = BUILTIN_CURVE_PALETTES["okabe-ito"]
    colors = tuple(QColor(color).name() for color in palette.colors)
    parent = QDialog()
    menu = dialogs._curve_color_menu(
        parent,
        object_name="testCurveColorMenu",
        colors=colors,
    )

    assert menu.objectName() == "testCurveColorMenu"
    assert len(menu.actions()) == len(colors)
    for index, (action, color_name) in enumerate(zip(menu.actions(), colors, strict=True)):
        assert action.text() == ""
        assert action.toolTip() == f"Palette color {index + 1}"
        assert "#" not in action.toolTip()
        assert action.data() == color_name
        assert action.isIconVisibleInMenu()
        assert not action.icon().isNull()
        icon = action.icon().pixmap(18, 18).toImage()
        assert icon.pixelColor(icon.width() // 2, icon.height() // 2) == QColor(color_name)


def test_gradient_order_scalars_reverse_clamping_and_atomic_errors(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="gradient")
    for key in ("cold", "middle", "hot"):
        plot.add_curve(key)
    plot.apply_curve_gradient("viridis")
    gradient = BUILTIN_COLOR_GRADIENTS["viridis"]
    assert plot.curve_style("cold").line_color == gradient.color_at(0.0).name()
    assert plot.curve_style("middle").line_color == gradient.color_at(0.5).name()
    before = tuple(plot.curve_style(key) for key in ("cold", "middle", "hot"))
    with pytest.raises(KeyError):
        plot.apply_curve_gradient("plasma", values={"missing": 1.0})
    assert tuple(plot.curve_style(key) for key in ("cold", "middle", "hot")) == before

    plot.apply_curve_gradient(
        "plasma",
        values={"cold": -5.0, "hot": 20.0},
        value_range=(0.0, 10.0),
        reverse=True,
    )
    plasma = BUILTIN_COLOR_GRADIENTS["plasma"]
    assert plot.curve_style("cold").line_color == plasma.color_at(0.0, reverse=True).name()
    assert plot.curve_style("hot").line_color == plasma.color_at(1.0, reverse=True).name()


def test_persistence_reuses_pool_and_follows_source_state(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="persistence")
    plot.plot("signal", [0.0, 1.0], [0.0, 1.0])
    config = TracePersistenceConfig(history_length=2)
    plot.set_curve_persistence("signal", config)
    plot.set_data("signal", [0.0, 1.0], [1.0, 2.0])
    plot.set_data("signal", [0.0, 1.0], [2.0, 3.0])
    items = plot._trace_persistence.items("signal")
    item_ids = {id(item) for item in items}
    assert len(items) == 2
    assert items[0].opts["pen"].color().alphaF() == pytest.approx(config.newest_opacity, abs=0.01)
    assert items[-1].opts["pen"].color().alphaF() == pytest.approx(config.oldest_opacity, abs=0.01)

    plot.set_data("signal", [0.0, 1.0], [3.0, 4.0])
    assert {id(item) for item in plot._trace_persistence.items("signal")} == item_ids
    plot.set_curve_visible("signal", False)
    assert all(not item.isVisible() for item in items)
    plot.clear_curve("signal")
    assert all(item.getData()[0] is None for item in items)
    plot.remove_curve("signal")
    assert plot._trace_persistence.items("signal") == ()


def test_failed_data_update_and_add_point_do_not_create_frames(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="persistence-errors")
    plot.plot("signal", [0.0, 1.0], [0.0, 1.0])
    plot.set_curve_persistence("signal", TracePersistenceConfig())
    with pytest.raises(ValueError):
        plot.set_data("signal", [0.0], [1.0, 2.0])
    assert plot._trace_persistence.items("signal") == ()
    plot.add_point("signal", 2.0, 2.0)
    assert plot._trace_persistence.items("signal") == ()


def test_layout_round_trips_palette_and_persistence(qapp: QApplication, tmp_path: Path) -> None:
    path = tmp_path / "appearance.layout.json"
    source = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    source.add_curve("signal")
    source.set_curve_palette("tol-bright")
    config = TracePersistenceConfig(history_length=7, decay=2.0)
    source.set_curve_persistence("signal", config)
    source.save_layout()

    target = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    target.add_curve("signal")
    assert target.load_layout()
    assert target.curve_palette.name == "tol-bright"
    assert target.curve_persistence("signal") == config

    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["plots"]["plot"]["curve_palette"] = "missing"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(LayoutFileError, match="Unknown.*palette"):
        target.load_layout()
