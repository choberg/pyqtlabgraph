from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_FILES = sorted((REPO_ROOT / "pyqtlabgraph").glob("*.py"))
DEMO_FILES = [
    REPO_ROOT / "examples" / "_demo_theme.py",
    REPO_ROOT / "examples" / "demo_thermostat.py",
    REPO_ROOT / "examples" / "demo_time_fft.py",
    REPO_ROOT / "examples" / "demo_minimal.py",
    REPO_ROOT / "examples" / "demo_cursor.py",
]
SMOKE_FILES = [
    REPO_ROOT / "tests" / "customize_smoke_helpers.py",
    REPO_ROOT / "tests" / "cursor_smoke_helpers.py",
    REPO_ROOT / "tests" / "smoke_adaptive_performance.py",
    REPO_ROOT / "tests" / "smoke_axis_formatting.py",
    REPO_ROOT / "tests" / "smoke_customize_dialog_structure.py",
    REPO_ROOT / "tests" / "smoke_customize_dialog_preview.py",
    REPO_ROOT / "tests" / "smoke_customize_dialog_save.py",
    REPO_ROOT / "tests" / "smoke_demo_theme_toggle.py",
    REPO_ROOT / "tests" / "smoke_cursor_demo.py",
    REPO_ROOT / "tests" / "smoke_cursor_dragging.py",
    REPO_ROOT / "tests" / "smoke_cursor_domain.py",
    REPO_ROOT / "tests" / "smoke_cursor_plot_items.py",
    REPO_ROOT / "tests" / "smoke_cursor_refresh.py",
    REPO_ROOT / "tests" / "smoke_cursor_display_editing_settings.py",
    REPO_ROOT / "tests" / "smoke_cursor_selection_keyboard.py",
    REPO_ROOT / "tests" / "smoke_cursor_pairing_drag_drop.py",
    REPO_ROOT / "tests" / "smoke_cursor_embedding_host_style.py",
    REPO_ROOT / "tests" / "smoke_cursor_widget_api.py",
    REPO_ROOT / "tests" / "smoke_legend_interaction.py",
    REPO_ROOT / "tests" / "smoke_layout_persistence.py",
    REPO_ROOT / "tests" / "smoke_minimal_demo.py",
    REPO_ROOT / "tests" / "smoke_packaging_metadata.py",
    REPO_ROOT / "tests" / "smoke_public_api_cleanup.py",
    REPO_ROOT / "tests" / "smoke_thermostat_demo_ui.py",
    REPO_ROOT / "tests" / "smoke_time_fft_demo.py",
    REPO_ROOT / "tests" / "smoke_toolbar_assets.py",
    REPO_ROOT / "tests" / "smoke_toolbar_interaction.py",
    REPO_ROOT / "tests" / "smoke_version_metadata.py",
    REPO_ROOT / "tests" / "test_axis_dragging.py",
    REPO_ROOT / "tests" / "test_architecture_guardrails.py",
    REPO_ROOT / "tests" / "test_basic.py",
    REPO_ROOT / "tests" / "test_curve_command_contracts.py",
    REPO_ROOT / "tests" / "test_core_boundaries_and_dispatch.py",
    REPO_ROOT / "tests" / "test_runtime_snapshot_and_layouts.py",
    REPO_ROOT / "tests" / "test_cursor_boundaries.py",
    REPO_ROOT / "tests" / "test_validated_state_and_registry.py",
    REPO_ROOT / "tests" / "verify_installed_package.py",
    REPO_ROOT / "tests" / "run_smoke_checks.py",
]


@dataclass(frozen=True)
class SmokeCommand:
    label: str
    args: list[str]
    qt_offscreen: bool = False


def _syntax_check(paths: list[Path]) -> None:
    print("[smoke] syntax check package, demos, and smoke checks", flush=True)
    for path in paths:
        source = path.read_text(encoding="utf-8")
        compile(source, str(path.relative_to(REPO_ROOT)), "exec")


def _run(command: SmokeCommand) -> None:
    env = os.environ.copy()
    env.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    if command.qt_offscreen:
        env.setdefault("QT_QPA_PLATFORM", "offscreen")

    print(f"[smoke] {command.label}", flush=True)
    subprocess.run(command.args, cwd=REPO_ROOT, env=env, check=True)


def main() -> int:
    _syntax_check(PACKAGE_FILES + DEMO_FILES + SMOKE_FILES)

    commands = [
        SmokeCommand(
            "focused architecture, state, registry, curve, cursor, and layout pytest suite",
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "tests/test_architecture_refactor.py",
                "tests/test_architecture_guardrails.py",
                "tests/test_axis_dragging.py",
                "tests/test_core_boundaries_and_dispatch.py",
                "tests/test_cursor_boundaries.py",
                "tests/test_curve_command_contracts.py",
                "tests/test_runtime_snapshot_and_layouts.py",
                "tests/test_validated_state_and_registry.py",
            ],
            qt_offscreen=True,
        ),
        SmokeCommand("adaptive performance", [sys.executable, "tests/smoke_adaptive_performance.py"], qt_offscreen=True),
        SmokeCommand("axis formatting", [sys.executable, "tests/smoke_axis_formatting.py"], qt_offscreen=True),
        SmokeCommand("customize dialog structure", [sys.executable, "tests/smoke_customize_dialog_structure.py"], qt_offscreen=True),
        SmokeCommand("customize dialog preview", [sys.executable, "tests/smoke_customize_dialog_preview.py"], qt_offscreen=True),
        SmokeCommand("customize dialog save", [sys.executable, "tests/smoke_customize_dialog_save.py"], qt_offscreen=True),
        SmokeCommand("demo theme toggle", [sys.executable, "tests/smoke_demo_theme_toggle.py"], qt_offscreen=True),
        SmokeCommand("cursor demo", [sys.executable, "tests/smoke_cursor_demo.py"], qt_offscreen=True),
        SmokeCommand("cursor dragging", [sys.executable, "tests/smoke_cursor_dragging.py"], qt_offscreen=True),
        SmokeCommand("cursor plot items", [sys.executable, "tests/smoke_cursor_plot_items.py"], qt_offscreen=True),
        SmokeCommand("cursor refresh", [sys.executable, "tests/smoke_cursor_refresh.py"], qt_offscreen=True),
        SmokeCommand("cursor display and settings", [sys.executable, "tests/smoke_cursor_display_editing_settings.py"], qt_offscreen=True),
        SmokeCommand("cursor selection and keyboard", [sys.executable, "tests/smoke_cursor_selection_keyboard.py"], qt_offscreen=True),
        SmokeCommand("cursor pairing and drag-drop", [sys.executable, "tests/smoke_cursor_pairing_drag_drop.py"], qt_offscreen=True),
        SmokeCommand("cursor embedding and host style", [sys.executable, "tests/smoke_cursor_embedding_host_style.py"], qt_offscreen=True),
        SmokeCommand("legend interaction", [sys.executable, "tests/smoke_legend_interaction.py"], qt_offscreen=True),
        SmokeCommand("minimal demo", [sys.executable, "tests/smoke_minimal_demo.py"], qt_offscreen=True),
        SmokeCommand("packaging metadata", [sys.executable, "tests/smoke_packaging_metadata.py"]),
        SmokeCommand("thermostat demo ui", [sys.executable, "tests/smoke_thermostat_demo_ui.py"], qt_offscreen=True),
        SmokeCommand("time fft demo", [sys.executable, "tests/smoke_time_fft_demo.py"], qt_offscreen=True),
        SmokeCommand("toolbar assets", [sys.executable, "tests/smoke_toolbar_assets.py"]),
        SmokeCommand("toolbar interaction", [sys.executable, "tests/smoke_toolbar_interaction.py"], qt_offscreen=True),
        SmokeCommand("public api cleanup", [sys.executable, "tests/smoke_public_api_cleanup.py"], qt_offscreen=True),
        SmokeCommand("version metadata", [sys.executable, "tests/smoke_version_metadata.py"]),
    ]

    for command in commands:
        _run(command)

    print("[smoke] all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
