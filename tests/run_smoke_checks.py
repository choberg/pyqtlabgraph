from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

PACKAGE_FILES = sorted((REPO_ROOT / "pyqt_lab_graph").glob("*.py"))
DEMO_FILES = [
    REPO_ROOT / "demo_thermostat.py",
    REPO_ROOT / "demo_time_fft.py",
    REPO_ROOT / "demo_minimal.py",
]
SMOKE_FILES = [
    REPO_ROOT / "tests" / "smoke_adaptive_performance.py",
    REPO_ROOT / "tests" / "smoke_axis_formatting.py",
    REPO_ROOT / "tests" / "smoke_customize_dialog.py",
    REPO_ROOT / "tests" / "smoke_legend_interaction.py",
    REPO_ROOT / "tests" / "smoke_layout_persistence.py",
    REPO_ROOT / "tests" / "smoke_public_api_cleanup.py",
    REPO_ROOT / "tests" / "smoke_thermostat_demo_ui.py",
    REPO_ROOT / "tests" / "smoke_time_fft_demo.py",
    REPO_ROOT / "tests" / "smoke_toolbar_assets.py",
    REPO_ROOT / "tests" / "smoke_toolbar_interaction.py",
    REPO_ROOT / "tests" / "smoke_version_metadata.py",
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
            "adaptive performance",
            [sys.executable, "tests/smoke_adaptive_performance.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "axis formatting",
            [sys.executable, "tests/smoke_axis_formatting.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "customize dialog",
            [sys.executable, "tests/smoke_customize_dialog.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "legend interaction",
            [sys.executable, "tests/smoke_legend_interaction.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "layout persistence",
            [sys.executable, "tests/smoke_layout_persistence.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "public api cleanup",
            [sys.executable, "tests/smoke_public_api_cleanup.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "thermostat demo ui",
            [sys.executable, "tests/smoke_thermostat_demo_ui.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "time fft demo",
            [sys.executable, "tests/smoke_time_fft_demo.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "toolbar assets",
            [sys.executable, "tests/smoke_toolbar_assets.py"],
        ),
        SmokeCommand(
            "toolbar interaction",
            [sys.executable, "tests/smoke_toolbar_interaction.py"],
            qt_offscreen=True,
        ),
        SmokeCommand(
            "version metadata",
            [sys.executable, "tests/smoke_version_metadata.py"],
        ),
    ]

    for command in commands:
        _run(command)

    print("[smoke] all checks passed", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
