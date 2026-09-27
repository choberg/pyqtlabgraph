from __future__ import annotations

from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import pyqtlabgraph

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_EXPORTS = {
    "AxisMode",
    "BUILTIN_CURVE_PALETTES",
    "BUILTIN_COLOR_GRADIENTS",
    "BUILTIN_THEMES",
    "CursorLineStyle",
    "CursorPairState",
    "CursorState",
    "CursorStyle",
    "CursorType",
    "CurveStyle",
    "LayoutFileError",
    "PlotSnapshot",
    "PyQtLabGraphCursors",
    "PyQtLabGraphCursorWidget",
    "PyQtLabGraphColorGradient",
    "PyQtLabGraphCurvePalette",
    "PyQtLabGraphLegend",
    "PyQtLabGraphStyleRegistry",
    "PyQtLabGraphTheme",
    "PyQtLabGraphToolbar",
    "PyQtLabGraphWidget",
    "TracePersistenceConfig",
    "__version__",
}
EXPECTED_ASSETS = {
    "autoscale_x.svg",
    "autoscale_y.svg",
    "customize.svg",
    "rolling_x.svg",
    "save.svg",
    "show_all.svg",
    "zoom_rect.svg",
    "zoom_x.svg",
    "zoom_y.svg",
}


def main() -> int:
    package_path = Path(pyqtlabgraph.__file__).resolve()
    assert not package_path.is_relative_to(REPO_ROOT), (
        f"Expected an installed package, imported source tree at {package_path}"
    )

    assert set(pyqtlabgraph.__all__) == EXPECTED_EXPORTS
    assert all(hasattr(pyqtlabgraph, name) for name in EXPECTED_EXPORTS)
    assert pyqtlabgraph.__version__ == version("pyqtlabgraph")

    package_files = files("pyqtlabgraph")
    assert package_files.joinpath("py.typed").is_file()
    assets = package_files.joinpath("assets")
    installed_assets = {entry.name for entry in assets.iterdir() if entry.is_file()}
    assert installed_assets == EXPECTED_ASSETS
    for filename in sorted(EXPECTED_ASSETS):
        assert b"<svg" in assets.joinpath(filename).read_bytes()

    print("installed wheel verification ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
