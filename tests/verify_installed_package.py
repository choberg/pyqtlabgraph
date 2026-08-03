from __future__ import annotations

from importlib.metadata import version
from importlib.resources import files
from pathlib import Path

import pyqtlabgraph

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_EXPORTS = {
    "AxisMode",
    "BUILTIN_PLOT_STYLES",
    "BUILTIN_THEMES",
    "CursorLineStyle",
    "CursorPairState",
    "CursorState",
    "CursorStyle",
    "CursorType",
    "CurveStyle",
    "LayoutFileError",
    "PlotSnapshot",
    "PyQtLabGraphCursorWidget",
    "PyQtLabGraphLegend",
    "PyQtLabGraphPlotStyle",
    "PyQtLabGraphStyleRegistry",
    "PyQtLabGraphTheme",
    "PyQtLabGraphToolbar",
    "PyQtLabGraphWidget",
    "__version__",
}
EXPECTED_ASSETS = {
    "autox.png",
    "autoy.png",
    "edit_params.png",
    "reset_zoom.png",
    "rolling.png",
    "saveplot.png",
    "x-zoom.png",
    "y-zoom.png",
    "zoom_area.png",
}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
        assert assets.joinpath(filename).read_bytes().startswith(PNG_SIGNATURE)

    print("installed wheel verification ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
