from django.urls import path

from notas.interface.views.pwa import (
    pwa_icon,
    pwa_manifest,
    pwa_service_worker,
    pwa_startup_image,
)

urlpatterns = [
    path("manifest.webmanifest", pwa_manifest, name="pwa_manifest"),
    path("icons/<int:size>.png", pwa_icon, name="pwa_icon"),
    path("startup/<slug:image_key>.png", pwa_startup_image, name="pwa_startup_image"),
    path("service-worker.js", pwa_service_worker, name="pwa_service_worker"),
]
