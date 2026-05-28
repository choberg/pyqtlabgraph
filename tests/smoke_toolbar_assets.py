from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLBAR_PATH = REPO_ROOT / "pyqt_lab_graph" / "toolbar.py"
ASSETS_PATH = REPO_ROOT / "pyqt_lab_graph" / "assets"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


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
    package_data = pyproject["tool"]["setuptools"]["package-data"]["pyqt_lab_graph"]
    return {str(item) for item in package_data}


def main() -> None:
    toolbar_icons = _toolbar_icon_filenames()
    assert toolbar_icons, "Toolbar should reference packaged runtime icons."
    assert all(filename.endswith(".png") for filename in toolbar_icons)

    active_asset_filenames = {
        path.name for path in ASSETS_PATH.iterdir() if path.is_file()
    }
    assert active_asset_filenames == toolbar_icons

    for filename in sorted(toolbar_icons):
        asset_path = ASSETS_PATH / filename
        assert asset_path.exists(), f"Missing toolbar icon: {filename}"
        assert asset_path.read_bytes().startswith(PNG_SIGNATURE), (
            f"Toolbar icon is not a PNG file: {filename}"
        )

    package_assets = _package_data_assets()
    assert "py.typed" in package_assets, "py.typed must be in package-data"
    package_assets = package_assets - {"py.typed"}
    expected_package_assets = {f"assets/{filename}" for filename in toolbar_icons}
    assert package_assets == expected_package_assets
    assert all(path.startswith("assets/") for path in package_assets)
    assert all(path.endswith(".png") for path in package_assets)
    assert not any("original_icons" in path or path.endswith(".svg") for path in package_assets)

    print("toolbar assets smoke ok")


if __name__ == "__main__":
    sys.exit(main())
