from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.test import SimpleTestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APP_ROOT = PROJECT_ROOT / "nutrition_solver"
README = APP_ROOT / "README.md"


class NutritionSolverAppBoundaryTests(SimpleTestCase):
    def test_app_is_registered_in_django_settings(self):
        self.assertIn(
            "nutrition_solver.apps.NutritionSolverConfig",
            settings.INSTALLED_APPS,
        )

        app_config = apps.get_app_config("nutrition_solver")

        self.assertEqual(app_config.name, "nutrition_solver")
        self.assertEqual(app_config.verbose_name, "Nutrition Solver")

    def test_s7_app_shell_files_exist_with_extracted_solver_layers(self):
        expected_paths = (
            "__init__.py",
            "apps.py",
            "models.py",
            "admin.py",
            "migrations/__init__.py",
            "tests/__init__.py",
            "domain/__init__.py",
            "domain/models.py",
            "domain/constants.py",
            "application/__init__.py",
            "application/contracts.py",
            "application/portion_solver.py",
            "application/validators.py",
            "application/problem_v2.py",
            "application/candidate_portfolio.py",
            "application/optimizer_v2.py",
            "application/quality.py",
            "application/shadow.py",
        )

        for relative_path in expected_paths:
            self.assertTrue(
                (APP_ROOT / relative_path).exists(),
                msg=f"Missing nutrition_solver/{relative_path}",
            )

    def test_readme_documents_current_optimization_v2_boundary(self):
        content = README.read_text()

        self.assertIn("Status: Optimization V2 implementation complete in NSO00-NSO10", content)
        self.assertIn("nutrition_solver/domain/models.py", content)
        self.assertIn("nutrition_solver/application/contracts.py", content)
        self.assertIn("nutrition_solver/application/portion_solver.py", content)
        self.assertIn("nutrition_solver/application/validators.py", content)
        self.assertIn("nutrition_solver/application/optimizer_v2.py", content)
        self.assertIn("cp_sat_v1", content)
        self.assertIn("temporary compatibility bridges", content)
        self.assertIn("been retired", content)

    def test_app_root_shell_does_not_import_product_or_ai_boundaries(self):
        forbidden_prefixes = (
            "from notas",
            "import notas",
            "from food_catalog",
            "import food_catalog",
            "from ai_assistant",
            "import ai_assistant",
        )
        offenders = []

        for path in sorted(APP_ROOT.glob("*.py")):
            if path.name == "__init__.py":
                continue
            content = path.read_text()
            for prefix in forbidden_prefixes:
                if prefix in content:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {prefix!r}")

        self.assertEqual(offenders, [])

    def test_extracted_solver_layers_do_not_import_notas_or_ai_boundaries(self):
        forbidden_prefixes = (
            "from notas",
            "import notas",
            "from food_catalog",
            "import food_catalog",
            "from ai_assistant",
            "import ai_assistant",
        )
        offenders = []

        for path in sorted((APP_ROOT / "application").glob("*.py")) + sorted((APP_ROOT / "domain").glob("*.py")):
            if path.name == "__init__.py":
                continue
            content = path.read_text()
            for prefix in forbidden_prefixes:
                if prefix in content:
                    offenders.append(f"{path.relative_to(PROJECT_ROOT)} contains {prefix!r}")

        self.assertEqual(offenders, [])
