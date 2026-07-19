from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from billing.application.services.openfactura import issue_tax_document
from billing.infrastructure.gateways import build_openfactura_gateway
from billing.models import TaxDocument


class Command(BaseCommand):
    help = "Issue pending or retryable OpenFactura documents."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=25)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        documents = list(TaxDocument.objects.filter(status__in=[TaxDocument.Status.PENDING, TaxDocument.Status.FAILED]).order_by("created_at")[: options["limit"]])
        if options["dry_run"]:
            self.stdout.write(f"eligible={len(documents)}")
            return
        if not settings.BILLING_OPENFACTURA_ENABLED:
            raise CommandError("BILLING_OPENFACTURA_ENABLED is false.")
        gateway = build_openfactura_gateway()
        issued = 0
        for document in documents:
            result = issue_tax_document(document=document, gateway=gateway, issuer=settings.BILLING_OPENFACTURA_ISSUER_JSON)
            issued += int(result.status == TaxDocument.Status.ISSUED)
        self.stdout.write(self.style.SUCCESS(f"processed={len(documents)} issued={issued}"))
