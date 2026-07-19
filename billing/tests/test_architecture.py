import ast
from pathlib import Path

from django.test import SimpleTestCase


BILLING_ROOT = Path(__file__).resolve().parents[1]


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class BillingArchitectureTests(SimpleTestCase):
    def test_application_does_not_depend_on_infrastructure_or_interface(self):
        forbidden_prefixes = ("billing.infrastructure", "billing.interface")
        forbidden_django_edges = ("django.http", "django.shortcuts", "django.contrib.messages")

        for path in (BILLING_ROOT / "application").rglob("*.py"):
            imported = _imports(path)
            violations = {
                module
                for module in imported
                if module.startswith(forbidden_prefixes) or module.startswith(forbidden_django_edges)
            }
            self.assertEqual(violations, set(), f"{path.relative_to(BILLING_ROOT)} crosses inward boundaries")

    def test_infrastructure_does_not_depend_on_http_interface(self):
        for path in (BILLING_ROOT / "infrastructure").rglob("*.py"):
            violations = {module for module in _imports(path) if module.startswith("billing.interface")}
            self.assertEqual(violations, set(), f"{path.relative_to(BILLING_ROOT)} imports interface")

    def test_application_provider_contracts_are_framework_neutral(self):
        imported = _imports(BILLING_ROOT / "application" / "contracts.py")

        self.assertFalse(any(module.startswith("django") for module in imported))
        self.assertFalse(any(module.startswith("requests") for module in imported))
