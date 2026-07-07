from .base import *
from .base import _env_bool, _env_csv

from accounts.email_verification import production_email_verification_default
from django.core.exceptions import ImproperlyConfigured


SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()
if not SECRET_KEY:
    raise ImproperlyConfigured("SECRET_KEY must be configured in production.")

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

SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "3600"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = _env_bool("SECURE_HSTS_PRELOAD", False)

ACCOUNT_EMAIL_VERIFICATION = os.environ.get(
    "ACCOUNT_EMAIL_VERIFICATION",
    production_email_verification_default(EMAIL_BACKEND, EMAIL_HOST),
).strip()
