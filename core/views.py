from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET


@require_GET
def healthz(request):
    """Cheap process-level liveness probe for the deployment platform."""
    return JsonResponse({"status": "ok"})


def landing(request):
    return render(request, "core/landing.html")


def privacy(request):
    return render(request, "core/privacy.html")


def terms(request):
    return render(request, "core/terms.html")


def support(request):
    return render(request, "core/support.html")
