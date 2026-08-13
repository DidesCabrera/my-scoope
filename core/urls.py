from django.urls import path

from .views import (
    healthz,
    landing,
    msos,
    msos_detail,
    privacy,
    support,
    terms,
)

urlpatterns = [
    path("healthz/", healthz, name="healthz"),
    path("msos/", msos, name="msos"),
    path("msos/<slug:kind>/<slug:item_id>/", msos_detail, name="msos_detail"),
    path("", landing, name="landing"),
    path("privacy/", privacy, name="privacy"),
    path("terms/", terms, name="terms"),
    path("support/", support, name="support"),
]
