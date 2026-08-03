from __future__ import annotations

import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood


class Command(BaseCommand):
    help = "Seed idempotent, disposable fixtures for authenticated browser tests."

    def add_arguments(self, parser):
        parser.add_argument("--login", default="e2e-ci@my-scoope.test")
        parser.add_argument("--password", required=True)
        parser.add_argument("--github-env", action="store_true")
        parser.add_argument("--github-env-path", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        login = str(options["login"] or "").strip().lower()
        password = str(options["password"] or "")
        if not login or not password:
            raise CommandError("A non-empty --login and --password are required.")

        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            username=login,
            defaults={"email": login, "is_active": True},
        )
        changed_fields = []
        if user.email != login:
            user.email = login
            changed_fields.append("email")
        if not user.is_active:
            user.is_active = True
            changed_fields.append("is_active")
        user.set_password(password)
        changed_fields.append("password")
        user.save(update_fields=changed_fields)

        searchable_food, _ = Food.objects.update_or_create(
            created_by=user,
            canonical_name="e2e-pechuga-pollo-cocida",
            defaults={
                "name": "Pechuga Pollo Cocida",
                "protein": 31,
                "carbs": 0,
                "fat": 3.6,
                "is_global": True,
                "is_active": True,
                "is_verified": True,
            },
        )
        base_foods = []
        for index in range(1, 6):
            food, _ = Food.objects.update_or_create(
                created_by=user,
                canonical_name=f"e2e-base-food-{index}",
                defaults={
                    "name": f"E2E alimento base {index}",
                    "protein": 5 + index,
                    "carbs": 10 + index,
                    "fat": 2 + index,
                    "is_active": True,
                    "is_verified": True,
                },
            )
            base_foods.append(food)

        meal, _ = Meal.objects.update_or_create(
            created_by=user,
            name="E2E Comida Editable",
            defaults={"is_public": False, "is_draft": False},
        )
        for order, food in enumerate(base_foods, start=1):
            MealFood.objects.update_or_create(
                meal=meal,
                food=food,
                defaults={"quantity": 80 + order * 10, "order": order},
            )

        browse_meal, _ = Meal.objects.update_or_create(
            created_by=user,
            name="Nueva Comida 2",
            defaults={"is_public": False, "is_draft": False},
        )
        MealFood.objects.update_or_create(
            meal=browse_meal,
            food=searchable_food,
            defaults={"quantity": 100, "order": 1},
        )

        dailyplan, _ = DailyPlan.objects.update_or_create(
            created_by=user,
            name="E2E Plan Editable",
            defaults={"is_public": False, "is_draft": False},
        )
        dailyplan_meal, _ = DailyPlanMeal.objects.update_or_create(
            dailyplan=dailyplan,
            meal=meal,
            defaults={"order": 1},
        )

        payload = {
            "MYSCOOPE_E2E_LOGIN": login,
            "MYSCOOPE_E2E_MEAL_ID": meal.pk,
            "MYSCOOPE_E2E_DAILYPLAN_ID": dailyplan.pk,
            "MYSCOOPE_E2E_DAILYPLAN_MEAL_ID": dailyplan_meal.pk,
        }
        github_env_lines = "".join(f"{key}={value}\n" for key, value in payload.items())
        github_env_path = str(options["github_env_path"] or "").strip()
        if github_env_path:
            with Path(github_env_path).open("a", encoding="utf-8") as env_file:
                env_file.write(github_env_lines)
            self.stdout.write(json.dumps({"github_env_written": True, **payload}, sort_keys=True))
        elif options["github_env"]:
            self.stdout.write(github_env_lines.rstrip())
        else:
            self.stdout.write(json.dumps(payload, sort_keys=True))
