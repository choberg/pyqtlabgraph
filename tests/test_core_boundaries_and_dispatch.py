from __future__ import annotations

import inspect
import os

import numpy as np
import pytest
from PySide6.QtWidgets import QApplication

from pyqtlabgraph import PyQtLabGraphWidget


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "collaborator_name",
    [
        "_curve_manager",
        "_range_controller",
        "_render_optimizer",
        "_style_controller",
    ],
)
def test_non_cursor_core_collaborators_do_not_store_the_widget(
    qapp: QApplication,
    collaborator_name: str,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier=f"narrow-{collaborator_name}")
    collaborator = getattr(graph, collaborator_name)

    assert graph not in vars(collaborator).values()
    assert not hasattr(collaborator, "_widget")
    assert "self._widget" not in inspect.getsource(type(collaborator))


@pytest.mark.parametrize("method_name", ["plot", "set_data"])
def test_high_level_data_methods_have_no_arbitrary_keyword_forwarding(
    method_name: str,
) -> None:
    signature = inspect.signature(getattr(PyQtLabGraphWidget, method_name))

    assert all(
        parameter.kind is not inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )


def test_typed_data_api_supports_y_only_and_explicit_xy(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="typed-data")
    graph.plot("y-only", [2.0, 4.0])
    graph.add_curve("explicit")
    graph.set_data("explicit", [10.0, 20.0], [1.0, 3.0])

    y_only_x, y_only_y = graph.curve_data("y-only")
    explicit_x, explicit_y = graph.curve_data("explicit")
    np.testing.assert_allclose(y_only_x, [0.0, 1.0])
    np.testing.assert_allclose(y_only_y, [2.0, 4.0])
    np.testing.assert_allclose(explicit_x, [10.0, 20.0])
    np.testing.assert_allclose(explicit_y, [1.0, 3.0])

    graph.set_data("explicit", x=[30.0], y=[5.0])
    explicit_x, explicit_y = graph.curve_data("explicit")
    np.testing.assert_allclose(explicit_x, [30.0])
    np.testing.assert_allclose(explicit_y, [5.0])

    with pytest.raises(TypeError):
        graph.plot("native-options", [1.0], pen="red")  # type: ignore[call-arg]


def test_explicit_xy_validation_precedes_curve_mutation(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="typed-data-validation")
    graph.plot("sensor", [0.0, 1.0], [2.0, 3.0])
    original_data = graph.curve_data("sensor")

    with pytest.raises(ValueError, match="same length"):
        graph.set_data("sensor", [0.0, 1.0, 2.0], [4.0])

    actual_x, actual_y = graph.curve_data("sensor")
    np.testing.assert_array_equal(actual_x, original_data[0])
    np.testing.assert_array_equal(actual_y, original_data[1])


def test_data_update_uses_the_central_order(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="data-update-order")
    graph.add_curve("sensor")
    events: list[str] = []

    original_set_data = graph._curve_manager.set_data

    def mutate(key: str, *data: object) -> None:
        events.append("data")
        original_set_data(key, *data)

    monkeypatch.setattr(graph._curve_manager, "set_data", mutate)
    monkeypatch.setattr(
        graph._cursor_controller,
        "refresh_for_curve",
        lambda _key: events.append("cursor-cache"),
    )
    monkeypatch.setattr(
        graph._range_controller,
        "apply_axis_scaling",
        lambda: events.append("range"),
    )

    def update_rendering(*, force: bool = False) -> bool:
        assert force is False
        events.append("rendering")
        return True

    monkeypatch.setattr(
        graph._render_optimizer,
        "update_adaptive_performance",
        update_rendering,
    )
    monkeypatch.setattr(
        graph._style_controller,
        "apply_curve_style",
        lambda _curve: events.append("style"),
    )
    monkeypatch.setattr(
        graph._cursor_controller,
        "refresh_presentation",
        lambda: events.append("cursor-presentation"),
    )
    graph.curve_data_changed.connect(lambda _key: events.append("signal"))

    graph.set_data("sensor", [0.0], [1.0])

    assert events == [
        "data",
        "cursor-cache",
        "range",
        "rendering",
        "style",
        "cursor-presentation",
        "signal",
    ]


def test_view_update_uses_the_central_order(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="view-update-order")
    graph.add_curve("sensor")
    events: list[str] = []

    monkeypatch.setattr(
        graph,
        "request_manual_navigation",
        lambda: events.append("interaction"),
    )

    def update_rendering(*, force: bool = False) -> bool:
        assert force is False
        events.append("rendering")
        return True

    monkeypatch.setattr(
        graph._render_optimizer,
        "update_adaptive_performance",
        update_rendering,
    )
    monkeypatch.setattr(
        graph._style_controller,
        "apply_curve_style",
        lambda _curve: events.append("style"),
    )
    monkeypatch.setattr(
        graph._cursor_controller,
        "refresh_presentation",
        lambda: events.append("cursor-presentation"),
    )
    graph.presentation_changed.connect(lambda: events.append("signal"))

    graph._handle_view_range_changed()

    assert events == [
        "interaction",
        "rendering",
        "style",
        "cursor-presentation",
        "signal",
    ]


def test_dispatcher_coalesces_public_notifications(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="coalesced-notifications")
    graph.add_cursor("x", key="cursor")
    events: list[str] = []
    graph.cursor_changed.connect(lambda key: events.append(f"cursor:{key}"))
    graph.curve_changed.connect(lambda key: events.append(f"curve:{key}"))
    graph.curve_data_changed.connect(lambda key: events.append(f"data:{key}"))
    graph.presentation_changed.connect(lambda: events.append("presentation"))

    with graph._change_dispatcher.batch():
        graph.set_cursor_name("cursor", "First")
        graph.set_cursor_name("cursor", "Second")
        graph._publish_curve_changed("sensor")
        graph._publish_curve_changed("sensor")
        graph._change_dispatcher.curve_data_changed("sensor")
        graph._change_dispatcher.curve_data_changed("sensor")
        graph._publish_presentation_changed()
        graph._publish_presentation_changed()

    assert events == [
        "cursor:cursor",
        "curve:sensor",
        "data:sensor",
        "presentation",
    ]


def test_dispatcher_discards_notifications_after_a_failed_nested_batch(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="failed-batch-notifications")
    graph.add_cursor("x", key="cursor")
    events: list[str] = []
    graph.curve_changed.connect(events.append)
    graph.cursor_changed.connect(events.append)

    with graph._change_dispatcher.batch():
        graph._publish_curve_changed("before-failure")
        graph.set_cursor_name("cursor", "Pending")
        try:
            with graph._change_dispatcher.batch():
                graph._publish_curve_changed("failed")
                raise RuntimeError("injected failure")
        except RuntimeError:
            pass
        graph._publish_curve_changed("after-failure")

    assert events == []
