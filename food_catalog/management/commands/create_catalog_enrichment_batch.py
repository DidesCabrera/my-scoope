import json

from django.core.management.base import BaseCommand, CommandError

from food_catalog.infrastructure.enrichment import create_enrichment_batch
from food_catalog.models import CatalogFood


class Command(BaseCommand):
    help = "Create a bounded enrichment batch and emit the production context for Codex."

    def add_arguments(self, parser):
        parser.add_argument("--ids", required=True, help="Comma-separated CatalogFood IDs.")
        parser.add_argument("--environment", required=True, choices=("staging", "production"))
        parser.add_argument("--reason", required=True)
        parser.add_argument("--instruction", default="")

    def handle(self, *args, **options):
        try:
            ids = sorted({int(value.strip()) for value in options["ids"].split(",") if value.strip()})
        except ValueError as exc:
            raise CommandError("--ids must contain integers") from exc
        foods = list(CatalogFood.objects.filter(pk__in=ids).prefetch_related("portions").order_by("id"))
        if len(foods) != len(ids):
            found = {food.pk for food in foods}
            raise CommandError(f"CatalogFood IDs not found: {sorted(set(ids) - found)}")
        batch = create_enrichment_batch(
            foods=foods, environment=options["environment"], reason=options["reason"],
            instruction=options["instruction"],
        )
        self.stdout.write(json.dumps({
            "batch_ref": str(batch.batch_ref),
            "contract_version": batch.contract_version,
            "input_sha256": batch.input_sha256,
            "scope": batch.scope_payload,
            "foods": [_context(food) for food in foods],
        }, ensure_ascii=False, indent=2, sort_keys=True))


def _context(food):
    default = food.portions.filter(is_default=True).order_by("id").first()
    return {
        "catalog_food_id": food.pk,
        "expected_updated_at": food.updated_at.isoformat(),
        "display_name": food.display_name,
        "food_group": food.food_group,
        "food_subgroup": food.food_subgroup,
        "preparation_state": food.preparation_state,
        "default_portion_g": str(default.grams) if default else None,
        "current": {
            "solver_min_portion_g": str(food.solver_min_portion_g) if food.solver_min_portion_g else None,
            "solver_max_portion_g": str(food.solver_max_portion_g) if food.solver_max_portion_g else None,
            "solver_portion_step_g": str(food.solver_portion_step_g) if food.solver_portion_step_g else None,
            "solver_enabled": food.solver_enabled,
            "food_form": food.food_form,
            "functional_roles": food.functional_roles,
            "meal_affinities": food.meal_affinities,
            "preparation_effort": food.preparation_effort,
            "cost_band": food.cost_band,
        },
    }
