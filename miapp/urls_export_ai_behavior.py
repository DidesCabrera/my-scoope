"""Minimal URLConf for executable AI behavior export validation."""

from django.http import JsonResponse
from django.urls import path


def export_health(request):
    return JsonResponse({"workspace": "ai_behavior", "status": "ok"})


urlpatterns = [path("__export__/health/", export_health, name="export_health")]
