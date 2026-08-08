from pathlib import Path

from django.conf import settings

from billing.infrastructure.providers.apple_app_store import AppleAppStoreClient
from billing.infrastructure.providers.mercado_pago import MercadoPagoClient
from billing.infrastructure.providers.openfactura import OpenFacturaClient


def build_mercado_pago_gateway() -> MercadoPagoClient:
    return MercadoPagoClient(
        access_token=settings.BILLING_MERCADOPAGO_ACCESS_TOKEN,
        base_url=settings.BILLING_MERCADOPAGO_API_BASE_URL,
        timeout_seconds=settings.BILLING_MERCADOPAGO_TIMEOUT_SECONDS,
    )


def build_openfactura_gateway() -> OpenFacturaClient:
    return OpenFacturaClient(
        api_key=settings.BILLING_OPENFACTURA_API_KEY,
        base_url=settings.BILLING_OPENFACTURA_API_BASE_URL,
        timeout_seconds=settings.BILLING_OPENFACTURA_TIMEOUT_SECONDS,
    )


def build_apple_app_store_gateway() -> AppleAppStoreClient:
    default_certificate = Path(__file__).resolve().parent / "providers" / "AppleRootCA-G3.cer"
    return AppleAppStoreClient(
        bundle_id=settings.BILLING_APPLE_BUNDLE_ID,
        environment=settings.BILLING_APPLE_ENVIRONMENT,
        root_certificate_paths=(str(default_certificate),),
        online_checks=settings.BILLING_APPLE_ONLINE_CHECKS,
        app_apple_id=settings.BILLING_APPLE_APP_ID or None,
        signing_key=settings.BILLING_APPLE_IN_APP_PURCHASE_KEY,
        key_id=settings.BILLING_APPLE_KEY_ID,
        issuer_id=settings.BILLING_APPLE_ISSUER_ID,
    )
