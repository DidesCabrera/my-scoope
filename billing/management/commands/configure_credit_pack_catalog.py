from django.core.management.base import BaseCommand, CommandError

from billing.application.services.credit_packs import CreditPackUnavailable, configure_credit_pack_product
from billing.models import PaymentProvider


class Command(BaseCommand):
    help = "Map verified one-time provider products to canonical credit packs."

    def add_arguments(self, parser):
        parser.add_argument("--provider", required=True, choices=PaymentProvider.values)
        parser.add_argument("--environment", required=True, choices=("sandbox", "live"))
        parser.add_argument("--offer-code", required=True)
        parser.add_argument("--product-id", required=True)
        parser.add_argument("--price-id", default="")

    def handle(self, *args, **options):
        try:
            product = configure_credit_pack_product(
                provider=options["provider"], environment=options["environment"],
                offer_code=options["offer_code"], external_product_id=options["product_id"],
                external_price_id=options["price_id"],
            )
        except CreditPackUnavailable as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f"Credit pack mapping ready: {product.pk}"))
