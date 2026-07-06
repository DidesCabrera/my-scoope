from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from food_catalog.application.external_providers.contracts import ExternalFoodProviderError
from food_catalog.infrastructure.external_providers.fatsecret import FatSecretProvider


class Command(BaseCommand):
    help = "Search FatSecret as an external lookup provider without persisting results."

    def add_arguments(self, parser):
        parser.add_argument("query", help="Search expression to send to FatSecret.")
        parser.add_argument("--max-results", type=int, default=10)

    def handle(self, *args, **options):
        provider = FatSecretProvider.from_django_settings(settings)
        try:
            results = provider.search(options["query"], max_results=options["max_results"])
        except ExternalFoodProviderError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(f"FatSecret returned {len(results)} result(s)."))
        self.stdout.write("These are external lookup results only; nothing was persisted.")
        for result in results:
            self.stdout.write(
                f"- {result.name} [{result.external_food_id}]"
                + (f" · {result.brand_name}" if result.brand_name else "")
            )
