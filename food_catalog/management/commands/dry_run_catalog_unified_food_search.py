from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand

from food_catalog.application.unified_search import search_unified_food_catalog
from food_catalog.infrastructure.external_providers.fatsecret import FatSecretProvider
from food_catalog.infrastructure.external_providers.open_food_facts import OpenFoodFactsProvider


class Command(BaseCommand):
    help = "Search the curated Food Catalog and optionally FatSecret without creating catalog/operational foods."

    def add_arguments(self, parser):
        parser.add_argument("query", help="Search expression.")
        parser.add_argument("--catalog-limit", type=int, default=10)
        parser.add_argument("--external-limit", type=int, default=10)
        parser.add_argument(
            "--include-fatsecret",
            action="store_true",
            help="Also search FatSecret as an external lookup provider.",
        )
        parser.add_argument(
            "--include-openfoodfacts",
            action="store_true",
            help="Also search Open Food Facts as an external lookup provider.",
        )
        parser.add_argument(
            "--record-external-references",
            action="store_true",
            help=(
                "Record ExternalFoodReference metadata for external lookup results. "
                "Nutrition payloads are not persisted."
            ),
        )

    def handle(self, *args, **options):
        providers = []
        if options["include_fatsecret"]:
            providers.append(FatSecretProvider.from_django_settings(settings))
        if options["include_openfoodfacts"]:
            providers.append(OpenFoodFactsProvider.from_django_settings(settings))

        results = search_unified_food_catalog(
            options["query"],
            catalog_limit=options["catalog_limit"],
            external_limit=options["external_limit"],
            external_providers=providers,
            include_external=bool(providers),
            record_external_references=options["record_external_references"],
        )

        self.stdout.write(self.style.SUCCESS(f"Unified search returned {len(results.items)} result(s)."))
        self.stdout.write(f"Catalog results: {results.catalog_count}")
        self.stdout.write(f"External results: {results.external_count}")
        if results.errors:
            self.stdout.write(self.style.WARNING("External provider errors: " + " | ".join(results.errors)))

        if providers and not options["record_external_references"]:
            self.stdout.write("External results were shown without recording references.")

        for item in results.items:
            if item.is_catalog_item:
                self.stdout.write(
                    f"- [catalog:{item.catalog_food_id}] {item.display_name}"
                    + (f" · {item.brand_name}" if item.brand_name else "")
                    + f" · quality={item.data_quality_score}"
                )
            else:
                reference = f" ref={item.external_reference_id}" if item.external_reference_id else ""
                self.stdout.write(
                    f"- [{item.provider}:{item.external_food_id}] {item.display_name}"
                    + (f" · {item.brand_name}" if item.brand_name else "")
                    + reference
                    + " · external lookup"
                )
