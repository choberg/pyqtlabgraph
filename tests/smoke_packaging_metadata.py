from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pyqtlabgraph  # noqa: E402

DIRECT_RUNTIME_DEPENDENCIES = {
    "numpy",
    "PySide6",
    "pyqtgraph",
}
CURSOR_PUBLIC_EXPORTS = {
    "CursorPairState",
    "CursorState",
    "CursorStyle",
    "CursorType",
    "PyQtLabGraphCursorWidget",
}
STYLE_PUBLIC_EXPORTS = {
    "CurveStyle",
    "PyQtLabGraphPlotStyle",
    "PyQtLabGraphStyleRegistry",
    "PyQtLabGraphTheme",
}
FORBIDDEN_PACKAGE_DATA_PARTS = {
    "bak",
    "original_icons",
}
FORBIDDEN_PACKAGE_DATA_SUFFIXES = {
    ".layout.json",
    ".svg",
}


def main() -> int:
    pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    dependency_names = {_dependency_name(dependency) for dependency in dependencies}

    missing_dependencies = DIRECT_RUNTIME_DEPENDENCIES - dependency_names
    assert not missing_dependencies, f"Missing runtime dependencies: {sorted(missing_dependencies)}"

    package_data = pyproject["tool"]["setuptools"]["package-data"]["pyqtlabgraph"]
    for entry in package_data:
        parts = set(Path(entry).parts)
        assert not (parts & FORBIDDEN_PACKAGE_DATA_PARTS), entry
        assert not any(entry.endswith(suffix) for suffix in FORBIDDEN_PACKAGE_DATA_SUFFIXES), entry
    assert all(entry.endswith(".png") or entry == "py.typed" for entry in package_data)

    required_exports = CURSOR_PUBLIC_EXPORTS | STYLE_PUBLIC_EXPORTS
    missing_exports = {
        name
        for name in required_exports
        if not hasattr(pyqtlabgraph, name) or name not in pyqtlabgraph.__all__
    }
    assert not missing_exports, f"Missing public exports: {sorted(missing_exports)}"

    print("packaging metadata smoke ok")
    return 0


def _dependency_name(dependency: str) -> str:
    match = re.match(r"\s*([A-Za-z0-9_.-]+)", dependency)
    if match is None:
        raise AssertionError(f"Could not parse dependency name: {dependency!r}")
    return match.group(1)


if __name__ == "__main__":
    raise SystemExit(main())
