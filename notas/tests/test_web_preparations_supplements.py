from zoneinfo import ZoneInfo

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from accounts.seed_plans import seed_account_plans
from notas.domain.models import (
    CalendarizedDay,
    CalendarizedSupplementIntakeExecution,
    DailyPlan,
    Food,
    Meal,
    MealPreparation,
    Preparation,
    ProgramCalendarization,
    Supplement,
    SupplementIntake,
    SupplementIntakeItem,
    SupplementIntakePreset,
)


@override_settings(
    NUTRITION_ONBOARDING_GATE_ENABLED=False,
    PERSONAL_PREPARATIONS_FEATURE_ENABLED=True,
    SUPPLEMENTS_FEATURE_ENABLED=True,
)
class WebPreparationsAndSupplementsTests(TestCase):
    def setUp(self):
        seed_account_plans()
        self.user = User.objects.create_user(username="web-parity", password="test-password")
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="pro")},
        )
        self.client.force_login(self.user)
        self.food = Food.objects.create(
            name="Avena", protein=10, carbs=60, fat=5, is_global=True,
            preparation_state="dry", sodium_mg_per_100g=2,
        )

    def test_personal_preparation_flows_from_library_into_meal(self):
        meal = Meal.objects.create(name="Desayuno", created_by=self.user)
        created = self.client.post(reverse("preparation_create"), {"name": "Avena casera"})
        self.assertEqual(created.status_code, 302)
        preparation = Preparation.objects.get(created_by=self.user, name="Avena casera")
        self.assertIsNone(preparation.current_version)
        self.assertContains(self.client.get(reverse("preparation_detail", args=[preparation.pk])), "Borrador")
        self.assertContains(self.client.get(reverse("preparation_edit", args=[preparation.pk]) + "?food=Avena"), "Avena")
        added = self.client.post(reverse("preparation_edit", args=[preparation.pk]), {
            "action": "add_food", "food_id": self.food.pk, "quantity_g": "80",
        })
        self.assertEqual(added.status_code, 302)
        preparation.refresh_from_db()
        self.assertIsNotNone(preparation.current_version)
        library = self.client.get(reverse("preparation_list"))
        self.assertContains(library, 'class="entity-card entity-card--preparation"')
        self.assertContains(library, reverse("preparation_detail", args=[preparation.pk]))
        self.assertContains(library, 'data-card-panel-target="preparation-foods-')
        self.assertContains(library, "Porción habitual · 100 g")
        detail = self.client.get(reverse("preparation_detail", args=[preparation.pk]))
        self.assertContains(detail, "Receta completa")
        self.assertContains(detail, "Porción (100 g)")
        self.assertContains(detail, "Composición de la preparación")
        self.assertContains(detail, "Detalle de cada ingrediente")
        self.assertContains(detail, "Información de la preparación")
        self.assertContains(detail, "Avena")
        self.assertContains(detail, 'class="dash-kpi-comp"')
        self.assertContains(detail, 'data-target="#card-grid-calories-')
        self.assertContains(detail, 'entity-card--food card food-child-card')
        self.assertContains(detail, f'data-food-id="{self.food.id}"')
        self.assertNotContains(detail, 'name="quantity_g"')
        relation = self.client.post(reverse("meal_preparation_add", args=[meal.pk]), {
            "preparation_id": preparation.pk, "units": "1.5",
        })
        self.assertEqual(relation.status_code, 302)
        self.assertEqual(MealPreparation.objects.get(meal=meal).quantity_g, 150)
        self.assertContains(self.client.get(reverse("meal_detail", args=[meal.pk])), "Avena casera")
        relation = MealPreparation.objects.get(meal=meal)
        self.assertEqual(self.client.post(reverse("meal_preparation_update", args=[meal.pk, relation.pk]), {
            "mode": "grams", "quantity": "60",
        }).status_code, 302)
        relation.refresh_from_db()
        self.assertEqual(relation.quantity_g, 60)
        self.client.post(reverse("preparation_edit", args=[preparation.pk]), {
            "action": "update_food", "food_id": self.food.pk, "quantity_g": "120",
        })
        preparation.refresh_from_db()
        self.assertEqual(preparation.current_version.ingredients.get().quantity_g, 120)

    def test_preparation_rename_preserves_estimated_yield_until_manual_override(self):
        created = self.client.post(reverse("preparation_create"), {"name": "Avena inicial"})
        self.assertEqual(created.status_code, 302)
        preparation = Preparation.objects.get(created_by=self.user, name="Avena inicial")
        self.client.post(reverse("preparation_edit", args=[preparation.pk]), {
            "action": "add_food", "food_id": self.food.pk, "quantity_g": "80",
        })
        preparation.refresh_from_db()
        self.assertFalse(preparation.current_version.evidence["yield_is_manual"])

        self.client.post(reverse("preparation_edit", args=[preparation.pk]), {
            "action": "save", "name": "Avena renombrada", "yield_g": "80",
            "default_portion_g": "100",
        })
        preparation.refresh_from_db()
        self.assertFalse(preparation.current_version.evidence["yield_is_manual"])
        self.assertEqual(preparation.name, "Avena renombrada")

        self.client.post(reverse("preparation_edit", args=[preparation.pk]), {
            "action": "save", "name": preparation.name, "manual_yield": "1",
            "yield_g": "120", "default_portion_g": "100",
        })
        preparation.refresh_from_db()
        self.assertTrue(preparation.current_version.evidence["yield_is_manual"])
        self.assertEqual(preparation.current_version.yield_g, 120)

    def test_supplement_intake_does_not_change_plan_nutrition(self):
        plan = DailyPlan.objects.create(name="Minuta", created_by=self.user)
        response = self.client.post(reverse("supplement_create"), {"name": "Vitamina D"})
        self.assertEqual(response.status_code, 302)
        supplement = Supplement.objects.get(created_by=self.user)
        library = self.client.get(reverse("supplement_list"))
        self.assertContains(library, 'class="entity-card entity-card--supplement"')
        self.assertContains(library, reverse("supplement_detail", args=[supplement.pk]))
        self.assertContains(self.client.get(reverse("supplement_detail", args=[supplement.pk])), "Vitamina D")
        self.assertContains(self.client.get(reverse("supplement_detail", args=[supplement.pk])), "Información nutricional")
        self.assertNotContains(self.client.get(reverse("supplement_detail", args=[supplement.pk])), 'name="default_quantity"')
        response = self.client.post(reverse("dailyplan_intake_add", args=[plan.pk]), {
            "intake_id": [str(supplement.pk)], "intake_quantity": ["1"],
            "intake_unit": ["capsule"], "hour": "08:30",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(SupplementIntake.objects.filter(dailyplan=plan).count(), 1)
        plan.refresh_from_db()
        self.assertEqual(plan.total_kcal, 0)
        self.assertContains(self.client.get(reverse("dailyplan_detail", args=[plan.pk])), "Vitamina D")
        intake = SupplementIntake.objects.get(dailyplan=plan)
        self.assertEqual(self.client.post(reverse("dailyplan_intake_update", args=[plan.pk, intake.pk]), {
            "item_id": [str(intake.items.get().pk)], "quantity": ["2"],
            "unit": ["capsule"], "hour": "09:00",
        }).status_code, 302)
        self.assertEqual(intake.items.get().quantity, 2)
        preset_saved = self.client.post(reverse("supplement_preset_create"), {
            "name": "Mañana", "preset_id": [str(supplement.pk)],
            "preset_quantity": ["2"], "preset_unit": ["capsule"],
        })
        self.assertEqual(preset_saved.status_code, 302)
        preset = SupplementIntakePreset.objects.get(created_by=self.user)
        library = self.client.get(reverse("supplement_list"))
        self.assertContains(library, reverse("supplement_preset_detail", args=[preset.pk]))
        self.assertEqual(preset_saved.url, reverse("supplement_preset_detail", args=[preset.pk]))
        preset_detail = self.client.get(reverse("supplement_preset_detail", args=[preset.pk]))
        self.assertContains(preset_detail, "Mañana")
        self.assertContains(preset_detail, "Composición de la ingesta")
        self.assertContains(preset_detail, reverse("supplement_preset_edit", args=[preset.pk]))
        self.assertNotContains(preset_detail, 'name="preset_quantity"')
        self.assertContains(self.client.get(reverse("supplement_preset_edit", args=[preset.pk])), 'name="preset_quantity"')

    def test_dailyplan_list_card_exposes_owned_supplements_in_collapsible_panel(self):
        plan = DailyPlan.objects.create(name="Minuta con suplementos", created_by=self.user, is_draft=False)
        intake = SupplementIntake.objects.create(dailyplan=plan, hour=timezone.datetime(2026, 1, 1, 8, 30).time())
        SupplementIntakeItem.objects.create(
            intake=intake, supplement_snapshot={"name": "Magnesio"},
            quantity="2", unit="cápsulas",
        )

        response = self.client.get(reverse("dailyplan_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-card-panel-target="dailyplan-meals-')
        self.assertContains(response, 'data-card-panel-target="dailyplan-supplements-')
        self.assertContains(response, 'data-card-panel-target="dailyplan-foods-')
        self.assertContains(response, 'class="entity-card__panel" role="region" aria-label="Suplementos de Minuta con suplementos" hidden')
        self.assertContains(response, "Magnesio · 2 cápsulas")
        self.assertNotContains(response, 'class="entity-card__footer card-bottom"')

    @override_settings(SUPPLEMENTS_FEATURE_ENABLED=False)
    def test_dailyplan_list_hides_supplement_panel_when_feature_is_disabled(self):
        DailyPlan.objects.create(name="Minuta sin suplementos", created_by=self.user, is_draft=False)

        response = self.client.get(reverse("dailyplan_list"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-card-panel-target="dailyplan-supplements-')

    def test_supplement_form_keeps_decimal_values_and_rejects_incomplete_intake(self):
        plan = DailyPlan.objects.create(name="Minuta", created_by=self.user)
        supplement = Supplement.objects.create(
            created_by=self.user, name="Magnesio", default_quantity="1.5",
            default_unit="capsule", nutrition={"protein_g": 1.25},
        )
        detail = self.client.get(reverse("supplement_edit", args=[supplement.pk]))
        self.assertContains(detail, 'name="default_quantity" value="1.500"')
        self.assertContains(detail, 'name="protein_g" type="number" min="0" step="0.001" value="1.25"')
        self.assertNotContains(self.client.get(reverse("supplement_detail", args=[supplement.pk])), "Notas personales")
        response = self.client.post(reverse("dailyplan_intake_add", args=[plan.pk]), {
            "intake_id": [str(supplement.pk), ""],
            "intake_quantity": ["1", "2"],
            "intake_unit": ["capsule", "capsule"],
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(SupplementIntake.objects.filter(dailyplan=plan).exists())

    def test_supplement_detail_is_read_only_and_localizes_dose(self):
        supplement = Supplement.objects.create(
            created_by=self.user, name="Magnesio", form="capsule",
            default_quantity="2", default_unit="capsule",
            components=[{"name": "Magnesio", "quantity": "200", "unit": "mg"}],
            nutrition={"energy_kcal": 0, "sodium_mg": 5},
            user_information="Nota personal",
        )
        detail = self.client.get(reverse("supplement_detail", args=[supplement.pk]))
        self.assertContains(detail, "Dosis predeterminada")
        self.assertContains(detail, "2 cápsulas")
        self.assertContains(detail, "1 componente")
        self.assertContains(detail, "Nota personal")
        self.assertContains(detail, reverse("supplement_edit", args=[supplement.pk]))
        self.assertNotContains(detail, 'name="component_name"')

    def test_other_user_cannot_read_or_change_private_entities(self):
        supplement = Supplement.objects.create(created_by=self.user, name="Privado")
        preparation = Preparation.objects.create(name="Privada", is_global=False, created_by=self.user)
        other = User.objects.create_user(username="other-web", password="test-password")
        AccountSubscription.objects.update_or_create(
            user=other, defaults={"plan": AccountPlan.objects.get(slug="pro")},
        )
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("supplement_detail", args=[supplement.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("supplement_edit", args=[supplement.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("preparation_detail", args=[preparation.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("preparation_edit", args=[preparation.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("supplement_remove", args=[supplement.pk])).status_code, 404)

    @override_settings(SUPPLEMENTS_FEATURE_ENABLED=False, PERSONAL_PREPARATIONS_FEATURE_ENABLED=False)
    def test_disabled_features_keep_curated_preparations_visible_and_block_writes(self):
        self.assertContains(self.client.get(reverse("preparation_list")), "Preparaciones del catálogo")
        self.assertEqual(self.client.post(reverse("preparation_create"), {"name": "Privada"}).status_code, 403)
        self.assertContains(self.client.get(reverse("supplement_list")), "Suplementos Pro")
        self.assertEqual(self.client.post(reverse("supplement_create"), {"name": "Vitamina"}).status_code, 403)

    def test_calendarized_preparation_is_distinct_and_only_changes_that_day(self):
        self.client.post(reverse("preparation_create"), {"name": "Avena casera"})
        preparation = Preparation.objects.get(created_by=self.user, name="Avena casera")
        self.client.post(reverse("preparation_edit", args=[preparation.pk]), {
            "action": "add_food", "food_id": self.food.pk, "quantity_g": "80",
        })
        today = timezone.now().astimezone(ZoneInfo("UTC")).date()
        calendarization = ProgramCalendarization.objects.create(
            user=self.user, program_name_snapshot="Programa",
            start_date=today, end_date=today, timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization, calendar_date=today,
            week_number=1, day_number=1,
            plan_snapshot={"name": "Minuta", "meals": [{"key": "meal-1", "name": "Desayuno", "foods": [], "totals": {}}], "totals": {}},
        )
        response = self.client.post(reverse("calendarized_preparation_add", args=[day.pk, "meal-1"]), {
            "preparation_id": preparation.pk, "units": "1",
        })
        self.assertEqual(response.status_code, 302)
        day.refresh_from_db()
        component = day.plan_snapshot["meals"][0]["foods"][0]
        self.assertEqual(component["component_type"], "preparation")
        self.assertEqual(component["name"], "Avena casera")
        self.assertEqual(component["ingredients"][0]["quantity_g"], 100)
        self.assertContains(self.client.get(reverse("calendarization_meal_detail", args=[day.pk, "meal-1"])), "Preparaciones de esta Comida")
        removed = self.client.post(reverse("calendarized_preparation_remove", args=[day.pk, "meal-1", component["key"]]))
        self.assertEqual(removed.status_code, 302)
        day.refresh_from_db()
        self.assertEqual(day.plan_snapshot["meals"][0]["foods"], [])

    def test_calendarized_supplement_check_in_is_owner_scoped(self):
        today = timezone.now().astimezone(ZoneInfo("UTC")).date()
        calendarization = ProgramCalendarization.objects.create(
            user=self.user, program_name_snapshot="Programa",
            start_date=today, end_date=today, timezone_name="UTC",
            status=ProgramCalendarization.STATUS_ACTIVE,
        )
        day = CalendarizedDay.objects.create(
            calendarization=calendarization, calendar_date=today,
            week_number=1, day_number=1,
            plan_snapshot={"name": "Minuta", "meals": [], "totals": {}, "supplement_intakes": [
                {"key": "supplement_intake:1", "label": "Ingesta 1", "items": [{"supplement": {"name": "Vitamina D"}, "quantity": "1", "unit": "capsule"}]},
            ]},
        )
        response = self.client.post(reverse("calendarization_supplement_intake_check_in", args=[day.pk, "supplement_intake:1"]), {
            "action": "completed", "idempotency_key": "web-test-intake-completed",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(CalendarizedSupplementIntakeExecution.objects.get().action, "completed")
        self.assertEqual(self.client.post(reverse("calendarization_supplement_intake_check_in", args=[day.pk, "other"]), {
            "action": "completed", "idempotency_key": "web-test-other",
        }).status_code, 404)
