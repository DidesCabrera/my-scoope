from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[3]


class DeploymentContractTests(SimpleTestCase):
    def test_catalog_authority_has_one_web_service_and_one_database(self):
        blueprint = (ROOT / "render.catalog.yaml").read_text()

        self.assertIn("name: myscoope-food-catalog-db", blueprint)
        self.assertIn("name: myscoope-food-catalog", blueprint)
        self.assertEqual(blueprint.count("type: web"), 1)
        self.assertNotIn("type: worker", blueprint)
        self.assertIn("DJANGO_SETTINGS_MODULE", blueprint)
        self.assertIn("miapp.settings.catalog", blueprint)
        self.assertIn("FOOD_CATALOG_RELEASE_TOKEN", blueprint)
        self.assertIn("- key: SECRET_KEY\n        sync: false", blueprint)
        self.assertIn("preDeployCommand: python manage.py migrate --noinput", blueprint)

    def test_render_blueprint_versions_the_complete_runtime_topology(self):
        blueprint = (ROOT / "render.yaml").read_text()

        for resource in (
            "nutricion-db",
            "myscoope-cache",
            "my-scoope-notifications",
            "my-scoope-ai-jobs",
            "my-scoope-calendar-housekeeping",
        ):
            self.assertIn(f"name: {resource}", blueprint)
        self.assertIn("type: web", blueprint)
        self.assertIn("type: worker", blueprint)
        self.assertIn("type: cron", blueprint)
        self.assertIn("type: keyvalue", blueprint)
        self.assertIn("preDeployCommand: bash scripts/render_production_predeploy.sh", blueprint)
        self.assertIn("healthCheckPath: /healthz/", blueprint)

        predeploy = (ROOT / "scripts/render_production_predeploy.sh").read_text()
        self.assertIn("python manage.py migrate --noinput", predeploy)
        self.assertIn("python manage.py seed_billing_catalog", predeploy)
        self.assertIn("--environment \"${catalog_environment}\"", predeploy)

    def test_render_blueprint_references_managed_data_services(self):
        blueprint = (ROOT / "render.yaml").read_text()

        self.assertIn("fromDatabase:", blueprint)
        self.assertIn("fromService:", blueprint)
        self.assertIn("property: connectionString", blueprint)
        self.assertNotIn("sqlite:///", blueprint)
        self.assertNotIn("postgresql://", blueprint)

    def test_staging_blueprint_versions_dual_environment_apple_contract(self):
        blueprint = (ROOT / "render.staging.yaml").read_text()

        self.assertIn("- key: BILLING_APPLE_ENVIRONMENT\n        value: production", blueprint)
        self.assertIn("- key: BILLING_APPLE_BUNDLE_ID\n        value: com.myscoope.app", blueprint)
        self.assertIn("- key: BILLING_APPLE_APP_ID\n        value: \"6804048394\"", blueprint)
        self.assertIn("- key: BILLING_APPLE_ONLINE_CHECKS\n        value: \"true\"", blueprint)
        for setting in (
            "BILLING_APPLE_NOTIFICATIONS_ENABLED",
            "BILLING_APPLE_PURCHASES_ENABLED",
            "BILLING_APPLE_SANDBOX_NOTIFICATIONS_ENABLED",
            "BILLING_APPLE_SANDBOX_PURCHASES_ENABLED",
        ):
            self.assertIn(f"- key: {setting}\n        value: \"false\"", blueprint)
        for credential in (
            "BILLING_APPLE_IN_APP_PURCHASE_KEY",
            "BILLING_APPLE_KEY_ID",
            "BILLING_APPLE_ISSUER_ID",
        ):
            self.assertIn(f"- key: {credential}\n        sync: false", blueprint)

    def test_blueprints_version_google_play_environment_and_rtdn_contract(self):
        staging = (ROOT / "render.staging.yaml").read_text()
        production = (ROOT / "render.yaml").read_text()

        self.assertIn("- key: BILLING_GOOGLE_PLAY_ENVIRONMENT\n        value: sandbox", staging)
        self.assertIn("- key: BILLING_GOOGLE_PLAY_RTDN_ENABLED\n        value: \"false\"", staging)
        self.assertIn(
            "- key: BILLING_GOOGLE_PLAY_PUBSUB_AUDIENCE\n"
            "        value: https://myscoope-staging.onrender.com/billing/webhooks/google-play/",
            staging,
        )
        self.assertIn("- key: BILLING_GOOGLE_PLAY_ENVIRONMENT\n        value: live", production)
        self.assertIn("- key: BILLING_GOOGLE_PLAY_RTDN_ENABLED\n        value: \"false\"", production)
        self.assertIn(
            "- key: BILLING_GOOGLE_PLAY_PUBSUB_AUDIENCE\n"
            "        value: https://www.myscoope.com/billing/webhooks/google-play/",
            production,
        )
        for blueprint in (staging, production):
            self.assertIn(
                "- key: BILLING_GOOGLE_PLAY_PUBSUB_SERVICE_ACCOUNT_EMAIL\n        sync: false",
                blueprint,
            )

    def test_render_build_keeps_schema_changes_out_of_the_build_step(self):
        build_script = (ROOT / "scripts/render_build.sh").read_text()

        self.assertIn("collectstatic --noinput", build_script)
        self.assertNotIn("manage.py migrate", build_script)

    def test_all_django_processes_share_one_generated_secret_key(self):
        blueprint = (ROOT / "render.yaml").read_text()

        self.assertEqual(blueprint.count("key: SECRET_KEY"), 1)
        self.assertEqual(blueprint.count("generateValue: true"), 1)
        self.assertEqual(blueprint.count("fromGroup: myscoope-django-runtime"), 4)
