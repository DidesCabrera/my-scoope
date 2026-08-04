import dj_database_url
from django.core.exceptions import ImproperlyConfigured

from accounts.email_verification import production_email_verification_default

from .base import *
from .base import _env_bool, _env_csv, _env_int

SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be configured in production.")

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise ImproperlyConfigured("DATABASE_URL must be configured in production.")

try:
    PRODUCTION_DATABASE = dj_database_url.parse(
        DATABASE_URL,
        conn_max_age=60,
        conn_health_checks=True,
    )
except (TypeError, ValueError) as exc:
    raise ImproperlyConfigured("DATABASE_URL is invalid in production.") from exc

if PRODUCTION_DATABASE.get("ENGINE") != "django.db.backends.postgresql":
    raise ImproperlyConfigured("DATABASE_URL must use PostgreSQL in production.")

DATABASES = {"default": PRODUCTION_DATABASE}

DEBUG = False

ALLOWED_HOSTS = _env_csv(
    "ALLOWED_HOSTS",
    ("www.myscoope.com", "myscoope.com", "my-scoope.onrender.com"),
)

CSRF_TRUSTED_ORIGINS = _env_csv(
    "CSRF_TRUSTED_ORIGINS",
    [f"https://{host}" for host in ALLOWED_HOSTS if host and not host.startswith(".")],
)

SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE", True)
CSRF_COOKIE_SECURE = _env_bool("CSRF_COOKIE_SECURE", True)
SECURE_SSL_REDIRECT = _env_bool("SECURE_SSL_REDIRECT", True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SECURE_HSTS_SECONDS = _env_int("SECURE_HSTS_SECONDS", 31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", True)
SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", True)

AI_ASSISTANT_ASYNC_ENABLED = _env_bool("AI_ASSISTANT_ASYNC_ENABLED", True)

ACCOUNT_EMAIL_VERIFICATION = os.environ.get(
    "ACCOUNT_EMAIL_VERIFICATION",
    production_email_verification_default(EMAIL_BACKEND, EMAIL_HOST),
).strip()
