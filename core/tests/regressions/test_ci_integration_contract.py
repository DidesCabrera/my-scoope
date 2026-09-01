from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[3]


class CiIntegrationContractTests(SimpleTestCase):
    def test_proposed_changes_run_from_staging_pushes_and_pull_requests(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()

        self.assertIn("  pull_request:", workflow)
        self.assertIn("      - staging", workflow)
        self.assertIn("      - main", workflow)

    def test_ci_checks_migration_drift_and_repository_hygiene(self):
        aggregate_script = (ROOT / "scripts/ci_django_checks.sh").read_text()
        fast_script = (ROOT / "scripts/ci_fast_checks.sh").read_text()

        self.assertIn("scripts/ci_fast_checks.sh", aggregate_script)
        self.assertIn("scripts/ci_django_full_suite.sh", aggregate_script)
        self.assertIn("scripts/check_repository_hygiene.sh", fast_script)
        self.assertIn("scripts/check_frontend_debt.py", fast_script)
        self.assertIn("scripts/check_backend_debt.py", fast_script)
        self.assertIn("scripts/check_e2e_contract.py", fast_script)
        self.assertIn("manage.py makemigrations --check --dry-run", fast_script)

    def test_ci_exposes_django_and_mcp_as_separate_quality_surfaces(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()

        self.assertIn("django-fast:", workflow)
        self.assertIn("django-full:", workflow)
        self.assertIn("django-postgres:", workflow)
        self.assertIn("mcp:", workflow)
        self.assertIn("browser-smoke:", workflow)
        self.assertIn("scripts/test_mcp.sh", workflow)

    def test_complete_django_gate_measures_coverage_and_mobile_audits_dependencies(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()
        coverage_script = (ROOT / "scripts/coverage_django.sh").read_text()
        mobile_script = (ROOT / "scripts/ci_mobile_checks.sh").read_text()
        configuration = (ROOT / "pyproject.toml").read_text()

        self.assertIn("scripts/coverage_django.sh", workflow)
        self.assertIn('"mobile_api"', configuration)
        self.assertIn("fail_under = 75", configuration)
        self.assertIn("MYSCOOPE_COVERAGE_MINIMUM", coverage_script)
        self.assertIn("scripts/check_dependency_audits.mjs", mobile_script)

    def test_postgres_gate_uses_a_real_postgres_service_and_full_suite(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()
        postgres_script = (ROOT / "scripts/ci_postgres_suite.sh").read_text()

        self.assertIn("image: postgres:17", workflow)
        self.assertIn("DATABASE_URL: postgresql://", workflow)
        self.assertIn("scripts/ci_postgres_suite.sh", workflow)
        self.assertIn("manage.py migrate --noinput", postgres_script)
        self.assertIn("manage.py test", postgres_script)

    def test_browser_gate_seeds_and_runs_the_authenticated_suite(self):
        workflow = (ROOT / ".github/workflows/django-ci.yml").read_text()

        self.assertIn("manage.py seed_e2e_fixtures", workflow)
        self.assertIn('--github-env-path "$GITHUB_ENV"', workflow)
        self.assertIn("scripts/test_e2e.sh", workflow)

    def test_quality_gate_includes_a_scoped_type_check(self):
        quality_script = (ROOT / "scripts/quality_checks.sh").read_text()
        configuration = (ROOT / "pyproject.toml").read_text()

        self.assertIn('"${PYTHON_BIN}" -m mypy', quality_script)
        self.assertIn("[tool.mypy]", configuration)
        self.assertIn('"core/environment_contract.py"', configuration)
        self.assertIn('"core/observability.py"', configuration)
