from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from core.transition_registry import load_transition_registry, validate_transition_registry


class TransitionRegistryTests(SimpleTestCase):
    def test_current_transition_registry_is_complete_and_valid(self):
        root = Path(settings.BASE_DIR)

        entries = load_transition_registry(root)
        errors = validate_transition_registry(root)

        self.assertEqual(errors, [])
        self.assertGreaterEqual(len(entries), 6)
        for entry in entries:
            self.assertTrue(entry.current_consumers)
            self.assertTrue(entry.exit_evidence)

    def test_registry_distinguishes_transitional_from_intentionally_durable(self):
        statuses = {entry.status for entry in load_transition_registry(Path(settings.BASE_DIR))}

        self.assertEqual(statuses, {"transitional", "intentionally_durable"})
