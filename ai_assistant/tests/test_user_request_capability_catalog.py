from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

CATALOG_PATH = (
    Path(settings.BASE_DIR)
    / "docs"
    / "00_current"
    / "features"
    / "ai_assistant"
    / "user_request_capability_catalog.md"
)
ROW_PATTERN = re.compile(
    r"^\| (?P<id>(?:PR|F|M|DP|PG|C|X|A)-\d{2}) "
    r"\| (?P<request>.+?) \| (?P<resolution>.+?) "
    r"\| (?P<coverage>.+?) \| (?P<observation>.+?) \|$"
)
ALLOWED_COVERAGE = {
    "Cubierta",
    "Cubierta con límites",
    "Cubierta parcial",
    "Parcial",
    "Brecha",
    "Brecha intencional",
    "Brecha parcial",
    "UI",
    "No aplica",
}
EXPECTED_PREFIX_COUNTS = {
    "PR": 5,
    "F": 13,
    "M": 14,
    "DP": 14,
    "PG": 10,
    "C": 10,
    "X": 10,
    "A": 6,
}


def _catalog_rows():
    rows = []
    for line in CATALOG_PATH.read_text(encoding="utf-8").splitlines():
        match = ROW_PATTERN.match(line)
        if match:
            rows.append(match.groupdict())
    return rows


class UserRequestCapabilityCatalogContractTests(SimpleTestCase):
    def test_catalog_has_unique_structured_rows_for_every_declared_family(self):
        rows = _catalog_rows()
        identifiers = [row["id"] for row in rows]

        self.assertEqual(len(rows), 82)
        self.assertEqual(len(identifiers), len(set(identifiers)))
        self.assertEqual(
            {
                prefix: sum(identifier.startswith(f"{prefix}-") for identifier in identifiers)
                for prefix in EXPECTED_PREFIX_COUNTS
            },
            EXPECTED_PREFIX_COUNTS,
        )

    def test_every_row_has_a_supported_coverage_state_and_actionable_text(self):
        for row in _catalog_rows():
            with self.subTest(capability_id=row["id"]):
                self.assertIn(row["coverage"], ALLOWED_COVERAGE)
                self.assertGreaterEqual(len(row["request"].strip()), 8)
                self.assertGreaterEqual(len(row["resolution"].strip()), 3)
                self.assertGreaterEqual(len(row["observation"].strip()), 12)

    def test_high_value_regression_cases_remain_in_the_living_catalog(self):
        identifiers = {row["id"] for row in _catalog_rows()}
        self.assertTrue(
            {
                "F-01",
                "M-04",
                "M-08",
                "M-11",
                "DP-01",
                "DP-13",
                "DP-14",
                "PG-01",
                "C-01",
                "A-03",
            }.issubset(identifiers)
        )
