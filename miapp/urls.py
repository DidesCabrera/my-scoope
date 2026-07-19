from django.contrib import admin
from django.urls import include, path
from allauth.account import views as allauth_account_views

from core.rate_limits import limit_login, limit_signup
from notas.interface.views.oauth import (
    oauth_authorization_server_metadata,
    oauth_authorize,
    oauth_authorize_consent,
    oauth_token,
)


urlpatterns = [
    path("admin/", admin.site.urls),

    # OAuth / MCP app auth
    path(
        ".well-known/oauth-authorization-server",
        oauth_authorization_server_metadata,
        name="oauth_authorization_server_metadata",
    ),
    path(
        "oauth/authorize",
        oauth_authorize,
        name="oauth_authorize",
    ),
    path(
        "oauth/authorize/consent",
        oauth_authorize_consent,
        name="oauth_authorize_consent",
    ),
    path(
        "oauth/token",
        oauth_token,
        name="oauth_token",
    ),

    # Landing pública
    path("", include("core.urls")),

    # Auth system
    path("accounts/", include("accounts.urls")),
    path(
        "accounts/login/",
        limit_login(allauth_account_views.login),
        name="account_login",
    ),
    path(
        "accounts/signup/",
        limit_signup(allauth_account_views.signup),
        name="account_signup",
    ),
    path("accounts/", include("allauth.urls")),

    # External billing callbacks (provider-authenticated, disabled by default)
    path("billing/", include("billing.interface.urls")),

    # Internal product intelligence
    path("staff/analytics/", include("admin_analytics.urls")),

    # Internal product operations
    path("staff/operations/", include("admin_operations.urls")),

    # Main app
    path("app/", include("notas.urls")),
]
