from datetime import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from notas.application.dailyplan_catalog_seed import STARTER_DAILYPLAN_CATALOG
from notas.application.services.cache.dailyplan_summary import refresh_dailyplan_summary_cache
from notas.application.services.commands.meal_commands import fork_meal_for_dailyplan
from notas.domain.models import DailyPlan, DailyPlanCatalogEntry, DailyPlanMeal, Meal, MealCatalogEntry

CATALOG_USERNAME = "myscoope_catalog"


class Command(BaseCommand):
    help = "Validate or create the curated starter catalog for Explore plans."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--refresh", action="store_true", help="Restore starter definitions edited by an administrator.")

    def handle(self, *args, **options):
        names = {name for definition in STARTER_DAILYPLAN_CATALOG for name, _hour in definition["meals"]}
        entries = {
            entry.meal.name: entry
            for entry in MealCatalogEntry.objects.select_related("meal").filter(meal__name__in=names, is_published=True, meal__is_draft=False)
        }
        missing = sorted(names - entries.keys())
        if missing:
            raise CommandError(f"Missing {len(missing)} published catalog meals: {', '.join(missing)}")
        compatible = {
            "omnivore": {"omnivore", "pescatarian", "vegetarian", "vegan"},
            "pescatarian": {"pescatarian", "vegetarian", "vegan"},
            "vegetarian": {"vegetarian", "vegan"},
            "vegan": {"vegan"},
        }
        for definition in STARTER_DAILYPLAN_CATALOG:
            for name, _hour in definition["meals"]:
                if entries[name].dietary_style not in compatible[definition["dietary_style"]]:
                    raise CommandError(f"Incompatible dietary style in {definition['name']}: {name}")
        if not options["apply"]:
            self.stdout.write(self.style.SUCCESS(f"Dry run valid: {len(STARTER_DAILYPLAN_CATALOG)} plans and {len(names)} meals resolved."))
            return

        with transaction.atomic():
            owner, _created = get_user_model().objects.get_or_create(
                username=CATALOG_USERNAME,
                defaults={"first_name": "Equipo", "last_name": "My Scoope", "is_active": False},
            )
            if owner.has_usable_password():
                owner.set_unusable_password()
                owner.save(update_fields=["password"])
            for sort_order, definition in enumerate(STARTER_DAILYPLAN_CATALOG, start=1):
                plan, created = DailyPlan.objects.get_or_create(
                    created_by=owner,
                    name=definition["name"],
                    defaults={"source": DailyPlan.SOURCE_SYSTEM, "is_public": False, "is_draft": False},
                )
                if created or options["refresh"]:
                    if not created:
                        embedded_ids = list(plan.dailyplan_meals.values_list("meal_id", flat=True))
                        plan.dailyplan_meals.all().delete()
                        Meal.objects.filter(pk__in=embedded_ids, scope=Meal.Scope.EMBEDDED, created_by=owner).delete()
                        plan.source = DailyPlan.SOURCE_SYSTEM
                        plan.is_public = False
                        plan.is_draft = False
                        plan.save(update_fields=["source", "is_public", "is_draft"])
                    for order, (name, hour) in enumerate(definition["meals"], start=1):
                        meal = fork_meal_for_dailyplan(entries[name].meal, owner)
                        DailyPlanMeal.objects.create(dailyplan=plan, meal=meal, hour=time.fromisoformat(hour), order=order)
                    refresh_dailyplan_summary_cache(plan)
                entry, entry_created = DailyPlanCatalogEntry.objects.get_or_create(
                    dailyplan=plan,
                    defaults={"summary": definition["summary"], "dietary_style": definition["dietary_style"], "is_published": True, "sort_order": sort_order},
                )
                if options["refresh"] and not entry_created:
                    entry.summary = definition["summary"]
                    entry.dietary_style = definition["dietary_style"]
                    entry.is_published = True
                    entry.sort_order = sort_order
                    entry.save(update_fields=["summary", "dietary_style", "is_published", "sort_order", "updated_at"])
        self.stdout.write(self.style.SUCCESS(f"Curated daily-plan catalog ready: {len(STARTER_DAILYPLAN_CATALOG)} plans."))
