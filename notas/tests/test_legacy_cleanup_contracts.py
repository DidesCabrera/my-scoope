import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


REMOVED_LEGACY_PATHS = [
    "notas/interface/views/content_template.py",
    "notas/presentation/composition/viewmodel/components/builder_kpis.py",
    "notas/presentation/composition/viewmodel/inbox/inbox_list_builder.py",
    "notas/templates/components/alloc_bar_js.html",
    "notas/templates/components/dash_kpi_mini.html",
    "notas/templates/components/list_header_profile.html",
    "notas/templates/components/program_metric_chart.html",
    "notas/templates/notas/dailyplans/attach_meal.html",
    "notas/templates/notas/inbox.html",
    "notas/templates/notas/meals/mealfood_edit.html",
]


class LegacyCleanupContractsTests(unittest.TestCase):
    def test_known_legacy_files_stay_removed(self):
        for relative_path in REMOVED_LEGACY_PATHS:
            self.assertFalse((PROJECT_ROOT / relative_path).exists(), relative_path)

    def test_patch_residue_files_are_not_present(self):
        residue_suffixes = {".orig", ".rej"}
        residues = [
            str(path.relative_to(PROJECT_ROOT))
            for path in PROJECT_ROOT.rglob("*")
            if path.is_file() and path.suffix in residue_suffixes
        ]
        self.assertEqual(residues, [])
