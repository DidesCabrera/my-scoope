from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[3]

# These limits are a ratchet, not a target.  A file may become smaller without
# updating the budget, but any growth must first move responsibility elsewhere.
HOTSPOT_LINE_BUDGETS = {
    "notas/domain/models.py": 100,
    "ai_assistant/application/orchestrator.py": 1_300,
    "notas/application/ai_intake/nutrition_brief.py": 2_370,
    "admin_operations/service_modules/food_catalog.py": 2_104,
    "notas/application/ai_intake/real_provider_validation.py": 1_510,
    "notas/application/ai_intake/chat_engine.py": 1_346,
}


class PythonHotspotBudgetTests(TestCase):
    def test_reviewed_hotspots_cannot_grow(self):
        overruns = []
        for relative_path, maximum in HOTSPOT_LINE_BUDGETS.items():
            line_count = len((ROOT / relative_path).read_text().splitlines())
            if line_count > maximum:
                overruns.append(f"{relative_path}: {line_count} lines > {maximum}")

        self.assertEqual(
            overruns,
            [],
            "Extract responsibility from the module instead of increasing its budget:\n"
            + "\n".join(overruns),
        )
