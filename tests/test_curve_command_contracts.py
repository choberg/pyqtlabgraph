from __future__ import annotations

import os

import pytest
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import CurveStyle, PyQtLabGraphWidget


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _record_signal(signal: object) -> list[tuple[object, ...]]:
    emissions: list[tuple[object, ...]] = []
    signal.connect(lambda *args: emissions.append(args))  # type: ignore[attr-defined]
    return emissions


def test_add_curve_and_plot_publish_only_one_creation_signal(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="curve-creation-signals")
    added = _record_signal(graph.curve_added)
    changed = _record_signal(graph.curve_changed)
    data_changed = _record_signal(graph.curve_data_changed)

    graph.add_curve("empty")
    graph.plot("populated", [0.0, 1.0], [2.0, 3.0])

    assert added == [("empty",), ("populated",)]
    assert changed == []
    assert data_changed == []


def test_failed_plot_data_validation_removes_curve_and_plot_item(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="failed-plot-validation")
    initial_items = tuple(graph.native_plot_item.listDataItems())
    added = _record_signal(graph.curve_added)
    changed = _record_signal(graph.curve_changed)
    data_changed = _record_signal(graph.curve_data_changed)

    with pytest.raises(ValueError, match="same length"):
        graph.plot("broken", [0.0, 1.0], [2.0])

    assert graph.curve_choices() == ()
    assert tuple(graph.native_plot_item.listDataItems()) == initial_items
    assert added == []
    assert changed == []
    assert data_changed == []


def test_duplicate_plot_preserves_the_existing_curve(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="duplicate-plot")
    existing_item = graph.plot("sensor", [0.0], [1.0])
    existing_data = graph.curve_data("sensor")
    added = _record_signal(graph.curve_added)

    with pytest.raises(ValueError, match="already exists"):
        graph.plot("sensor", [2.0], [3.0])

    assert graph.curve_choices() == (("sensor", "sensor"),)
    assert graph.curve_item("sensor") is existing_item
    assert graph.curve_data("sensor") == pytest.approx(existing_data)
    assert added == []


@pytest.mark.parametrize(
    ("collaborator_name", "method_name"),
    [
        ("_render_optimizer", "apply_curve_rendering_options"),
        ("_style_controller", "apply_curve_style"),
    ],
)
def test_failed_plot_configuration_rolls_back_curve(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    collaborator_name: str,
    method_name: str,
) -> None:
    graph = PyQtLabGraphWidget(
        plot_identifier=f"failed-plot-{collaborator_name.removeprefix('_')}"
    )
    collaborator = getattr(graph, collaborator_name)

    def fail_during_data_application(*args: object, **kwargs: object) -> object:
        raise RuntimeError("injected curve configuration failure")

    monkeypatch.setattr(collaborator, method_name, fail_during_data_application)
    initial_items = tuple(graph.native_plot_item.listDataItems())
    added = _record_signal(graph.curve_added)
    changed = _record_signal(graph.curve_changed)
    data_changed = _record_signal(graph.curve_data_changed)

    with pytest.raises(RuntimeError, match="injected curve configuration failure"):
        graph.plot("broken", [0.0, 1.0], [2.0, 3.0])

    assert graph.curve_choices() == ()
    assert tuple(graph.native_plot_item.listDataItems()) == initial_items
    assert added == []
    assert changed == []
    assert data_changed == []


def test_data_commands_publish_one_data_change_after_success(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="curve-data-signals")
    graph.add_curve("sensor")
    data_changed = _record_signal(graph.curve_data_changed)

    graph.set_data("sensor", [0.0], [1.0])
    graph.add_point("sensor", 1.0, 2.0)
    graph.clear_curve("sensor")

    assert data_changed == [("sensor",), ("sensor",), ("sensor",)]


def test_failed_data_command_publishes_no_data_change(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="failed-curve-data-signal")
    graph.add_curve("sensor")
    data_changed = _record_signal(graph.curve_data_changed)

    with pytest.raises(ValueError, match="same length"):
        graph.set_data("sensor", [0.0, 1.0], [2.0])

    assert data_changed == []


def test_curve_style_and_visibility_no_ops_publish_no_signal(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="curve-mutation-no-ops")
    graph.add_curve("sensor")
    changed = _record_signal(graph.curve_changed)
    original_style = graph.curve_style("sensor")

    graph.set_curve_style("sensor", original_style)
    graph.set_curve_visible("sensor", True)

    assert changed == []

    graph.set_curve_style(
        "sensor",
        original_style.with_overrides(line_width=original_style.line_width + 1.0),
    )
    graph.set_curve_visible("sensor", False)

    assert changed == [("sensor",), ("sensor",)]


def test_set_plot_style_updates_all_curves_and_has_clean_signals(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="plot-style-signals")
    graph.add_curve("first")
    graph.add_curve("second")
    changed = _record_signal(graph.curve_changed)
    presented = _record_signal(graph.presentation_changed)

    graph.set_plot_style("dark")

    assert changed == [("first",), ("second",)]
    assert presented == [()]
    assert graph.curve_style("first") == graph.plot_style.curve_style(0)
    assert graph.curve_style("second") == graph.plot_style.curve_style(1)

    changed.clear()
    presented.clear()
    graph.set_plot_style("dark")
    assert changed == []
    assert presented == []

    graph.add_curve("third")
    assert graph.curve_style("third") == graph.plot_style.curve_style(2)


def test_theme_and_rendering_repaints_are_not_curve_mutations(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="curve-repaint-signals")
    graph.plot(
        "sensor",
        [0.0, 1.0],
        [2.0, 3.0],
        style=CurveStyle(marker_enabled=True),
    )
    changed = _record_signal(graph.curve_changed)

    graph.set_theme("dark")
    graph._render_optimizer.update_adaptive_performance(force=True)

    assert changed == []
