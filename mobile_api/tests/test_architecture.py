from __future__ import annotations

import ast
from pathlib import Path

from django.test import SimpleTestCase

from mobile_api.architecture import route_domain


ROOT = Path(__file__).resolve().parents[2]


class MobileAPIArchitectureTests(SimpleTestCase):
    def test_every_v1_route_has_an_explicit_domain_owner(self):
        tree = ast.parse((ROOT / "mobile_api/api.py").read_text())
        routes = []
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call) or not decorator.args:
                    continue
                function = decorator.func
                if not (
                    isinstance(function, ast.Attribute)
                    and isinstance(function.value, ast.Name)
                    and function.value.id == "api"
                    and function.attr in {"delete", "get", "patch", "post", "put"}
                ):
                    continue
                if isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                    routes.append((node.name, decorator.args[0].value))

        self.assertGreaterEqual(len(routes), 79)
        unowned = [f"{name}: {path}" for name, path in routes if route_domain(path) is None]
        self.assertEqual(unowned, [])

    def test_support_helpers_are_outside_the_route_registry_facade(self):
        source = (ROOT / "mobile_api/api.py").read_text()

        self.assertIn("from mobile_api.api_support import", source)
        self.assertNotIn("def _calendarization_error", source)
        self.assertNotIn("def _proposal_error", source)
