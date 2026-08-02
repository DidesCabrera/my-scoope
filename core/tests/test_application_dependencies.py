import ast
from collections import defaultdict
from pathlib import Path

from django.test import SimpleTestCase

from core.application_dependencies import (
    ADMIN_OPERATIONS_HTTP_IMPORT_ALLOWLIST,
    ALLOWED_APP_DEPENDENCIES,
    PROJECT_APPS,
    TRANSITIONAL_APP_EDGES,
)


ROOT = Path(__file__).resolve().parents[2]


def _production_python_files(app_name):
    for path in (ROOT / app_name).rglob("*.py"):
        relative_parts = path.relative_to(ROOT).parts
        if "__pycache__" in relative_parts or "migrations" in relative_parts or "tests" in relative_parts:
            continue
        if path.name.startswith("test"):
            continue
        yield path


def _imports(path):
    tree = ast.parse(path.read_text(), filename=str(path))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    return imported


def _actual_app_dependencies():
    dependencies = {app_name: set() for app_name in PROJECT_APPS}
    for app_name in PROJECT_APPS:
        for path in _production_python_files(app_name):
            for imported in _imports(path):
                target = imported.split(".", 1)[0]
                if target in PROJECT_APPS and target != app_name:
                    dependencies[app_name].add(target)
    return {key: frozenset(value) for key, value in dependencies.items()}


def _module_graph():
    module_paths = {}
    for app_name in PROJECT_APPS:
        for path in _production_python_files(app_name):
            parts = list(path.relative_to(ROOT).with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            module_paths[".".join(parts)] = path

    graph = {module: set() for module in module_paths}
    for module, path in module_paths.items():
        for imported in _imports(path):
            target = imported
            while target and target not in module_paths:
                target = target.rsplit(".", 1)[0] if "." in target else ""
            if target in module_paths and target != module:
                graph[module].add(target)
    return graph


def _cyclic_components(graph):
    index = 0
    stack = []
    on_stack = set()
    indexes = {}
    lowlinks = {}
    components = []

    def visit(node):
        nonlocal index
        indexes[node] = lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in graph[node]:
            if target not in indexes:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indexes[target])

        if lowlinks[node] == indexes[node]:
            component = []
            while True:
                target = stack.pop()
                on_stack.remove(target)
                component.append(target)
                if target == node:
                    break
            if len(component) > 1:
                components.append(tuple(sorted(component)))

    for node in graph:
        if node not in indexes:
            visit(node)
    return sorted(components)


class ApplicationDependencyTests(SimpleTestCase):
    def test_cross_app_dependencies_match_the_explicit_policy(self):
        self.assertEqual(_actual_app_dependencies(), ALLOWED_APP_DEPENDENCIES)

    def test_transitional_edges_are_current_allowed_edges(self):
        allowed_edges = {
            (source, target)
            for source, targets in ALLOWED_APP_DEPENDENCIES.items()
            for target in targets
        }
        self.assertTrue(set(TRANSITIONAL_APP_EDGES).issubset(allowed_edges))

    def test_production_module_import_graph_has_no_cycles(self):
        self.assertEqual(_cyclic_components(_module_graph()), [])

    def test_admin_operations_http_import_debt_does_not_grow(self):
        offenders = set()
        forbidden = ("django.contrib.messages", "django.http", "django.shortcuts", "django.views")
        for path in _production_python_files("admin_operations"):
            if path.name == "views.py" or path.name.startswith("interface_"):
                continue
            for imported in _imports(path):
                if imported.startswith(forbidden):
                    offenders.add(f"{path.relative_to(ROOT)} imports {imported}")
        self.assertEqual(offenders, set(ADMIN_OPERATIONS_HTTP_IMPORT_ALLOWLIST))
