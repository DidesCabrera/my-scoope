import json
import os
from pathlib import Path
import dj_database_url

from core.observability import configure_sentry

BASE_DIR = Path(__file__).resolve().parent.parent.parent

def _env_csv(name: str, default: list[str] | tuple[str, ...] | None = None) -> list[str]:
    raw_value = os.environ.get(name, "")
    if raw_value.strip():
        return [item.strip() for item in raw_value.split(",") if item.strip()]
    return list(default or [])


def _env_float(name: str, default: float = 0.0) -> float:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _env_int(name: str, default: int = 0) -> int:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


SECRET_KEY = os.environ.get("SECRET_KEY", "")

DEBUG = False

ALLOWED_HOSTS = _env_csv("ALLOWED_HOSTS")



# ==============================
# APPLICATIONS
# ==============================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    "food_catalog.apps.FoodCatalogConfig",
    "ai_assistant.apps.AiAssistantConfig",
    "nutrition_solver.apps.NutritionSolverConfig",
    "admin_analytics.apps.AdminAnalyticsConfig",
    "admin_operations.apps.AdminOperationsConfig",
    "notas.apps.NotasConfig",
    "accounts",
    "core",

    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
]


# ==============================
# MIDDLEWARE
# ==============================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "accounts.middleware.NutritionOnboardingRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==============================
# URLS
# ==============================

ROOT_URLCONF = "miapp.urls"


# ==============================
# TEMPLATES
# ==============================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notas.context_processors.user_weight",
            ],
        },
    },
]


WSGI_APPLICATION = "miapp.wsgi.application"


# ==============================
# DATABASE
# ==============================

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}


# ==============================
# PASSWORD VALIDATION
# ==============================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# ==============================
# INTERNATIONALIZATION
# ==============================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# ==============================
# STATIC FILES
# ==============================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"


# ==============================
# DEFAULT PK
# ==============================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================
# AUTH
# ==============================

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/app/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# ==============================
# ONBOARDING
# ==============================

NUTRITION_ONBOARDING_GATE_ENABLED = os.environ.get(
    "NUTRITION_ONBOARDING_GATE_ENABLED",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}

NUTRITION_ONBOARDING_ALLOWED_PREFIXES = (
    "/accounts/",
    "/admin/",
    "/staff/",
    "/static/",
    "/media/",
    "/favicon.ico",
    "/manifest.json",
    "/serviceworker.js",
    "/.well-known/",
    "/oauth/",
)


# ==============================
# NUTRITION SOLVER OPTIMIZATION
# ==============================

NUTRITION_SOLVER_BACKEND = os.environ.get(
    "NUTRITION_SOLVER_BACKEND",
    "heuristic_v2",
).strip().lower()
NUTRITION_SOLVER_SHADOW_ENABLED = os.environ.get(
    "NUTRITION_SOLVER_SHADOW_ENABLED",
    "false",
).strip().lower() in {"1", "true", "yes", "on"}
NUTRITION_SOLVER_SHADOW_BACKEND = os.environ.get(
    "NUTRITION_SOLVER_SHADOW_BACKEND",
    "cp_sat_v1",
).strip().lower()
NUTRITION_SOLVER_TIME_LIMIT_MS = max(
    50,
    min(_env_int("NUTRITION_SOLVER_TIME_LIMIT_MS", 1500), 10_000),
)


# ==============================
# AI ASSISTANT / EXTERNAL LLM
# ==============================

AI_ASSISTANT_CHAT_ENGINE_MODE = os.environ.get("AI_ASSISTANT_CHAT_ENGINE_MODE", "deterministic").strip()
AI_ASSISTANT_LLM_PROVIDER = os.environ.get("AI_ASSISTANT_LLM_PROVIDER", "fake").strip()
AI_ASSISTANT_OPENAI_API_KEY = os.environ.get("AI_ASSISTANT_OPENAI_API_KEY", "").strip()
AI_ASSISTANT_OPENAI_MODEL = os.environ.get("AI_ASSISTANT_OPENAI_MODEL", "gpt-5.4-mini").strip()
AI_ASSISTANT_OPENAI_BASE_URL = os.environ.get(
    "AI_ASSISTANT_OPENAI_BASE_URL",
    "https://api.openai.com/v1",
).strip()
AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS = int(
    os.environ.get("AI_ASSISTANT_OPENAI_TIMEOUT_SECONDS", "30")
)
AI_ASSISTANT_OPENAI_REASONING_EFFORT = os.environ.get(
    "AI_ASSISTANT_OPENAI_REASONING_EFFORT",
    "low",
).strip().lower()
AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED = os.environ.get(
    "AI_ASSISTANT_USAGE_OBSERVABILITY_ENABLED",
    "true",
).strip().lower() in {"1", "true", "yes", "on"}
AI_ASSISTANT_LLM_DEFAULT_PRICING_USD_PER_1M_TOKENS = {
    "openai": {
        "gpt-5.4-mini": {"input": "0.75", "cached_input": "0.075", "output": "4.50"},
        "gpt-5.4-nano": {"input": "0.20", "cached_input": "0.02", "output": "1.25"},
        "gpt-5.4": {"input": "2.50", "cached_input": "0.25", "output": "15.00"},
        "gpt-5.5": {"input": "5.00", "cached_input": "0.50", "output": "30.00"},
        "default": {"input": "0.75", "cached_input": "0.075", "output": "4.50"},
    },
}


def _llm_pricing_from_env():
    raw_value = os.environ.get("AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS_JSON", "").strip()
    if not raw_value:
        return AI_ASSISTANT_LLM_DEFAULT_PRICING_USD_PER_1M_TOKENS
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        return AI_ASSISTANT_LLM_DEFAULT_PRICING_USD_PER_1M_TOKENS
    return parsed if isinstance(parsed, dict) else AI_ASSISTANT_LLM_DEFAULT_PRICING_USD_PER_1M_TOKENS


AI_ASSISTANT_LLM_PRICING_USD_PER_1M_TOKENS = _llm_pricing_from_env()

# Technical per-turn guardrails for the external LLM cycle. These are not
# commercial credits; they prevent accidental runaway context while real usage
# data is collected.
AI_ASSISTANT_MAX_HISTORY_MESSAGES = int(os.environ.get("AI_ASSISTANT_MAX_HISTORY_MESSAGES", "8"))
AI_ASSISTANT_MAX_OUTPUT_TOKENS = int(os.environ.get("AI_ASSISTANT_MAX_OUTPUT_TOKENS", "900"))
AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS = int(os.environ.get("AI_ASSISTANT_MAX_TOOL_LOOP_ITERATIONS", "1"))
AI_ASSISTANT_MAX_INPUT_TOKENS = int(os.environ.get("AI_ASSISTANT_MAX_INPUT_TOKENS", "6000"))
AI_ASSISTANT_MAX_CONTEXT_CHARS = int(os.environ.get("AI_ASSISTANT_MAX_CONTEXT_CHARS", "8000"))
AI_ASSISTANT_MAX_MESSAGE_CHARS = int(os.environ.get("AI_ASSISTANT_MAX_MESSAGE_CHARS", "2000"))
AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN = int(os.environ.get("AI_ASSISTANT_MAX_TOOL_REQUESTS_PER_TURN", "3"))
AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS = os.environ.get(
    "AI_ASSISTANT_ENABLE_REVIEWABLE_PROPOSAL_TOOLS",
    "false",
).lower() in {"1", "true", "yes", "on"}

# Patch 59: AI credits are the commercial usage unit. Disabled by default so
# staging can keep measuring real usage before enforcing membership quotas.
AI_ASSISTANT_CREDITS_ENABLED = os.environ.get(
    "AI_ASSISTANT_CREDITS_ENABLED",
    "false",
).lower() in {"1", "true", "yes", "on"}
AI_ASSISTANT_USD_PER_AI_CREDIT = os.environ.get("AI_ASSISTANT_USD_PER_AI_CREDIT", "0.001")
AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN = int(os.environ.get("AI_ASSISTANT_DEFAULT_CREDITS_PER_TURN", "1"))
AI_ASSISTANT_CREDIT_PLANS = {
    "free": {
        "monthly_credit_limit": 25,
        "daily_credit_limit": 5,
        "block_on_exhaustion": True,
    },
    "basic": {
        "monthly_credit_limit": 150,
        "daily_credit_limit": 30,
        "block_on_exhaustion": True,
    },
    "pro": {
        "monthly_credit_limit": 1000,
        "daily_credit_limit": 150,
        "block_on_exhaustion": True,
    },
}
AI_ASSISTANT_CREDIT_PLAN_ALIASES = {
    "default": "free",
    "member": "basic",
    "nutritionist": "pro",
}
AI_ASSISTANT_ACTION_CREDIT_MULTIPLIERS = {}

# Patch 61: optional cost optimization route table. Keep only a default route
# out of the box so behavior remains unchanged until production config chooses
# cheaper/stronger models per action_type. Example action-specific routes can be
# added in deployment settings without exposing tokens to end users.
AI_ASSISTANT_LLM_MODEL_ROUTES = {
    "default": {
        "provider": AI_ASSISTANT_LLM_PROVIDER,
        "model": AI_ASSISTANT_OPENAI_MODEL if AI_ASSISTANT_LLM_PROVIDER == "openai" else "",
        "max_output_tokens": AI_ASSISTANT_MAX_OUTPUT_TOKENS,
        "reason": "default_external_llm_route",
    },
}

# Patch 62: production rollout gate. LLM production mode requires both
# AI_ASSISTANT_CHAT_ENGINE_MODE=llm_production and this rollout flag enabled.
# This keeps rollback to deterministic explicit and immediate.
AI_ASSISTANT_LLM_ROLLOUT_ENABLED = os.environ.get(
    "AI_ASSISTANT_LLM_ROLLOUT_ENABLED",
    "false",
).lower() in {"1", "true", "yes", "on"}
AI_ASSISTANT_LLM_ROLLOUT_MODE = os.environ.get("AI_ASSISTANT_LLM_ROLLOUT_MODE", "off")
AI_ASSISTANT_LLM_ROLLOUT_USER_IDS = os.environ.get("AI_ASSISTANT_LLM_ROLLOUT_USER_IDS", "")
AI_ASSISTANT_LLM_ROLLOUT_PERCENT = int(os.environ.get("AI_ASSISTANT_LLM_ROLLOUT_PERCENT", "0"))
AI_ASSISTANT_LLM_ROLLOUT_STICKY_SALT = os.environ.get(
    "AI_ASSISTANT_LLM_ROLLOUT_STICKY_SALT",
    "ai-assistant-rollout-v1",
)


# ==============================
# RATE LIMITING
# ==============================

RATE_LIMIT_LOGIN = os.environ.get("RATE_LIMIT_LOGIN", "10/m").strip()
RATE_LIMIT_SIGNUP = os.environ.get("RATE_LIMIT_SIGNUP", "5/m").strip()
RATE_LIMIT_AI_ASSISTANT_TURN_USER = os.environ.get(
    "RATE_LIMIT_AI_ASSISTANT_TURN_USER",
    "20/h",
).strip()
RATE_LIMIT_AI_ASSISTANT_TURN_IP = os.environ.get(
    "RATE_LIMIT_AI_ASSISTANT_TURN_IP",
    "5/h",
).strip()


# ==============================
# EMAIL
# ==============================

def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


EMAIL_HOST = os.environ.get("EMAIL_HOST", "").strip()
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND") or (
    "django.core.mail.backends.smtp.EmailBackend"
    if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")

# Resend SMTP on port 465 uses SSL. If SSL is enabled, TLS must stay off.
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", False)
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", bool(EMAIL_HOST) and not EMAIL_USE_SSL) and not EMAIL_USE_SSL
EMAIL_TIMEOUT = int(os.environ.get("EMAIL_TIMEOUT", "10"))

# Web Push is opt-in. Keep the dispatcher inert until all VAPID values are set.
MYSCOOPE_WEB_PUSH_ENABLED = _env_bool("MYSCOOPE_WEB_PUSH_ENABLED", False)
MYSCOOPE_VAPID_PUBLIC_KEY = os.environ.get("MYSCOOPE_VAPID_PUBLIC_KEY", "").strip()
MYSCOOPE_VAPID_PRIVATE_KEY = os.environ.get("MYSCOOPE_VAPID_PRIVATE_KEY", "").strip()
MYSCOOPE_VAPID_SUBJECT = os.environ.get(
    "MYSCOOPE_VAPID_SUBJECT",
    "mailto:notifications@myscoope.com",
).strip()
MYSCOOPE_PWA_CACHE_VERSION = os.environ.get("MYSCOOPE_PWA_CACHE_VERSION", "v2")

DEFAULT_FROM_EMAIL = os.environ.get(
    "DEFAULT_FROM_EMAIL",
    "My Scoope <no-reply@myscoope.com>",
)
SERVER_EMAIL = os.environ.get("SERVER_EMAIL", DEFAULT_FROM_EMAIL)


# ==============================
# ERROR OBSERVABILITY
# ==============================

_DEFAULT_SENTRY_ENVIRONMENT = (
    "development"
    if os.environ.get("DJANGO_SETTINGS_MODULE", "").endswith(".dev")
    else "production"
)

SENTRY_DSN = os.environ.get("SENTRY_DSN", "").strip()
SENTRY_ENVIRONMENT = os.environ.get(
    "SENTRY_ENVIRONMENT",
    os.environ.get("RENDER_SERVICE_NAME", _DEFAULT_SENTRY_ENVIRONMENT),
).strip()
SENTRY_RELEASE = os.environ.get(
    "SENTRY_RELEASE",
    os.environ.get("RENDER_GIT_COMMIT", ""),
).strip()
SENTRY_TRACES_SAMPLE_RATE = _env_float("SENTRY_TRACES_SAMPLE_RATE", 0.0)
SENTRY_PROFILES_SAMPLE_RATE = _env_float("SENTRY_PROFILES_SAMPLE_RATE", 0.0)
SENTRY_ENABLED = configure_sentry(
    dsn=SENTRY_DSN,
    environment=SENTRY_ENVIRONMENT,
    release=SENTRY_RELEASE,
    traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
    profiles_sample_rate=SENTRY_PROFILES_SAMPLE_RATE,
)


# ==============================
# FOOD CATALOG / EXTERNAL PROVIDERS
# ==============================

FOOD_CATALOG_FATSECRET_ENABLED = _env_bool("FOOD_CATALOG_FATSECRET_ENABLED", False)
FOOD_CATALOG_FATSECRET_CLIENT_ID = os.environ.get("FOOD_CATALOG_FATSECRET_CLIENT_ID", "").strip()
FOOD_CATALOG_FATSECRET_CLIENT_SECRET = os.environ.get("FOOD_CATALOG_FATSECRET_CLIENT_SECRET", "").strip()
FOOD_CATALOG_FATSECRET_TOKEN_URL = os.environ.get(
    "FOOD_CATALOG_FATSECRET_TOKEN_URL",
    "https://oauth.fatsecret.com/connect/token",
).strip()
FOOD_CATALOG_FATSECRET_API_BASE_URL = os.environ.get(
    "FOOD_CATALOG_FATSECRET_API_BASE_URL",
    "https://platform.fatsecret.com/rest/server.api",
).strip()
FOOD_CATALOG_FATSECRET_OAUTH_SCOPE = os.environ.get(
    "FOOD_CATALOG_FATSECRET_OAUTH_SCOPE",
    "basic",
).strip()
FOOD_CATALOG_FATSECRET_SEARCH_METHOD = os.environ.get(
    "FOOD_CATALOG_FATSECRET_SEARCH_METHOD",
    "foods.search",
).strip()
FOOD_CATALOG_FATSECRET_FOOD_GET_METHOD = os.environ.get(
    "FOOD_CATALOG_FATSECRET_FOOD_GET_METHOD",
    "food.get",
).strip()
FOOD_CATALOG_FATSECRET_TIMEOUT_SECONDS = int(
    os.environ.get("FOOD_CATALOG_FATSECRET_TIMEOUT_SECONDS", "15")
)

FOOD_CATALOG_OPEN_FOOD_FACTS_ENABLED = _env_bool("FOOD_CATALOG_OPEN_FOOD_FACTS_ENABLED", False)
FOOD_CATALOG_OPEN_FOOD_FACTS_API_BASE_URL = os.environ.get(
    "FOOD_CATALOG_OPEN_FOOD_FACTS_API_BASE_URL",
    "https://world.openfoodfacts.org",
).strip()
FOOD_CATALOG_OPEN_FOOD_FACTS_TIMEOUT_SECONDS = int(
    os.environ.get("FOOD_CATALOG_OPEN_FOOD_FACTS_TIMEOUT_SECONDS", "15")
)
FOOD_CATALOG_OPEN_FOOD_FACTS_USER_AGENT = os.environ.get(
    "FOOD_CATALOG_OPEN_FOOD_FACTS_USER_AGENT",
    "MyScoope FoodCatalog/1.0 (contact: support@myscoope.com)",
).strip()


# ==============================
# SITES
# ==============================

SITE_ID = 1


# ==============================
# AUTHENTICATION BACKENDS
# ==============================

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


# ==============================
# ALLAUTH SETTINGS (MODERN)
# ==============================

ACCOUNT_LOGIN_METHODS = {"email"}

ACCOUNT_SIGNUP_FIELDS = [
    "email*",
    "password1*",
    "password2*",
]

ACCOUNT_EMAIL_VERIFICATION = os.environ.get("ACCOUNT_EMAIL_VERIFICATION", "none").strip()
ACCOUNT_UNIQUE_EMAIL = True

ACCOUNT_LOGOUT_REDIRECT_URL = "/accounts/login/"

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_ADAPTER = "accounts.adapters.MyScoopeSocialAccountAdapter"
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        # Google returns verified email ownership. This lets social login reuse
        # an existing local account without showing the intermediate signup form.
        "VERIFIED_EMAIL": True,
        "EMAIL_AUTHENTICATION": True,
        "EMAIL_AUTHENTICATION_AUTO_CONNECT": True,
    },
}
