from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[3]


class DeploymentContractTests(SimpleTestCase):
    def test_render_blueprint_versions_the_complete_runtime_topology(self):
        blueprint = (ROOT / "render.yaml").read_text()

        for resource in (
            "my-scoope-postgres",
            "my-scoope-cache",
            "my-scoope-notifications",
            "my-scoope-ai-jobs",
            "my-scoope-calendar-housekeeping",
        ):
            self.assertIn(f"name: {resource}", blueprint)
        self.assertIn("type: web", blueprint)
        self.assertIn("type: worker", blueprint)
        self.assertIn("type: cron", blueprint)
        self.assertIn("type: keyvalue", blueprint)
        self.assertIn("preDeployCommand: python manage.py migrate --noinput", blueprint)
        self.assertIn("healthCheckPath: /healthz/", blueprint)

    def test_render_blueprint_references_managed_data_services(self):
        blueprint = (ROOT / "render.yaml").read_text()

        self.assertIn("fromDatabase:", blueprint)
        self.assertIn("fromService:", blueprint)
        self.assertIn("property: connectionString", blueprint)
        self.assertNotIn("sqlite:///", blueprint)
        self.assertNotIn("postgresql://", blueprint)

    def test_render_build_keeps_schema_changes_out_of_the_build_step(self):
        build_script = (ROOT / "scripts/render_build.sh").read_text()

        self.assertIn("collectstatic --noinput", build_script)
        self.assertNotIn("manage.py migrate", build_script)
