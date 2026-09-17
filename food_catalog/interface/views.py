from __future__ import annotations

import hmac

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from food_catalog.infrastructure.releases import (
    build_authority_snapshot_envelope,
    release_envelope,
)
from food_catalog.models import CatalogRelease


@require_GET
def catalog_healthz(_request):
    return JsonResponse({"status": "ok", "service": "myscoope-food-catalog"})


@require_GET
def catalog_service_info(_request):
    return JsonResponse(
        {
            "service": "myscoope-food-catalog",
            "delivery": "immutable-releases",
        }
    )


@require_GET
def export_catalog_release(request, version: str):
    authorization_error = _authorization_error(request)
    if authorization_error:
        return authorization_error

    releases = CatalogRelease.objects.filter(
        role=CatalogRelease.ROLE_AUTHORITY,
        status=CatalogRelease.STATUS_APPROVED,
    )
    if version == "latest":
        release = releases.order_by("-approved_at", "-id").first()
    else:
        release = releases.filter(version=version).first()
    if release is None:
        return JsonResponse({"error": "release_not_found"}, status=404)
    return JsonResponse(release_envelope(release), json_dumps_params={"ensure_ascii": False})


@require_GET
def export_authority_snapshot(request):
    authorization_error = _authorization_error(request)
    if authorization_error:
        return authorization_error
    if not bool(getattr(settings, "FOOD_CATALOG_AUTHORITY_EXPORT_ENABLED", False)):
        return JsonResponse({"error": "authority_export_disabled"}, status=404)
    return JsonResponse(
        build_authority_snapshot_envelope(),
        json_dumps_params={"ensure_ascii": False},
    )


def _authorization_error(request):
    configured_token = str(
        getattr(settings, "FOOD_CATALOG_RELEASE_TOKEN", "") or ""
    ).strip()
    supplied_token = _bearer_token(request)
    if not configured_token:
        return JsonResponse({"error": "release_delivery_not_configured"}, status=503)
    if not supplied_token or not hmac.compare_digest(supplied_token, configured_token):
        return JsonResponse({"error": "release_delivery_unauthorized"}, status=401)
    return None


def _bearer_token(request) -> str:
    authorization = str(request.headers.get("Authorization") or "").strip()
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return ""
    return authorization.removeprefix(prefix).strip()
