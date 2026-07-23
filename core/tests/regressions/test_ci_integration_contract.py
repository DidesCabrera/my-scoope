from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[3]


class CiIntegrationContractTests(SimpleTestCase):
    def test_workflow_runs_for_staging_pushes(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()

        self.assertIn("      - staging", workflow)

    def test_ci_checks_migration_drift_and_repository_hygiene(self):
        script = (ROOT / "scripts/ci_django_checks.sh").read_text()

        self.assertIn("scripts/check_repository_hygiene.sh", script)
        self.assertIn("manage.py makemigrations --check --dry-run", script)
