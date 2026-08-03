from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "pyqtlabgraph"


def _module_name(path: Path) -> str:
    relative = path.relative_to(PACKAGE_ROOT).with_suffix("")
    if relative.name == "__init__":
        relative = relative.parent
    suffix = ".".join(relative.parts)
    return "pyqtlabgraph" if not suffix else f"pyqtlabgraph.{suffix}"


def _is_type_checking_guard(test: ast.expr) -> bool:
    return (
        isinstance(test, ast.Name)
        and test.id == "TYPE_CHECKING"
        or isinstance(test, ast.Attribute)
        and isinstance(test.value, ast.Name)
        and test.value.id == "typing"
        and test.attr == "TYPE_CHECKING"
    )


class _RuntimeImportCollector(ast.NodeVisitor):
    def __init__(self, module: str) -> None:
        self.module = module
        self.imports: set[str] = set()
        self._type_checking_depth = 0

    def visit_If(self, node: ast.If) -> None:
        if _is_type_checking_guard(node.test):
            self._type_checking_depth += 1
            for statement in node.body:
                self.visit(statement)
            self._type_checking_depth -= 1
            for statement in node.orelse:
                self.visit(statement)
            return
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        if self._type_checking_depth:
            return
        for alias in node.names:
            if alias.name == "pyqtlabgraph" or alias.name.startswith("pyqtlabgraph."):
                self.imports.add(alias.name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if self._type_checking_depth:
            return
        if node.level:
            package_parts = self.module.split(".")[:-1]
            base_parts = package_parts[: len(package_parts) - node.level + 1]
            if node.module:
                base_parts.extend(node.module.split("."))
            imported = ".".join(base_parts)
        else:
            imported = node.module or ""
        if imported == "pyqtlabgraph" or imported.startswith("pyqtlabgraph."):
            self.imports.add(imported)


def _runtime_import_graph() -> dict[str, set[str]]:
    paths = sorted(PACKAGE_ROOT.rglob("*.py"))
    modules = {_module_name(path) for path in paths}
    graph: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        module = _module_name(path)
        collector = _RuntimeImportCollector(module)
        collector.visit(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        graph[module].update(
            imported for imported in collector.imports if imported in modules
        )
    return graph


def _find_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    visited: set[str] = set()
    active: list[str] = []
    active_set: set[str] = set()

    def visit(module: str) -> list[str] | None:
        if module in active_set:
            start = active.index(module)
            return [*active[start:], module]
        if module in visited:
            return None
        active.append(module)
        active_set.add(module)
        for dependency in sorted(graph.get(module, ())):
            cycle = visit(dependency)
            if cycle is not None:
                return cycle
        active.pop()
        active_set.remove(module)
        visited.add(module)
        return None

    for module in sorted(graph):
        cycle = visit(module)
        if cycle is not None:
            return cycle
    return None


def test_productive_modules_do_not_reach_into_foreign_private_attributes() -> None:
    violations: list[str] = []
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        local_classes = {
            node.name for node in tree.body if isinstance(node, ast.ClassDef)
        }
        allowed_receivers = {"self", "cls", *local_classes}
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Attribute)
                and node.attr.startswith("_")
                and not node.attr.startswith("__")
                and isinstance(node.value, ast.Name)
                and node.value.id not in allowed_receivers
            ):
                relative = path.relative_to(REPO_ROOT)
                violations.append(
                    f"{relative}:{node.lineno}: "
                    f"{node.value.id}.{node.attr}"
                )

    assert not violations, (
        "Productive code must not access another component's private attributes:\n"
        + "\n".join(violations)
    )


def test_productive_runtime_import_graph_is_acyclic() -> None:
    cycle = _find_cycle(_runtime_import_graph())
    assert cycle is None, f"Runtime import cycle: {' -> '.join(cycle or ())}"
