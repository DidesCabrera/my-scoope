from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from core.mobile_association import (
    android_asset_links_payload,
    apple_app_site_association_payload,
)


@require_GET
def healthz(request):
    """Cheap process-level liveness probe for the deployment platform."""
    return JsonResponse({"status": "ok"})


def _association_response(payload):
    if payload is None:
        response = JsonResponse({"status": "not_configured"}, status=503)
    else:
        response = JsonResponse(payload, safe=not isinstance(payload, list))
    response["Cache-Control"] = "public, max-age=300"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_GET
def apple_app_site_association(request):
    return _association_response(apple_app_site_association_payload())


@require_GET
def android_asset_links(request):
    return _association_response(android_asset_links_payload())


def landing(request):
    from billing.presentation.public_catalog import build_public_credit_pack_prices, build_public_plan_benefits

    return render(request, "core/landing.html", {
        "plan_benefits": build_public_plan_benefits(),
        "credit_packs": build_public_credit_pack_prices(),
    })


def _legal_page_context(request):
    from_mobile_onboarding = request.GET.get("source") == "mobile-onboarding"
    return {
        "from_mobile_onboarding": from_mobile_onboarding,
        "legal_query_suffix": "?source=mobile-onboarding" if from_mobile_onboarding else "",
    }


def privacy(request):
    return render(request, "core/privacy.html", _legal_page_context(request))


def refund_policy(request):
    return render(request, "core/refund_policy.html", _legal_page_context(request))


def terms(request):
    return render(request, "core/terms.html", _legal_page_context(request))


def support(request):
    return render(request, "core/support.html", _legal_page_context(request))
