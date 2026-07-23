"""Focused settings used to validate the ``ai_behavior`` export workspace.

This module is never selected by production. It keeps real domain models and
services while removing unrelated dashboards, global middleware and URL wiring
from the export smoke boundary.
"""

from .dev import *  # noqa: F403

INSTALLED_APPS = [  # noqa: F405
    app
    for app in INSTALLED_APPS
    if app not in {
        "django.contrib.admin",
        "admin_analytics.apps.AdminAnalyticsConfig",
        "admin_operations.apps.AdminOperationsConfig",
        "admin_knowledge.apps.AdminKnowledgeConfig",
    }
]

MIDDLEWARE = [  # noqa: F405
    middleware
    for middleware in MIDDLEWARE
    if middleware != "accounts.middleware.NutritionOnboardingRequiredMiddleware"
]

ROOT_URLCONF = "miapp.urls_export_ai_behavior"
NUTRITION_ONBOARDING_GATE_ENABLED = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
