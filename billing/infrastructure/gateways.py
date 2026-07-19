from django.conf import settings

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
