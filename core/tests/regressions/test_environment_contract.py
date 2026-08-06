import ast
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase

from core.environment_contract import ENVIRONMENT_VARIABLE_SPEC_BY_NAME
from miapp.settings.base import _env_float, _env_int

ROOT = Path(__file__).resolve().parents[3]


class EnvironmentContractTests(SimpleTestCase):
    def _load_production_settings(self, **overrides):
        env = os.environ.copy()
        for name in ("DATABASE_URL", "SECRET_KEY", "SENTRY_DSN"):
            env.pop(name, None)
        env.update(
            {
                "DJANGO_SETTINGS_MODULE": "miapp.settings.prod",
                "SECRET_KEY": "test-production-secret",
                "SENTRY_DSN": "",
                **overrides,
            }
        )
        script = """
import json
from django.conf import settings

print(json.dumps({
    "engine": settings.DATABASES["default"]["ENGINE"],
    "language_code": settings.LANGUAGE_CODE,
    "time_zone": settings.TIME_ZONE,
    "hsts_seconds": settings.SECURE_HSTS_SECONDS,
    "hsts_subdomains": settings.SECURE_HSTS_INCLUDE_SUBDOMAINS,
    "hsts_preload": settings.SECURE_HSTS_PRELOAD,
    "traces_sample_rate": settings.SENTRY_TRACES_SAMPLE_RATE,
    "ai_async_enabled": settings.AI_ASSISTANT_ASYNC_ENABLED,
}))
"""
        return subprocess.run(
            [sys.executable, "-c", script],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_all_environment_names_declared_by_settings_are_classified(self):
        declared_names = set()
        helper_names = {"_env_bool", "_env_csv", "_env_float", "_env_int"}
        for settings_path in (ROOT / "miapp/settings").glob("*.py"):
            tree = ast.parse(settings_path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not node.args:
                    continue
                first_arg = node.args[0]
                if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
                    continue
                function = node.func
                is_helper = isinstance(function, ast.Name) and function.id in helper_names
                is_environ_get = (
                    isinstance(function, ast.Attribute)
                    and function.attr == "get"
                    and isinstance(function.value, ast.Attribute)
                    and function.value.attr == "environ"
                    and isinstance(function.value.value, ast.Name)
                    and function.value.value.id == "os"
                )
                if is_helper or is_environ_get:
                    declared_names.add(first_arg.value)

        self.assertEqual(declared_names - ENVIRONMENT_VARIABLE_SPEC_BY_NAME.keys(), set())

    def test_public_example_exists_and_contains_no_secret_values(self):
        example = (ROOT / ".env.example").read_text()

        self.assertIn("DJANGO_SETTINGS_MODULE=miapp.settings.dev", example)
        for secret_name in (
            "SECRET_KEY", "DATABASE_URL", "EMAIL_HOST_PASSWORD", "SENTRY_DSN",
            "AI_ASSISTANT_OPENAI_API_KEY", "FOOD_CATALOG_FATSECRET_CLIENT_SECRET",
            "BILLING_MERCADOPAGO_ACCESS_TOKEN", "BILLING_MERCADOPAGO_WEBHOOK_SECRET",
            "BILLING_APPLE_IN_APP_PURCHASE_KEY",
            "MYSCOOPE_APNS_PRIVATE_KEY",
            "BILLING_OPENFACTURA_API_KEY",
            "TURNSTILE_SECRET_KEY", "CACHE_URL",
        ):
            self.assertIn(f"{secret_name}=\n", example)

    def test_critical_environment_values_are_classified(self):
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["SECRET_KEY"].secret)
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["SECRET_KEY"].required_in_production)
        self.assertEqual(
            ENVIRONMENT_VARIABLE_SPEC_BY_NAME["AI_ASSISTANT_MAX_INPUT_TOKENS"].value_type,
            "integer",
        )
        self.assertEqual(
            ENVIRONMENT_VARIABLE_SPEC_BY_NAME["MYSCOOPE_WEB_PUSH_ENABLED"].value_type,
            "boolean",
        )
        self.assertTrue(
            ENVIRONMENT_VARIABLE_SPEC_BY_NAME["MYSCOOPE_VAPID_PRIVATE_KEY"].secret,
        )
        self.assertTrue(
            ENVIRONMENT_VARIABLE_SPEC_BY_NAME["MYSCOOPE_APNS_PRIVATE_KEY"].secret,
        )
        self.assertFalse(
            ENVIRONMENT_VARIABLE_SPEC_BY_NAME["MYSCOOPE_VAPID_PUBLIC_KEY"].secret,
        )
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["BILLING_MERCADOPAGO_ACCESS_TOKEN"].secret)
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["BILLING_APPLE_IN_APP_PURCHASE_KEY"].secret)
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["BILLING_OPENFACTURA_API_KEY"].secret)
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["TURNSTILE_SECRET_KEY"].secret)
        self.assertTrue(ENVIRONMENT_VARIABLE_SPEC_BY_NAME["CACHE_URL"].secret)

    def test_invalid_numeric_configuration_fails_with_variable_name(self):
        with patch.dict(os.environ, {"PCF_TEST_INT": "not-a-number"}):
            with self.assertRaisesMessage(ImproperlyConfigured, "PCF_TEST_INT"):
                _env_int("PCF_TEST_INT", 1)
        with patch.dict(os.environ, {"PCF_TEST_FLOAT": "not-a-number"}):
            with self.assertRaisesMessage(ImproperlyConfigured, "PCF_TEST_FLOAT"):
                _env_float("PCF_TEST_FLOAT", 1.0)

    def test_wsgi_and_asgi_use_the_same_production_default(self):
        wsgi = (ROOT / "miapp/wsgi.py").read_text()
        asgi = (ROOT / "miapp/asgi.py").read_text()

        self.assertIn("miapp.settings.prod", wsgi)
        self.assertIn("miapp.settings.prod", asgi)

    def test_production_settings_fail_closed_without_database_url(self):
        result = self._load_production_settings()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL must be configured in production", result.stderr)

    def test_production_settings_reject_non_postgresql_database_url(self):
        result = self._load_production_settings(DATABASE_URL="sqlite:////tmp/unsafe-production.sqlite3")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DATABASE_URL must use PostgreSQL in production", result.stderr)

    def test_production_settings_use_launch_defaults_with_postgresql(self):
        result = self._load_production_settings(
            DATABASE_URL="postgresql://myscoope:password@localhost:5432/myscoope",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["engine"], "django.db.backends.postgresql")
        self.assertEqual(payload["language_code"], "es-cl")
        self.assertEqual(payload["time_zone"], "America/Santiago")
        self.assertEqual(payload["hsts_seconds"], 31_536_000)
        self.assertTrue(payload["hsts_subdomains"])
        self.assertTrue(payload["hsts_preload"])
        self.assertEqual(payload["traces_sample_rate"], 0.05)
        self.assertTrue(payload["ai_async_enabled"])
