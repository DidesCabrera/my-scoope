from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from food_catalog.infrastructure.external_providers.open_food_facts import OpenFoodFactsProvider


class Command(BaseCommand):
    help = "Search Open Food Facts without creating catalog/operational foods."

    def add_arguments(self, parser):
        parser.add_argument("query", help="Search expression or barcode/product code.")
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument(
            "--detail",
            action="store_true",
            help="Treat query as a barcode/product code and fetch detail instead of search.",
        )

    def handle(self, *args, **options):
        provider = OpenFoodFactsProvider.from_django_settings(settings)
        if options["detail"]:
            detail = provider.get_food(options["query"])
            self.stdout.write(self.style.SUCCESS(f"Open Food Facts detail: {detail.name}"))
            self.stdout.write(f"Provider id: {detail.external_food_id}")
            self.stdout.write(f"Brand: {detail.brand_name or '-'}")
            self.stdout.write(f"Servings: {len(detail.servings)}")
            for serving in detail.servings:
                self.stdout.write(
                    f"- {serving.external_serving_id or 'serving'} · {serving.serving_description or '-'} · "
                    f"kcal={serving.calories_kcal or '-'} protein={serving.protein_g or '-'} "
                    f"carbs={serving.carbs_g or '-'} fat={serving.fat_g or '-'}"
                )
            return

        results = provider.search(options["query"], max_results=options["limit"])
        self.stdout.write(self.style.SUCCESS(f"Open Food Facts returned {len(results)} result(s)."))
        for result in results:
            self.stdout.write(
                f"- [{result.external_food_id}] {result.name}"
                + (f" · {result.brand_name}" if result.brand_name else "")
                + (f" · {result.description}" if result.description else "")
            )
