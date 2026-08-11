from django.urls import path

from .views import (
    healthz,
    landing,
    msos,
    privacy,
    support,
    terms,
)

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("msos/", msos, name="msos"),
    path("", landing, name="landing"),
    path("privacy/", privacy, name="privacy"),
    path("terms/", terms, name="terms"),
    path("support/", support, name="support"),
]
