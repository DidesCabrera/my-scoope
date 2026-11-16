"""Migration checks for the separate authority and operational databases."""

import os
import subprocess
import sys
from pathlib import Path
from unittest import TestCase

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = """
import importlib
import django
from django.conf import settings

module = importlib.import_module(SETTINGS_MODULE)
config = {key: getattr(module, key) for key in dir(module) if key.isupper()}
config["DATABASES"] = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
settings.configure(**config)
django.setup()
"""


class IsolatedAuthorityMigrationTests(TestCase):
    def _run(self, settings_module, script):
        env = {
            **os.environ,
            "SECRET_KEY": "local-test-only",
            "DATABASE_URL": "postgresql://user:pass@localhost:5432/catalog",
            "FOOD_CATALOG_RELEASE_TOKEN": "local-test-token",
        }
        result = subprocess.run(
            [sys.executable, "-c", f"SETTINGS_MODULE = {settings_module!r}\n{BOOTSTRAP}\n{script}"],
            cwd=PROJECT_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_authority_can_migrate_without_operational_food(self):
        self._run(
            "miapp.settings.catalog",
            """
from django.apps import apps
from django.core.management import call_command
from django.db import connection

call_command("check", verbosity=0)
call_command("migrate", interactive=False, verbosity=0)
assert not apps.is_installed("notas")
assert "food_catalog_legacyfoodvisualasset" not in connection.introspection.table_names()
""",
        )

    def test_existing_operational_image_survives_model_ownership_transfer(self):
        self._run(
            "miapp.settings.dev",
            """
import uuid
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

old_target = [("food_catalog", "0022_catalogfood_description"), ("notas", "0101_food_description")]
executor = MigrationExecutor(connection)
executor.migrate(old_target)
old_apps = executor.loader.project_state(old_target).apps
food = old_apps.get_model("notas", "Food").objects.create(
    name="Legacy visual migration test", protein=1, carbs=2, fat=3, is_global=True
)
public_ref = uuid.uuid4()
image = old_apps.get_model("food_catalog", "LegacyFoodVisualAsset").objects.create(
    food_id=food.pk, public_ref=public_ref, image_data=b"original", mobile_image_data=b"mobile",
    content_sha256="a" * 64, is_published=True, source_note="Migration test"
)

new_target = [
    ("food_catalog", "0024_transfer_operational_visual_assets"),
    ("notas", "0104_operational_food_visual_assets"),
]
executor = MigrationExecutor(connection)
executor.migrate(new_target)
new_apps = executor.loader.project_state(new_target).apps
asset = new_apps.get_model("notas", "LegacyFoodVisualAsset").objects.get(pk=image.pk)
assert asset.food_id == food.pk
assert asset.public_ref == public_ref
assert bytes(asset.image_data) == b"original"
assert bytes(asset.mobile_image_data) == b"mobile"
assert asset.is_published
assert "food_catalog_legacyfoodvisualasset" in connection.introspection.table_names()
""",
        )
