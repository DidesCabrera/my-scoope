from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from billing.application.services.openfactura import reconcile_tax_document
from billing.application.services.provider_sync import sync_provider_subscription
from billing.infrastructure.gateways import build_mercado_pago_gateway, build_openfactura_gateway
from billing.models import PaymentProvider, ProviderSubscription, TaxDocument


class Command(BaseCommand):
    help = "Reconcile provider subscription and OpenFactura document state."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        limit = options["limit"]
        subscriptions = list(
            ProviderSubscription.objects.filter(provider=PaymentProvider.MERCADO_PAGO)
            .order_by("updated_at")[:limit]
        )
        documents = list(TaxDocument.objects.exclude(document_token="").filter(status__in=[TaxDocument.Status.ISSUED, TaxDocument.Status.REJECTED]).order_by("updated_at")[:limit])
        if options["dry_run"]:
            self.stdout.write(f"subscriptions={len(subscriptions)} tax_documents={len(documents)}")
            return
        if not settings.BILLING_MERCADOPAGO_ACCESS_TOKEN:
            raise CommandError("Mercado Pago access token is not configured.")
        payment_gateway = build_mercado_pago_gateway()
        for subscription in subscriptions:
            sync_provider_subscription(payment_gateway.get_subscription(subscription.external_subscription_id))
        if documents:
            if not settings.BILLING_OPENFACTURA_ENABLED:
                raise CommandError("OpenFactura is disabled while documents require reconciliation.")
            tax_gateway = build_openfactura_gateway()
            for document in documents:
                reconcile_tax_document(document=document, gateway=tax_gateway)
        self.stdout.write(self.style.SUCCESS(f"subscriptions={len(subscriptions)} tax_documents={len(documents)}"))
