from datetime import time
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from notas.application.services.commands.calendarization_commands import activate_program_calendarization
from notas.domain.models import DailyPlan, DailyPlanMeal, Food, Meal, MealFood, Program, ProgramDay


class Command(BaseCommand):
    help = "Prepare an idempotent, non-secret demo program for an existing App Review account."

    def add_arguments(self, parser):
        parser.add_argument("--login", required=True, help="Existing reviewer username or email.")

    @transaction.atomic
    def handle(self, *args, **options):
        login = str(options["login"] or "").strip()
        user_model = get_user_model()
        user = user_model.objects.filter(username=login).first() or user_model.objects.filter(email=login).first()
        if user is None:
            raise CommandError("Create the reviewer account through the normal signup flow first.")

        profile = user.profile
        profile.onboarding_completed_at = profile.onboarding_completed_at or timezone.now()
        profile.onboarding_version = profile.ONBOARDING_VERSION_NUTRITION_V1
        profile.mobile_disclosure_version = profile.MOBILE_DISCLOSURE_VERSION
        profile.mobile_disclosure_accepted_at = timezone.now()
        profile.timezone_name = "America/Santiago"
        profile.save(update_fields=[
            "onboarding_completed_at", "onboarding_version", "mobile_disclosure_version",
            "mobile_disclosure_accepted_at", "timezone_name",
        ])

        foods = []
        for key, name, protein, carbs, fat in (
            ("app-review-chicken", "Pechuga de pollo", 31, 0, 3.6),
            ("app-review-rice", "Arroz cocido", 2.7, 28, 0.3),
            ("app-review-oats", "Avena", 16.9, 66, 6.9),
            ("app-review-yogurt", "Yogur alto en proteína", 10, 4, 0.5),
        ):
            food, _ = Food.objects.update_or_create(
                created_by=user,
                canonical_name=key,
                defaults={"name": name, "protein": protein, "carbs": carbs, "fat": fat, "is_active": True},
            )
            foods.append(food)

        breakfast, _ = Meal.objects.update_or_create(
            created_by=user, name="Desayuno de entrenamiento", defaults={"is_public": False, "is_draft": False}
        )
        lunch, _ = Meal.objects.update_or_create(
            created_by=user, name="Almuerzo base", defaults={"is_public": False, "is_draft": False}
        )
        for meal, rows in ((breakfast, ((foods[2], 80), (foods[3], 200))), (lunch, ((foods[0], 180), (foods[1], 220)))):
            for order, (food, quantity) in enumerate(rows, start=1):
                MealFood.objects.update_or_create(meal=meal, food=food, defaults={"quantity": quantity, "order": order})

        daily_plan, _ = DailyPlan.objects.update_or_create(
            created_by=user, name="Día de fuerza · revisión", defaults={"is_public": False, "is_draft": False}
        )
        DailyPlanMeal.objects.update_or_create(
            dailyplan=daily_plan, meal=breakfast, defaults={"hour": time(8), "order": 1}
        )
        DailyPlanMeal.objects.update_or_create(
            dailyplan=daily_plan, meal=lunch, defaults={"hour": time(13, 30), "order": 2}
        )
        program, _ = Program.objects.update_or_create(
            created_by=user, name="Semana de fuerza · App Review", defaults={"duration_weeks": 1}
        )
        for day_number in range(1, 8):
            ProgramDay.objects.update_or_create(
                program=program, week_number=1, day_number=day_number, defaults={"dailyplan": daily_plan}
            )

        current = user.program_calendarizations.filter(status__in=("scheduled", "active", "paused")).first()
        if current and current.source_program_id == program.id:
            self.stdout.write(self.style.SUCCESS(f"Demo already ready: calendarization {current.id}."))
            return
        if current:
            raise CommandError("The reviewer account already has another current program; do not replace it implicitly.")

        result = activate_program_calendarization(
            user=user,
            program=program,
            start_date=timezone.localdate(timezone=ZoneInfo("America/Santiago")),
            timezone_name="America/Santiago",
            daily_notification_time=time(7, 30),
            daily_notifications_enabled=True,
            meal_notifications_enabled=True,
            confirm_incomplete=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Demo ready: calendarization {result.calendarization.id}."))
