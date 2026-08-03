from __future__ import annotations

import inspect
import os
from dataclasses import FrozenInstanceError

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QTabWidget, QWidget

from pyqtlabgraph import (
    CurveStyle,
    PyQtLabGraphPlotStyle,
    PyQtLabGraphStyleRegistry,
    PyQtLabGraphTheme,
    PyQtLabGraphWidget,
    customize_controls,
    dialogs,
    legend,
)
from pyqtlabgraph.models import InteractionState, InteractionTool
from pyqtlabgraph.styles import BUILTIN_PLOT_STYLES
from pyqtlabgraph.themes import BUILTIN_THEMES


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _custom_theme(name: str = "laboratory") -> PyQtLabGraphTheme:
    return PyQtLabGraphTheme(
        name=name,
        plot_background="#102030",
        grid=QColor(200, 210, 220, 60),
        border="#405060",
    )


def _custom_plot_style(name: str = "laboratory") -> PyQtLabGraphPlotStyle:
    return PyQtLabGraphPlotStyle(
        name=name,
        curve_styles=(CurveStyle(line_color="#abcdef", marker_symbol="d"),),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"line_width": 0.0},
        {"marker_size": 0},
        {"marker_outline_width": -0.1},
    ],
)
def test_curve_style_rejects_invalid_dimensions(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        CurveStyle(**overrides)


@pytest.mark.parametrize("name", ["", "   "])
def test_named_style_values_require_nonempty_names(name: str) -> None:
    with pytest.raises(ValueError, match="name"):
        _custom_theme(name)
    with pytest.raises(ValueError, match="name"):
        _custom_plot_style(name)


def test_plot_style_requires_a_nonempty_curve_palette() -> None:
    with pytest.raises(ValueError, match="curve style"):
        PyQtLabGraphPlotStyle(name="empty", curve_styles=())


def test_registry_contains_builtins_and_is_case_insensitive() -> None:
    registry = PyQtLabGraphStyleRegistry()

    assert registry.resolve_theme(" DARK ") is BUILTIN_THEMES["dark"]
    assert registry.resolve_plot_style("SoLaRiZeD") is BUILTIN_PLOT_STYLES["solarized"]
    assert tuple(value.name for value in registry.themes) == tuple(BUILTIN_THEMES)
    assert tuple(value.name for value in registry.plot_styles) == tuple(BUILTIN_PLOT_STYLES)


def test_registry_registration_is_explicit_isolated_and_duplicate_safe() -> None:
    first = PyQtLabGraphStyleRegistry()
    second = PyQtLabGraphStyleRegistry()
    theme = _custom_theme()
    plot_style = _custom_plot_style()

    first.register_theme(theme)
    first.register_plot_style(plot_style)

    assert first.resolve_theme("LABORATORY") is theme
    assert first.resolve_plot_style(" laboratory ") is plot_style
    with pytest.raises(ValueError, match="Unknown"):
        second.resolve_theme(theme.name)
    with pytest.raises(ValueError, match="Unknown"):
        second.resolve_plot_style(plot_style.name)
    with pytest.raises(ValueError, match="already registered"):
        first.register_theme(_custom_theme("LABORATORY"))
    with pytest.raises(ValueError, match="already registered"):
        first.register_plot_style(_custom_plot_style(" Laboratory "))
    assert "laboratory" not in BUILTIN_THEMES
    assert "laboratory" not in BUILTIN_PLOT_STYLES


def test_registry_rejects_unregistered_or_unequal_objects() -> None:
    registry = PyQtLabGraphStyleRegistry()
    theme = _custom_theme()
    plot_style = _custom_plot_style()

    with pytest.raises(ValueError, match="not registered"):
        registry.resolve_theme(theme)
    with pytest.raises(ValueError, match="not registered"):
        registry.resolve_plot_style(plot_style)

    registry.register_theme(theme)
    registry.register_plot_style(plot_style)
    unequal_theme = PyQtLabGraphTheme(
        name=theme.name.upper(),
        plot_background="#ffffff",
        grid=QColor("#777777"),
        border="#000000",
    )
    unequal_plot_style = PyQtLabGraphPlotStyle(
        name=plot_style.name.upper(),
        curve_styles=(CurveStyle(line_color="#123456"),),
    )
    with pytest.raises(ValueError, match="does not match"):
        registry.resolve_theme(unequal_theme)
    with pytest.raises(ValueError, match="does not match"):
        registry.resolve_plot_style(unequal_plot_style)


def test_widget_uses_injected_registry_without_partial_style_mutation(
    qapp: QApplication,
) -> None:
    registry = PyQtLabGraphStyleRegistry()
    theme = _custom_theme()
    plot_style = _custom_plot_style()
    registry.register_theme(theme)
    registry.register_plot_style(plot_style)
    graph = PyQtLabGraphWidget(
        plot_identifier="custom-registry",
        style_registry=registry,
        theme=theme,
        plot_style=plot_style,
    )

    assert graph.style_registry is registry
    assert graph.theme is theme
    assert graph.plot_style is plot_style
    graph.add_curve("sensor")
    assert graph.curve_style("sensor") == plot_style.curve_style(0)

    previous_theme = graph.theme
    previous_plot_style = graph.plot_style
    with pytest.raises(ValueError, match="not registered"):
        graph.set_theme(_custom_theme("unregistered"))
    with pytest.raises(ValueError, match="not registered"):
        graph.set_plot_style(_custom_plot_style("unregistered"))
    assert graph.theme is previous_theme
    assert graph.plot_style is previous_plot_style


def test_customize_controls_enumerate_the_widget_registry(
    qapp: QApplication,
) -> None:
    registry = PyQtLabGraphStyleRegistry()
    theme = _custom_theme()
    plot_style = _custom_plot_style()
    registry.register_theme(theme)
    registry.register_plot_style(plot_style)
    graph = PyQtLabGraphWidget(
        plot_identifier="custom-registry-controls",
        style_registry=registry,
        theme=theme.name,
        plot_style=plot_style.name,
    )
    parent = QWidget()
    tabs = QTabWidget(parent)

    controls = customize_controls.build_global_tab(graph, parent, tabs)

    assert controls.plot_background.findData(theme.name) >= 0
    assert controls.plot_background.currentData() == theme.name
    assert controls.plot_style.findData(plot_style.name) >= 0
    assert controls.plot_style.currentData() == plot_style.name


def test_customize_curve_tabs_keep_their_curve_labels(qapp: QApplication) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="customize-curve-labels")
    graph.add_curve("sensor", label="Sensor")
    graph.add_curve("reference", label="Reference")
    parent = QWidget()
    tabs = QTabWidget(parent)

    customize_controls.build_curve_tabs(
        graph,
        parent,
        tabs,
        lambda _curve_key: None,
    )

    assert [tabs.tabText(index) for index in range(tabs.count())] == [
        "Sensor",
        "Reference",
    ]


def test_interaction_state_is_frozen_and_rejects_contradictions() -> None:
    state = InteractionState()
    with pytest.raises(FrozenInstanceError):
        state.autoscale_x = False  # type: ignore[misc]

    with pytest.raises(ValueError, match="Autoscale X"):
        InteractionState(autoscale_x=True, rolling_x=True)
    with pytest.raises(ValueError, match="zoom tool"):
        InteractionState(
            autoscale_x=True,
            autoscale_y=False,
            active_tool=InteractionTool.X_ZOOM,
        )
    with pytest.raises(ValueError, match="zoom tool"):
        InteractionState(
            autoscale_x=False,
            autoscale_y=True,
            active_tool=InteractionTool.X_ZOOM,
        )
    with pytest.raises(ValueError, match="zoom tool"):
        InteractionState(
            autoscale_x=False,
            autoscale_y=False,
            rolling_x=True,
            active_tool=InteractionTool.X_ZOOM,
        )


def test_widget_interaction_commands_preserve_all_invariants(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="validated-interaction-commands")

    graph.request_tool(InteractionTool.X_ZOOM, True)
    assert graph.interaction_state == InteractionState(
        autoscale_x=False,
        autoscale_y=False,
        rolling_x=False,
        active_tool=InteractionTool.X_ZOOM,
    )

    graph.request_autoscale_y(True)
    assert graph.interaction_state == InteractionState(
        autoscale_x=False,
        autoscale_y=True,
        rolling_x=False,
        active_tool=InteractionTool.NONE,
    )

    graph.request_tool(InteractionTool.Y_ZOOM, True)
    graph.request_rolling_x(True)
    assert graph.interaction_state == InteractionState(
        autoscale_x=False,
        autoscale_y=False,
        rolling_x=True,
        active_tool=InteractionTool.NONE,
    )

    graph.request_autoscale_x(True)
    assert graph.interaction_state == InteractionState(
        autoscale_x=True,
        autoscale_y=False,
        rolling_x=False,
        active_tool=InteractionTool.NONE,
    )


def test_interaction_no_ops_do_not_publish_and_invalid_apply_is_atomic(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="atomic-interaction-state")
    emissions: list[InteractionState] = []
    graph.interaction_state_changed.connect(emissions.append)

    graph.request_autoscale_x(True)
    graph.apply_interaction_state(graph.interaction_state)
    assert emissions == []

    before = graph.interaction_state
    invalid = object.__new__(InteractionState)
    object.__setattr__(invalid, "autoscale_x", True)
    object.__setattr__(invalid, "autoscale_y", True)
    object.__setattr__(invalid, "rolling_x", True)
    object.__setattr__(invalid, "active_tool", InteractionTool.X_ZOOM)
    with pytest.raises(ValueError):
        graph.apply_interaction_state(invalid)
    assert graph.interaction_state == before
    assert emissions == []


def test_public_curve_and_rendering_queries_reflect_effective_state(
    qapp: QApplication,
) -> None:
    graph = PyQtLabGraphWidget(plot_identifier="public-state-queries")
    graph.add_curve("sensor")

    assert graph.curve_visible("sensor")
    assert graph.grid_visible
    assert graph.antialiasing_enabled
    assert graph.downsampling_enabled
    assert graph.clip_to_view_enabled
    assert graph.adaptive_performance_enabled

    graph.set_curve_visible("sensor", False)
    graph.set_grid_visible(False)
    graph.set_antialiasing_enabled(False)
    graph.set_downsampling_enabled(False)
    graph.set_clip_to_view_enabled(False)
    graph.set_adaptive_performance_enabled(False)

    assert not graph.curve_visible("sensor")
    assert not graph.grid_visible
    assert not graph.antialiasing_enabled
    assert not graph.downsampling_enabled
    assert not graph.clip_to_view_enabled
    assert not graph.adaptive_performance_enabled


def test_companion_modules_do_not_read_private_curve_or_rendering_state() -> None:
    for module in (legend, customize_controls, dialogs):
        source = inspect.getsource(module)
        assert "._curve_manager" not in source
        assert "._render_optimizer" not in source
