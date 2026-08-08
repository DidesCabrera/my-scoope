from __future__ import annotations

import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from billing.application.services.apple_app_store import process_apple_notification
from billing.application.services.checkout import (
    BillingCheckoutUnavailable,
    cancel_user_subscription,
    create_subscription_checkout,
)
from billing.application.services.events import receive_verified_billing_event
from billing.application.services.mercado_pago_events import process_mercado_pago_event
from billing.infrastructure.gateways import build_apple_app_store_gateway, build_mercado_pago_gateway
from billing.infrastructure.providers.apple_app_store import InvalidAppleSignedData
from billing.infrastructure.providers.mercado_pago import MercadoPagoProviderError
from billing.infrastructure.providers.mercado_pago_webhooks import (
    InvalidMercadoPagoSignature,
    verify_mercado_pago_signature,
)
from billing.models import BillingProduct, PaymentProvider, ProviderSubscription
from billing.presentation.viewmodels import build_billing_overview_vm
from notas.presentation.composition.viewmodel.ui_builder import build_ui_vm
from notas.presentation.config.viewmodel_config import BILLING_VIEWMODE
from notas.presentation.viewmodels.base_vm import BaseVM

MAX_WEBHOOK_BODY_BYTES = 128 * 1024


@login_required
def billing_overview(request: HttpRequest) -> HttpResponse:
    content = build_billing_overview_vm(
        user=request.user,
        checkout_enabled=settings.BILLING_MERCADOPAGO_CHECKOUT_ENABLED,
    )
    vm = BaseVM(ui=build_ui_vm(BILLING_VIEWMODE), content=content)
    return render(request, "billing/overview.html", vm.as_context())


@login_required
@require_POST
def create_checkout(request: HttpRequest, product_id: int) -> HttpResponse:
    if not settings.BILLING_MERCADOPAGO_CHECKOUT_ENABLED:
        messages.error(request, "El checkout de Mercado Pago todavía no está habilitado.")
        return redirect("billing:overview")
    product = get_object_or_404(BillingProduct, pk=product_id, active=True)
    public_base_url = settings.BILLING_PUBLIC_BASE_URL.rstrip("/")
    if not public_base_url.startswith("https://"):
        messages.error(request, "Billing no tiene una URL pública HTTPS configurada.")
        return redirect("billing:overview")
    try:
        checkout = create_subscription_checkout(
            user=request.user,
            product=product,
            gateway=build_mercado_pago_gateway(),
            back_url=f"{public_base_url}{reverse('billing:checkout_return')}",
        )
    except (BillingCheckoutUnavailable, MercadoPagoProviderError, ValueError):
        messages.error(request, "No fue posible iniciar la suscripción. Revisa tu cuenta o inténtalo nuevamente.")
        return redirect("billing:overview")
    return redirect(checkout.checkout_url)


@login_required
def checkout_return(request: HttpRequest) -> HttpResponse:
    messages.info(request, "Mercado Pago está procesando tu suscripción. El estado se actualizará automáticamente.")
    return redirect("billing:overview")


@login_required
@require_POST
def cancel_subscription(request: HttpRequest, subscription_id: int) -> HttpResponse:
    if not settings.BILLING_MERCADOPAGO_CHECKOUT_ENABLED:
        messages.error(request, "La gestión de Mercado Pago todavía no está habilitada.")
        return redirect("billing:overview")
    subscription = get_object_or_404(ProviderSubscription, pk=subscription_id, user=request.user)
    try:
        cancel_user_subscription(
            user=request.user,
            subscription=subscription,
            gateway=build_mercado_pago_gateway(),
        )
    except (BillingCheckoutUnavailable, MercadoPagoProviderError, ValueError):
        messages.error(request, "No fue posible cancelar la suscripción. Inténtalo nuevamente.")
    else:
        messages.success(request, "La suscripción fue cancelada.")
    return redirect("billing:overview")


@csrf_exempt
@require_POST
def mercado_pago_webhook(request: HttpRequest) -> HttpResponse:
    if not settings.BILLING_MERCADOPAGO_WEBHOOK_ENABLED:
        return HttpResponse(status=404)
    if len(request.body) > MAX_WEBHOOK_BODY_BYTES:
        return HttpResponse(status=413)

    try:
        payload = json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return JsonResponse({"detail": "invalid_json"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "invalid_payload"}, status=400)

    query_data_id = str(request.GET.get("data.id") or "").strip()
    body_data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    body_data_id = str(body_data.get("id") or "").strip()
    if not query_data_id or not body_data_id or query_data_id.lower() != body_data_id.lower():
        return JsonResponse({"detail": "resource_id_mismatch"}, status=400)

    try:
        verify_mercado_pago_signature(
            signature_header=request.headers.get("x-signature", ""),
            request_id=request.headers.get("x-request-id", ""),
            data_id=query_data_id,
            secret=settings.BILLING_MERCADOPAGO_WEBHOOK_SECRET,
            tolerance_seconds=settings.BILLING_MERCADOPAGO_WEBHOOK_TOLERANCE_SECONDS,
        )
    except InvalidMercadoPagoSignature:
        return JsonResponse({"detail": "invalid_signature"}, status=401)

    event_type = str(payload.get("type") or "").strip()
    external_event_id = str(payload.get("id") or "").strip()
    if not event_type or not external_event_id:
        return JsonResponse({"detail": "missing_event_identity"}, status=400)

    receipt = receive_verified_billing_event(
        provider=PaymentProvider.MERCADO_PAGO,
        external_event_id=external_event_id,
        event_type=event_type,
        resource_id=body_data_id,
        payload=payload,
        signature_verified=True,
    )
    try:
        event = process_mercado_pago_event(event=receipt.event, gateway=build_mercado_pago_gateway())
    except Exception:
        return JsonResponse({"detail": "provider_reconciliation_failed"}, status=502)
    return JsonResponse({"status": event.status}, status=200)


@csrf_exempt
@require_POST
def apple_app_store_webhook(request: HttpRequest) -> HttpResponse:
    """Receive App Store Server Notifications V2 after signed-payload verification."""

    if not settings.BILLING_APPLE_NOTIFICATIONS_ENABLED:
        return HttpResponse(status=404)
    if len(request.body) > MAX_WEBHOOK_BODY_BYTES:
        return HttpResponse(status=413)
    try:
        payload = json.loads(request.body or b"{}")
    except (TypeError, ValueError):
        return JsonResponse({"detail": "invalid_json"}, status=400)
    signed_payload = str(payload.get("signedPayload") or "") if isinstance(payload, dict) else ""
    try:
        notification = build_apple_app_store_gateway().verify_notification(signed_payload)
    except InvalidAppleSignedData:
        return JsonResponse({"detail": "invalid_signature"}, status=401)
    if not notification.notification_uuid or not notification.notification_type:
        return JsonResponse({"detail": "missing_event_identity"}, status=400)

    transaction = notification.transaction
    normalized_payload = {
        "notification_uuid": notification.notification_uuid,
        "notification_type": notification.notification_type,
        "subtype": notification.subtype,
        "environment": notification.environment,
        "signed_date": notification.signed_date,
        "original_transaction_id": transaction.original_transaction_id if transaction else "",
        "transaction_id": transaction.transaction_id if transaction else "",
        "product_id": transaction.product_id if transaction else "",
    }
    receipt = receive_verified_billing_event(
        provider=PaymentProvider.APPLE_APP_STORE,
        external_event_id=notification.notification_uuid,
        event_type=notification.notification_type,
        resource_id=transaction.original_transaction_id if transaction else "",
        payload=normalized_payload,
        signature_verified=True,
    )
    try:
        event = process_apple_notification(event=receipt.event, notification=notification)
    except Exception:
        return JsonResponse({"detail": "provider_reconciliation_failed"}, status=502)
    return JsonResponse({"status": event.status}, status=200)
