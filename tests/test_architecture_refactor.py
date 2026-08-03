from __future__ import annotations

import json
import os

import numpy as np
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget

from pyqtlabgraph import (
    CursorLineStyle,
    CursorStyle,
    LayoutFileError,
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)
from pyqtlabgraph.cursor_manager import CursorManager
from pyqtlabgraph.customize_session import CustomizeSession


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_cursor_domain_uses_canonical_snap_state_and_enum() -> None:
    data = {"sensor": (np.array([0.0, 2.0, 4.0]), np.array([1.0, 3.0, 5.0]))}
    manager = CursorManager(curve_data_provider=data.__getitem__)
    key = manager.add_cursor(
        "x",
        value=1.6,
        snap_target_curve_key="sensor",
        style=CursorStyle(line_style=CursorLineStyle.DASH),
    )
    assert manager.cursor_state(key).snap_target_curve_key == "sensor"
    assert manager.cursor_state(key).value == 2.0
    manager.set_cursor_snap_target(key, None)
    assert manager.cursor_state(key).snap_target_curve_key is None
    with pytest.raises(ValueError, match="Only X cursors"):
        manager.add_cursor("y", snap_target_curve_key="sensor")
    with pytest.raises(ValueError, match="visibility coupling"):
        manager.add_cursor("x", follow_target_visibility=True)
    with pytest.raises(TypeError, match="CursorLineStyle"):
        CursorStyle(line_style="dash")  # type: ignore[arg-type]


def test_customize_rollback_restores_cursor_with_visibility_coupling(
    qapp: QApplication,
) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="customize-cursor-rollback")
    plot.plot("sensor", [0.0, 1.0], [1.0, 2.0])
    plot.add_cursor(
        "x",
        key="snap",
        value=0.8,
        snap_target_curve_key="sensor",
        follow_target_visibility=True,
    )
    session = CustomizeSession(plot)

    plot.set_cursor_follow_target_visibility("snap", False)
    plot.set_cursor_snap_target("snap", None)
    session.rollback()

    restored = plot.cursor_state("snap")
    assert restored.snap_target_curve_key == "sensor"
    assert restored.follow_target_visibility


def test_pair_indices_order_and_cache_invalidation() -> None:
    calls = 0

    def data(_key: str) -> tuple[np.ndarray, np.ndarray]:
        nonlocal calls
        calls += 1
        return np.array([2.0, 1.0]), np.array([20.0, 10.0])

    manager = CursorManager(curve_data_provider=data)
    first = manager.add_cursor("x")
    loose = manager.add_cursor("x")
    second = manager.add_cursor("x")
    pair = manager.add_cursor_pair(first, second)
    assert [state.key for state in manager.cursor_states()] == [first, second, loose]
    assert manager.cursor_pair_for_cursor(first).key == pair  # type: ignore[union-attr]
    assert manager.cursor_pair_states()[0].key == pair
    assert manager.sorted_finite_x_values("sensor").tolist() == [1.0, 2.0]
    assert manager.sorted_finite_x_values("sensor").tolist() == [1.0, 2.0]
    assert calls == 1
    manager.invalidate_curve_data("sensor")
    manager.sorted_finite_x_values("sensor")
    assert calls == 2


def test_components_are_independent_and_signal_driven(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="components")
    toolbar = PyQtLabGraphToolbar(plot)
    legend = PyQtLabGraphLegend(plot, orientation=Qt.Orientation.Horizontal)
    first_panel = PyQtLabGraphCursorWidget(plot)
    second_panel = PyQtLabGraphCursorWidget(plot)
    assert all(isinstance(widget, QWidget) for widget in (plot, toolbar, legend, first_panel, second_panel))
    assert not any(hasattr(plot, name) for name in ("toolbar", "legend", "cursor_widget"))

    placeholders = [QWidget() for _ in range(4)]
    for placeholder, component in zip(placeholders, (plot, toolbar, legend, first_panel)):
        layout = QVBoxLayout(placeholder)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(component)
        assert layout.itemAt(0).widget() is component

    plot.add_curve("sensor")
    assert "sensor" in legend.items_by_key
    key = plot.add_cursor("x")
    plot.set_selected_cursor_keys([key])
    qapp.processEvents()
    assert first_panel.selected_cursor_keys() == [key]
    assert second_panel.selected_cursor_keys() == [key]
    plot.request_autoscale_x(False)
    assert not toolbar.autoscale_x_action.isChecked()


def test_layout_format_roundtrip_and_multi_plot_preservation(
    qapp: QApplication,
    tmp_path,
) -> None:
    path = tmp_path / "layout.json"
    first = PyQtLabGraphWidget(plot_identifier="first", layout_path=path)
    first.plot("sensor", [0.0, 1.0], [2.0, 3.0])
    snapped = first.add_cursor(
        "x",
        key="snap",
        value=0.8,
        snap_target_curve_key="sensor",
        label_visible=True,
    )
    peer = first.add_cursor("x", key="peer")
    first.add_cursor_pair(snapped, peer, key="measurement", measurement_visible=False)
    first.save_layout()

    second = PyQtLabGraphWidget(plot_identifier="second", layout_path=path)
    second.save_layout()
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["version"] == 1
    assert set(document["plots"]) == {"first", "second"}
    assert isinstance(document["plots"]["first"]["cursors"], list)
    assert "cursor_order" not in document["plots"]["first"]

    restored = PyQtLabGraphWidget(plot_identifier="first", layout_path=path)
    restored.add_curve("sensor")
    current_only = restored.add_cursor("y", key="current-only")
    restored.set_selected_cursor_keys([current_only])
    assert restored.load_layout()
    assert [state.key for state in restored.cursor_states()] == ["snap", "peer"]
    assert restored.selected_cursor_keys() == []
    assert restored.cursor_state("snap").snap_target_curve_key == "sensor"
    assert restored.cursor_state("snap").label_visible
    assert not restored.cursor_pair_state("measurement").measurement_visible


def test_unsupported_version_and_structurally_invalid_entries_are_rejected(
    qapp: QApplication,
    tmp_path,
) -> None:
    path = tmp_path / "layout.json"
    path.write_text(json.dumps({"version": 2, "plots": {}}), encoding="utf-8")
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    with pytest.raises(LayoutFileError, match="version 1 is required"):
        plot.load_layout()

    path.unlink()
    plot.save_layout()
    document = json.loads(path.read_text(encoding="utf-8"))
    document["plots"]["plot"]["cursors"] = {"not": "a list"}
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(LayoutFileError, match="must be a list"):
        plot.load_layout()

    plot.set_theme("dark")
    document["plots"]["plot"]["cursors"] = []
    document["plots"]["plot"]["cursor_pairs"] = [
        {
            "key": "bad",
            "members": ["missing-a", "missing-b"],
            "measurement_visible": True,
            "annotation_position": 0.08,
        }
    ]
    path.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(LayoutFileError, match="unknown cursor"):
        plot.load_layout()
    assert plot.theme.name == "dark"
