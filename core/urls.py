from django.urls import path

from .views import (
    healthz,
    landing,
    privacy,
    support,
    terms,
)

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("", landing, name="landing"),
    path("privacy/", privacy, name="privacy"),
    path("terms/", terms, name="terms"),
    path("support/", support, name="support"),
]
