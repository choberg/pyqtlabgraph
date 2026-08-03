from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QWidget

from pyqtlabgraph import (
    CursorStyle,
    LayoutFileError,
    PyQtLabGraphCursorWidget,
    PyQtLabGraphLegend,
    PyQtLabGraphPlotStyle,
    PyQtLabGraphStyleRegistry,
    PyQtLabGraphTheme,
    PyQtLabGraphToolbar,
    PyQtLabGraphWidget,
)
from pyqtlabgraph.customize_session import CustomizeSession
from pyqtlabgraph.layouts import (
    LAYOUT_FORMAT_VERSION,
    decode_layout_document,
)
from pyqtlabgraph.runtime_state import PlotSnapshot
from pyqtlabgraph.styles import CurveStyle


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _dispose(qapp: QApplication, *widgets: QWidget) -> None:
    for widget in widgets:
        widget.close()
        widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    qapp.processEvents()


def _layout(*, theme: str = "light", plot_style: str = "light") -> dict[str, object]:
    return {
        "restore_view_state_on_load": True,
        "theme": theme,
        "plot_style": plot_style,
        "axes": {
            "x": {"label": "Time", "units": "s", "mode": "linear", "log": False},
            "y": {"label": "Value", "units": None, "mode": "auto", "log": False},
        },
        "grid_visible": True,
        "rendering": {
            "antialiasing": True,
            "downsampling": True,
            "clip_to_view": True,
            "adaptive_performance": True,
        },
        "interaction": {
            "autoscale_x": False,
            "autoscale_y": False,
            "rolling_x": False,
            "active_tool": "none",
        },
        "ranges": {"x": [1.0, 3.0], "y": [-2.0, 4.0]},
        "curves": {},
        "cursors": [],
        "cursor_pairs": [],
    }


def _document(layout: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "version": LAYOUT_FORMAT_VERSION,
        "plots": {"plot": layout or _layout()},
    }


def _curve_style(**overrides: object) -> dict[str, object]:
    style = {
        "line_enabled": True,
        "line_color": "#0072B2",
        "line_width": 1.0,
        "marker_symbol": "s",
        "marker_size": 5,
        "marker_outline_width": 1.0,
        "marker_enabled": True,
        "marker_filled": False,
    }
    style.update(overrides)
    return style


def _cursor(
    key: str,
    *,
    name: str | None = None,
    cursor_type: str = "x",
    value: object = 1.0,
    **overrides: object,
) -> dict[str, object]:
    state = {
        "key": key,
        "name": name or key,
        "type": cursor_type,
        "value": value,
        "visible": True,
        "style": {
            "line_color": "#0072B2",
            "line_width": 1.0,
            "line_style": "solid",
        },
        "snap_target_curve_key": None,
        "follow_target_visibility": False,
        "label_visible": False,
    }
    state.update(overrides)
    return state


def _cursor_pair(
    key: str,
    first: str,
    second: str,
    **overrides: object,
) -> dict[str, object]:
    state = {
        "key": key,
        "members": [first, second],
        "measurement_visible": True,
        "annotation_position": 0.08,
    }
    state.update(overrides)
    return state


def _write(path: Path, document: dict[str, object]) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def test_layout_codec_runs_without_qapplication() -> None:
    source = json.dumps(_document())
    code = (
        "from PySide6.QtWidgets import QApplication\n"
        "from pyqtlabgraph.layouts import decode_layout_document\n"
        f"document = decode_layout_document({source!r})\n"
        "assert QApplication.instance() is None\n"
        "assert document.version == 1\n"
        "assert document.plots['plot'].x_axis.label == 'Time'\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


@pytest.mark.parametrize(
    ("path", "value", "match"),
    [
        (("grid_visible",), 1, "Boolean"),
        (("rendering", "antialiasing"), "false", "Boolean"),
        (("axes", "x", "log"), 0, "Boolean"),
        (("interaction", "active_tool"), "invalid", "active_tool"),
        (
            ("interaction",),
            {
                "autoscale_x": True,
                "autoscale_y": False,
                "rolling_x": True,
                "active_tool": "none",
            },
            "Autoscale X and rolling X",
        ),
        (("ranges", "x"), [0.0, float("inf")], "finite"),
        (("curves", "unknown", "style", "line_width"), 0.0, "greater than zero"),
        (("cursors",), [_cursor("cursor", value=float("nan"))], "finite"),
    ],
)
def test_layout_codec_strictly_rejects_invalid_values(
    path: tuple[str, ...],
    value: object,
    match: str,
) -> None:
    document = _document()
    target: object = document["plots"]["plot"]  # type: ignore[index]
    for key in path[:-1]:
        if key == "unknown":
            assert isinstance(target, dict)
            target[key] = {"visible": True, "style": _curve_style()}
        assert isinstance(target, dict)
        target = target[key]
    assert isinstance(target, dict)
    target[path[-1]] = value

    with pytest.raises(LayoutFileError, match=match):
        decode_layout_document(json.dumps(document))


def test_layout_codec_rejects_duplicate_json_keys() -> None:
    raw = (
        '{"version":1,"plots":{"plot":'
        '{"grid_visible":true,"grid_visible":false}}}'
    )
    with pytest.raises(LayoutFileError, match="Duplicate JSON object key"):
        decode_layout_document(raw)


@pytest.mark.parametrize(
    ("container_path", "field", "match"),
    [
        ((), "plots", "missing required field"),
        (("plots", "plot"), "theme", "missing required field"),
        (("plots", "plot", "axes", "x"), "mode", "missing required field"),
        (("plots", "plot", "rendering"), "antialiasing", "missing required field"),
        (("plots", "plot", "interaction"), "active_tool", "missing required field"),
    ],
)
def test_layout_codec_requires_all_fixed_fields(
    container_path: tuple[str, ...],
    field: str,
    match: str,
) -> None:
    document = _document()
    container: object = document
    for key in container_path:
        assert isinstance(container, dict)
        container = container[key]
    assert isinstance(container, dict)
    del container[field]

    with pytest.raises(LayoutFileError, match=match):
        decode_layout_document(json.dumps(document))


@pytest.mark.parametrize(
    "container_path",
    [
        (),
        ("plots", "plot"),
        ("plots", "plot", "axes", "x"),
        ("plots", "plot", "rendering"),
        ("plots", "plot", "interaction"),
    ],
)
def test_layout_codec_rejects_unknown_fixed_fields(
    container_path: tuple[str, ...],
) -> None:
    document = _document()
    container: object = document
    for key in container_path:
        assert isinstance(container, dict)
        container = container[key]
    assert isinstance(container, dict)
    container["unexpected"] = True

    with pytest.raises(LayoutFileError, match="unknown field"):
        decode_layout_document(json.dumps(document))


def test_layout_codec_rejects_invalid_cursor_pairs_without_widget() -> None:
    layout = _layout()
    layout["cursors"] = [
        _cursor("x", name="X"),
        _cursor("y", name="Y", cursor_type="y", value=2.0),
    ]
    layout["cursor_pairs"] = [
        _cursor_pair("bad", "x", "y"),
    ]
    with pytest.raises(LayoutFileError, match="same axis"):
        decode_layout_document(json.dumps(_document(layout)))


def _configure_runtime_state(plot: PyQtLabGraphWidget) -> None:
    plot.plot("sensor", [0.0, 1.0], [1.0, 2.0])
    plot.set_curve_visible("sensor", False)
    plot.set_axis_labels("Elapsed", "Temperature", x_units="s", y_units="K")
    plot.set_grid_visible(True)
    plot.set_antialiasing_enabled(False)
    plot.set_downsampling_enabled(False)
    plot.set_clip_to_view_enabled(False)
    plot.set_adaptive_performance_enabled(False)
    plot.request_autoscale_x(False)
    plot.request_autoscale_y(False)
    plot.apply_manual_x_limits(2.0, 8.0)
    plot.apply_manual_y_limits(-3.0, 9.0)
    first = plot.add_cursor("x", key="first", value=3.0, label_visible=True)
    second = plot.add_cursor(
        "x",
        key="second",
        value=6.0,
        style=CursorStyle(line_color="#D55E00"),
    )
    plot.add_cursor_pair(first, second, key="delta", measurement_visible=False)
    plot.set_selected_cursor_keys([second])


def test_plot_snapshot_restores_exact_runtime_state(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="snapshot")
    _configure_runtime_state(plot)
    before = PlotSnapshot.capture(plot)

    plot.set_theme("dark")
    plot.set_plot_style("dark")
    plot.set_curve_visible("sensor", True)
    plot.set_axis_labels("Changed X", "Changed Y")
    plot.request_show_all()
    plot.remove_cursor("first")
    plot.add_cursor("y", key="replacement", value=7.0)
    plot.set_selected_cursor_keys(["replacement"])

    plot.restore_snapshot(before)

    assert PlotSnapshot.capture(plot) == before
    _dispose(qapp, plot)


def test_layout_load_is_atomic_and_emits_only_state_reset(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.json"
    layout = _layout(theme="dark", plot_style="dark")
    layout["curves"] = {
        "sensor": {
            "visible": False,
            "style": {
                "line_enabled": True,
                "line_color": "#D55E00",
                "line_width": 2.0,
                "marker_symbol": "o",
                "marker_size": 7,
                "marker_outline_width": 1.0,
                "marker_enabled": True,
                "marker_filled": True,
            },
        }
    }
    _write(path, _document(layout))
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    plot.add_curve("sensor")

    granular: list[str] = []
    plot.curve_changed.connect(lambda _key: granular.append("curve"))
    plot.interaction_state_changed.connect(lambda _state: granular.append("interaction"))
    plot.presentation_changed.connect(lambda: granular.append("presentation"))
    plot.cursor_added.connect(lambda _key: granular.append("cursor"))
    resets: list[str] = []
    plot.state_reset.connect(lambda: resets.append("reset"))

    assert plot.load_layout()

    assert granular == []
    assert resets == ["reset"]
    assert plot.theme.name == "dark"
    assert not plot.curve_visible("sensor")
    assert plot.get_x_range() == pytest.approx((1.0, 3.0))
    _dispose(qapp, plot)


def test_failed_layout_application_restores_snapshot_and_emits_nothing(
    qapp: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "layout.json"
    layout = _layout(theme="dark")
    layout["curves"] = {
        "sensor": {"visible": False, "style": CurveStyle(line_color="#D55E00").__dict__}
    }
    _write(path, _document(layout))
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    _configure_runtime_state(plot)
    before = PlotSnapshot.capture(plot)
    events: list[str] = []
    for signal in (
        plot.curve_changed,
        plot.interaction_state_changed,
        plot.presentation_changed,
        plot.cursor_changed,
        plot.state_reset,
    ):
        signal.connect(lambda *_args: events.append("event"))

    original = plot.set_curve_style
    calls = 0

    def fail_once(key: str, style: CurveStyle) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("injected layout failure")
        original(key, style)

    monkeypatch.setattr(plot, "set_curve_style", fail_once)
    with pytest.raises(RuntimeError, match="injected layout failure"):
        plot.load_layout()

    assert PlotSnapshot.capture(plot) == before
    assert events == []
    _dispose(qapp, plot)


def test_contextual_layout_validation_precedes_widget_mutation(
    qapp: QApplication,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "layout.json"
    layout = _layout(theme="dark")
    layout["cursors"] = [
        _cursor("first", name="Changed axis", cursor_type="y"),
        _cursor("second", name="Second axis", cursor_type="x"),
    ]
    layout["cursor_pairs"] = [_cursor_pair("bad", "first", "second")]
    _write(path, _document(layout))
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    first = plot.add_cursor("x", key="first")
    second = plot.add_cursor("x", key="second")
    plot.add_cursor_pair(first, second, key="current-pair")
    before = PlotSnapshot.capture(plot)
    mutations: list[str] = []
    original = plot.set_theme

    def track_theme(theme: object) -> None:
        mutations.append("theme")
        original(theme)  # type: ignore[arg-type]

    monkeypatch.setattr(plot, "set_theme", track_theme)
    with pytest.raises(LayoutFileError, match="same axis"):
        plot.load_layout()

    assert mutations == []
    assert PlotSnapshot.capture(plot) == before
    _dispose(qapp, plot)


def test_custom_registered_appearance_roundtrips(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.json"
    registry = PyQtLabGraphStyleRegistry()
    theme = PyQtLabGraphTheme(
        name="laboratory",
        plot_background="#102030",
        grid=QColor("#405060"),
        border="#708090",
    )
    plot_style = PyQtLabGraphPlotStyle(
        name="laboratory",
        curve_styles=(CurveStyle(line_color="#ABCDEF"),),
    )
    registry.register_theme(theme)
    registry.register_plot_style(plot_style)

    source = PyQtLabGraphWidget(
        plot_identifier="plot",
        layout_path=path,
        style_registry=registry,
        theme=theme,
        plot_style=plot_style,
    )
    source.save_layout()
    target = PyQtLabGraphWidget(
        plot_identifier="plot",
        layout_path=path,
        style_registry=registry,
    )

    assert target.load_layout()
    assert target.theme is theme
    assert target.plot_style is plot_style
    _dispose(qapp, target, source)


def test_state_reset_refreshes_companion_projections(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.json"
    layout = _layout()
    layout["curves"] = {
        "sensor": {"visible": False, "style": CurveStyle().__dict__},
    }
    layout["cursors"] = [
        _cursor("saved", name="Saved", cursor_type="y", value=2.0),
    ]
    _write(path, _document(layout))
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    plot.add_curve("sensor")
    toolbar = PyQtLabGraphToolbar(plot)
    legend = PyQtLabGraphLegend(plot)
    cursor_widget = PyQtLabGraphCursorWidget(plot)

    assert plot.load_layout()

    assert not toolbar.autoscale_x_action.isChecked()
    assert not toolbar.autoscale_y_action.isChecked()
    assert not legend.items_by_key["sensor"].label.isEnabled()
    assert cursor_widget.model.cursor_keys() == ("saved",)
    _dispose(qapp, cursor_widget, legend, toolbar, plot)


def test_layout_keeps_host_curves_and_replaces_cursor_state(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.json"
    layout = _layout()
    layout["curves"] = {
        "saved-only": {"visible": False, "style": CurveStyle().__dict__},
    }
    layout["cursors"] = [
        _cursor("saved", name="Saved", value=4.0, label_visible=True)
    ]
    _write(path, _document(layout))
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    plot.add_curve("current-only")
    current_style = CurveStyle(line_color="#009E73")
    plot.set_curve_style("current-only", current_style)
    current_cursor = plot.add_cursor("y", key="current-cursor", value=2.0)
    plot.set_selected_cursor_keys([current_cursor])

    assert plot.load_layout()

    assert plot.curve_style("current-only") == current_style
    assert [state.key for state in plot.cursor_states()] == ["saved"]
    assert plot.selected_cursor_keys() == []
    _dispose(qapp, plot)


def test_layout_rejects_missing_snap_target_without_mutation(
    qapp: QApplication,
    tmp_path: Path,
) -> None:
    path = tmp_path / "layout.json"
    layout = _layout()
    layout["cursors"] = [
        _cursor(
            "saved",
            snap_target_curve_key="missing",
            follow_target_visibility=True,
        )
    ]
    _write(path, _document(layout))
    plot = PyQtLabGraphWidget(plot_identifier="plot", layout_path=path)
    plot.add_curve("current")
    plot.add_cursor("y", key="current-cursor", value=2.0)
    before = PlotSnapshot.capture(plot)
    events: list[str] = []
    plot.state_reset.connect(lambda: events.append("reset"))

    with pytest.raises(LayoutFileError, match="unknown snap target curve"):
        plot.load_layout()

    assert PlotSnapshot.capture(plot) == before
    assert events == []
    _dispose(qapp, plot)


def test_customize_rollback_uses_runtime_snapshot(qapp: QApplication) -> None:
    plot = PyQtLabGraphWidget(plot_identifier="customize")
    _configure_runtime_state(plot)
    session = CustomizeSession(plot)
    before = PlotSnapshot.capture(plot)

    plot.set_theme("dark")
    plot.remove_cursor("first")
    plot.set_selected_cursor_keys([])
    session.rollback()

    assert isinstance(session.baseline, PlotSnapshot)
    assert PlotSnapshot.capture(plot) == before
    _dispose(qapp, plot)
