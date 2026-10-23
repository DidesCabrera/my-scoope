import json
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

LEGACY_DAILY_PLAN_TERM = re.compile(r"\bplan(?:es)?\s+diarios?\b", re.IGNORECASE)


class VisibleProductVocabularyTests(SimpleTestCase):
    def test_visible_surfaces_do_not_reintroduce_legacy_daily_plan_label(self):
        root = Path(settings.BASE_DIR)
        surfaces = (
            root / "accounts/templates",
            root / "core/templates",
            root / "mobile/src",
            root / "mobile_api",
            root / "notas/interface",
            root / "notas/presentation",
            root / "notas/static",
            root / "notas/templates",
        )
        extensions = {".html", ".js", ".py", ".ts", ".tsx"}
        findings = []
        for surface in surfaces:
            for path in surface.rglob("*"):
                if path.suffix not in extensions:
                    continue
                if LEGACY_DAILY_PLAN_TERM.search(path.read_text(encoding="utf-8")):
                    findings.append(str(path.relative_to(root)))
        self.assertEqual(findings, [])

    def test_vocabulary_records_spanish_and_future_english_meaning(self):
        root = Path(settings.BASE_DIR)
        payload = json.loads(
            (root / "docs/00_current/PRODUCT_VOCABULARY.json").read_text(encoding="utf-8")
        )
        daily_plan = payload["entities"]["daily_plan"]
        self.assertEqual(daily_plan["es"]["singular"], "Minuta diaria")
        self.assertEqual(daily_plan["es"]["library_title"], "Mis minutas diarias")
        self.assertEqual(daily_plan["en"]["singular"], "Daily meal plan")
        self.assertIn("DailyPlan", daily_plan["technical_identifiers"])
