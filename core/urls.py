from django.urls import path

from .views import (
    android_asset_links,
    apple_app_site_association,
    healthz,
    landing,
    mcp_integration,
    meal_app_link,
    privacy,
    refund_policy,
    support,
    terms,
)

urlpatterns = [
    path(
        ".well-known/apple-app-site-association",
        apple_app_site_association,
        name="apple_app_site_association",
    ),
    path(".well-known/assetlinks.json", android_asset_links, name="android_asset_links"),
    path("healthz/", healthz, name="healthz"),
    path("libraries/meals/<int:meal_id>", meal_app_link, name="meal_app_link"),
    path("", landing, name="landing"),
    path("privacy/", privacy, name="privacy"),
    path("refund-policy/", refund_policy, name="refund_policy"),
    path("terms/", terms, name="terms"),
    path("support/", support, name="support"),
    path("integrations/mcp/", mcp_integration, name="mcp_integration"),
]
