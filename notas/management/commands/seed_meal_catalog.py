from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from notas.application.meal_catalog_seed import STARTER_MEAL_CATALOG
from notas.application.services.nutrition.meal_nutrition import rebuild_meal_cached_state
from notas.domain.models import Food, Meal, MealCatalogEntry, MealFood

CATALOG_USERNAME = "myscoope_catalog"


class Command(BaseCommand):
    help = "Validate or create the curated 30-meal starter catalog used by Explore."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Create or update the curated catalog.")
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Restore the starter definitions even when an administrator already edited them.",
        )

    def handle(self, *args, **options):
        required_names = sorted({name for item in STARTER_MEAL_CATALOG for name, _quantity in item["foods"]})
        foods_by_name = {food.name: food for food in Food.objects.filter(name__in=required_names, is_active=True)}
        missing = [name for name in required_names if name not in foods_by_name]
        if missing:
            raise CommandError(f"Missing {len(missing)} operational foods: {', '.join(missing)}")

        if not options["apply"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry run valid: {len(STARTER_MEAL_CATALOG)} catalog meals and {len(required_names)} foods resolved."
                )
            )
            return

        with transaction.atomic():
            user_model = get_user_model()
            owner, _created = user_model.objects.get_or_create(
                username=CATALOG_USERNAME,
                defaults={"first_name": "Equipo", "last_name": "My Scoope", "is_active": False},
            )
            # Serialize catalog seeds on the stable owner row. Render may start a
            # newer deploy while another pre-deploy is still seeding the catalog.
            owner = user_model.objects.select_for_update().get(pk=owner.pk)
            if owner.has_usable_password():
                owner.set_unusable_password()
                owner.save(update_fields=["password"])

            for sort_order, definition in enumerate(STARTER_MEAL_CATALOG, start=1):
                matching_meals = list(
                    Meal.objects.filter(created_by=owner, name=definition["name"])
                    .select_related("catalog_entry")
                    .order_by("id")
                )
                meal = next(
                    (candidate for candidate in matching_meals if hasattr(candidate, "catalog_entry")),
                    matching_meals[0] if matching_meals else None,
                )
                meal_created = meal is None
                if meal_created:
                    meal = Meal.objects.create(
                        created_by=owner,
                        name=definition["name"],
                        is_public=False,
                        is_forkable=True,
                        is_copiable=False,
                        is_draft=False,
                        scope=Meal.Scope.LIBRARY,
                    )
                else:
                    duplicate_ids = [candidate.id for candidate in matching_meals if candidate.id != meal.id]
                    if duplicate_ids:
                        # Preserve the meals because saved user copies may still
                        # reference them; remove only duplicate publications.
                        MealCatalogEntry.objects.filter(meal_id__in=duplicate_ids).delete()
                if meal_created or options["refresh"]:
                    if not meal_created:
                        meal.is_public = False
                        meal.is_forkable = True
                        meal.is_copiable = False
                        meal.is_draft = False
                        meal.scope = Meal.Scope.LIBRARY
                        meal.save(update_fields=["is_public", "is_forkable", "is_copiable", "is_draft", "scope"])
                    meal.meal_food_set.all().delete()
                    MealFood.objects.bulk_create([
                        MealFood(meal=meal, food=foods_by_name[name], quantity=quantity, order=order)
                        for order, (name, quantity) in enumerate(definition["foods"], start=1)
                    ])
                    rebuild_meal_cached_state(meal)
                entry, entry_created = MealCatalogEntry.objects.get_or_create(
                    meal=meal,
                    defaults={
                        "summary": definition["summary"],
                        "occasion": definition["occasion"],
                        "dietary_style": definition["dietary_style"],
                        "is_published": True,
                        "is_featured": sort_order <= 6,
                        "sort_order": sort_order,
                    },
                )
                if options["refresh"] and not entry_created:
                    entry.summary = definition["summary"]
                    entry.occasion = definition["occasion"]
                    entry.dietary_style = definition["dietary_style"]
                    entry.is_published = True
                    entry.is_featured = sort_order <= 6
                    entry.sort_order = sort_order
                    entry.save(update_fields=["summary", "occasion", "dietary_style", "is_published", "is_featured", "sort_order", "updated_at"])

        self.stdout.write(self.style.SUCCESS(f"Curated meal catalog ready: {len(STARTER_MEAL_CATALOG)} published meals."))
