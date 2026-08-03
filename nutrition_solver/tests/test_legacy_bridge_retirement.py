from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[2]
LEGACY_MODULES = (
    ROOT / "notas/application/nutrition_engine/contracts.py",
    ROOT / "notas/application/nutrition_engine/models.py",
    ROOT / "notas/application/nutrition_engine/portion_solver.py",
    ROOT / "notas/application/nutrition_engine/validators.py",
)


class NutritionSolverLegacyBridgeRetirementTests(SimpleTestCase):
    def test_legacy_import_modules_are_absent(self):
        self.assertEqual([str(path) for path in LEGACY_MODULES if path.exists()], [])

    def test_production_consumers_use_solver_owned_modules(self):
        generator = (
            ROOT / "notas/application/ai_intake/dailyplan_generator.py"
        ).read_text()
        self.assertIn("from nutrition_solver.domain.models import", generator)
        self.assertIn("from nutrition_solver.application.portion_solver import", generator)
        self.assertIn("from nutrition_solver.application.validators import", generator)
        self.assertNotIn("notas.application.nutrition_engine.models", generator)
        self.assertNotIn("notas.application.nutrition_engine.portion_solver", generator)
        self.assertNotIn("notas.application.nutrition_engine.validators", generator)
