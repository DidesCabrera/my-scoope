from pathlib import Path

from django.test import SimpleTestCase


ROOT = Path(__file__).resolve().parents[3]


class CiIntegrationContractTests(SimpleTestCase):
    def test_workflow_runs_for_staging_pushes(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()

        self.assertIn("      - staging", workflow)

    def test_ci_checks_migration_drift_and_repository_hygiene(self):
        aggregate_script = (ROOT / "scripts/ci_django_checks.sh").read_text()
        fast_script = (ROOT / "scripts/ci_fast_checks.sh").read_text()

        self.assertIn("scripts/ci_fast_checks.sh", aggregate_script)
        self.assertIn("scripts/ci_django_full_suite.sh", aggregate_script)
        self.assertIn("scripts/check_repository_hygiene.sh", fast_script)
        self.assertIn("scripts/check_frontend_debt.py", fast_script)
        self.assertIn("scripts/check_e2e_contract.py", fast_script)
        self.assertIn("manage.py makemigrations --check --dry-run", fast_script)

    def test_ci_exposes_django_and_mcp_as_separate_quality_surfaces(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()

        self.assertIn("django-fast:", workflow)
        self.assertIn("django-full:", workflow)
        self.assertIn("mcp:", workflow)
        self.assertIn("browser-smoke:", workflow)
        self.assertIn("scripts/test_mcp.sh", workflow)
