from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.test import SimpleTestCase

from core.document_registry import build_document_registry


class DocumentRegistryTests(SimpleTestCase):
    def test_repository_registry_has_unique_consistent_decision_ids(self):
        registry = build_document_registry(Path(settings.BASE_DIR))

        errors = [finding.as_dict() for finding in registry.findings if finding.severity == "error"]
        self.assertEqual(errors, [])
        self.assertTrue(any(entry.identifier == "0130" for entry in registry.entries))
        self.assertTrue(any(entry.identifier == "PCF00" for entry in registry.entries))

    def test_duplicate_decisions_are_detected(self):
        with TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            decisions = root / "docs/20_decisions"
            cycles = root / "docs/10_active_cycles"
            decisions.mkdir(parents=True)
            cycles.mkdir(parents=True)
            (decisions / "0001-first.md").write_text("# 0001 First\n\nStatus: accepted\n")
            (decisions / "0001-second.md").write_text("# 0001 Second\n\nStatus: accepted\n")

            registry = build_document_registry(root)

        self.assertFalse(registry.valid)
        self.assertTrue(
            any(finding.code == "decision.duplicate_identifier" for finding in registry.findings)
        )
