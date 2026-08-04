from pathlib import Path

from django.test import SimpleTestCase


class AICreditAuthorityContractTests(SimpleTestCase):
    def test_runtime_does_not_consume_legacy_ai_credit_models(self):
        project_root = Path(__file__).resolve().parents[3]
        allowed = {
            Path("ai_assistant/models.py"),
            Path("ai_assistant/admin.py"),
            Path("ai_assistant/application/credit_reconciliation.py"),
        }
        offenders = []
        for path in project_root.rglob("*.py"):
            relative = path.relative_to(project_root)
            if (
                relative in allowed
                or "migrations" in relative.parts
                or "tests" in relative.parts
                or relative.name.startswith("test_")
            ):
                continue
            source = path.read_text(encoding="utf-8")
            if "AIUserCreditQuota" in source or "AICreditLedger" in source:
                offenders.append(str(relative))

        self.assertEqual(
            offenders,
            [],
            "Legacy AI credit models may only be read by the explicit reconciliation boundary.",
        )
