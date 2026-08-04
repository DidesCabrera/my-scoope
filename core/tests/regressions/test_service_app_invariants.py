import ast
from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[3]
SERVICE_ONLY_APPS = ("core", "nutrition_solver")


def _concrete_model_classes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    concrete = []
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        if any(
            isinstance(base, ast.Attribute) and base.attr == "Model"
            for base in node.bases
        ):
            concrete.append(node.name)
    return concrete


class ServiceAppInvariantTests(SimpleTestCase):
    def test_service_only_apps_do_not_declare_database_models(self):
        offenders = {
            app_name: _concrete_model_classes(ROOT / app_name / "models.py")
            for app_name in SERVICE_ONLY_APPS
            if _concrete_model_classes(ROOT / app_name / "models.py")
        }

        self.assertEqual(offenders, {})

    def test_service_only_apps_have_no_schema_migrations(self):
        offenders = {
            app_name: sorted(
                path.name
                for path in (ROOT / app_name / "migrations").glob("*.py")
                if path.name != "__init__.py"
            )
            for app_name in SERVICE_ONLY_APPS
        }

        self.assertEqual(offenders, {"core": [], "nutrition_solver": []})
