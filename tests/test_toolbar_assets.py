from __future__ import annotations

import ast
import tomllib
import xml.etree.ElementTree as ElementTree
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLBAR_PATH = REPO_ROOT / "pyqtlabgraph" / "toolbar.py"
ASSETS_PATH = REPO_ROOT / "pyqtlabgraph" / "assets"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def _toolbar_icon_filenames() -> set[str]:
    tree = ast.parse(TOOLBAR_PATH.read_text(encoding="utf-8"))
    filenames: set[str] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in {"_add_action", "_themed_icon"}:
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            filenames.add(first_arg.value)

    return filenames


def _package_data_assets() -> set[str]:
    pyproject = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    package_data = pyproject["tool"]["setuptools"]["package-data"]["pyqtlabgraph"]
    return {str(item) for item in package_data}


def test_toolbar_assets() -> None:
    toolbar_icons = _toolbar_icon_filenames()
    assert toolbar_icons, "Toolbar should reference packaged runtime icons."
    assert all(filename.endswith(".svg") for filename in toolbar_icons)

    active_asset_filenames = {
        path.name for path in ASSETS_PATH.iterdir() if path.is_file()
    }
    assert active_asset_filenames == toolbar_icons

    for filename in sorted(toolbar_icons):
        asset_path = ASSETS_PATH / filename
        assert asset_path.exists(), f"Missing toolbar icon: {filename}"
        root = ElementTree.parse(asset_path).getroot()
        assert root.tag == "{http://www.w3.org/2000/svg}svg", f"Not an SVG icon: {filename}"
        assert root.get("viewBox") == "0 0 24 24", f"{filename} must use the 24px grid"
        assert root.get("stroke-width") == "2", f"{filename} must use 2px strokes"
        assert root.get("fill") == "none", f"{filename} must be an unfilled line icon"
        for element in root.iter():
            assert element.get("stroke-width") in {None, "2"}, filename
            assert element.get("fill") in {None, "none"}, filename

    package_assets = _package_data_assets()
    assert "py.typed" in package_assets, "py.typed must be in package-data"
    package_assets = package_assets - {"py.typed"}
    expected_package_assets = {f"assets/{filename}" for filename in toolbar_icons}
    assert package_assets == expected_package_assets
    assert not any("original_icons" in path for path in package_assets)


def test_toolbar_icons_render_in_the_palette_color(qapp) -> None:  # type: ignore[no-untyped-def]
    from PySide6.QtGui import QColor

    from pyqtlabgraph.toolbar import _recolored_svg_icon

    color = QColor("#336699")
    for filename in sorted(_toolbar_icon_filenames()):
        icon = _recolored_svg_icon(filename, color, 24, {1.0, 2.0})
        image = icon.pixmap(48, 48).toImage()
        opaque = [
            image.pixelColor(x, y)
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y).alpha() == 255
        ]
        assert opaque, f"{filename} rendered empty"
        assert all(pixel.rgb() == color.rgb() for pixel in opaque), filename
    assert _recolored_svg_icon("missing.svg", color, 24, {1.0}).isNull()
