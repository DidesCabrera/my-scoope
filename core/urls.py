from django.urls import path

from .views import (
    android_asset_links,
    apple_app_site_association,
    healthz,
    landing,
    msos,
    msos_detail,
    privacy,
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
    path("msos/", msos, name="msos"),
    path("msos/<slug:kind>/<slug:item_id>/", msos_detail, name="msos_detail"),
    path("", landing, name="landing"),
    path("privacy/", privacy, name="privacy"),
    path("terms/", terms, name="terms"),
    path("support/", support, name="support"),
]
