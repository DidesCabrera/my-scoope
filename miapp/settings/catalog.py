import os

from django.core.exceptions import ImproperlyConfigured

from .prod import *

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "food_catalog.apps.FoodCatalogConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "miapp.catalog_urls"
LOGIN_URL = "/admin/login/"
LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"

TEMPLATES[0]["OPTIONS"]["context_processors"] = [
    "django.template.context_processors.debug",
    "django.template.context_processors.request",
    "django.contrib.auth.context_processors.auth",
    "django.contrib.messages.context_processors.messages",
]

FOOD_CATALOG_RELEASE_TOKEN = os.environ.get("FOOD_CATALOG_RELEASE_TOKEN", "").strip()
if not FOOD_CATALOG_RELEASE_TOKEN:
    raise ImproperlyConfigured(
        "FOOD_CATALOG_RELEASE_TOKEN must be configured for the catalog authority."
    )
