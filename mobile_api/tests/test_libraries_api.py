from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import (
    MOBILE_SCOPE_READ,
)
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    FoodLabelCaptureReceipt,
    FoodShare,
    Meal,
    MealFood,
    Program,
    ProgramDay,
)


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPILibrariesTests(AuthenticatedMobileAPITestCase):
    def test_food_search_is_paginated_and_respects_existing_visibility(self):
        personal = Food.objects.create(name="Arroz personal", protein=7, carbs=78, fat=1, created_by=self.user)
        Food.objects.create(name="Arroz global", protein=8, carbs=77, fat=1, created_by=None, is_global=True)
        other = User.objects.create_user(username="other-user")
        private = Food.objects.create(name="Arroz privado ajeno", protein=9, carbs=70, fat=2, created_by=other)

        response = self.client.get("/api/v1/foods", {"search": "Arroz", "offset": 0, "limit": 1})

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["limit"], 1)
        self.assertEqual(len(data["items"]), 1)
        self.assertTrue(data["items"][0]["is_user_food"])
        self.assertIn("protein_allocation", data["items"][0])
        self.assertIn("carbs_allocation", data["items"][0])
        self.assertIn("fat_allocation", data["items"][0])
        detail = self.client.get(f"/api/v1/food-picker-options/{personal.id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["data"]["id"], personal.id)
        self.assertEqual(self.client.get(f"/api/v1/food-picker-options/{private.id}").status_code, 404)

    def test_personal_library_endpoints_match_the_four_web_library_entities(self):
        food = Food.objects.create(name="Avena personal", protein=13, carbs=68, fat=7, created_by=self.user)
        meal = Meal.objects.create(
            name="Desayuno reutilizable",
            created_by=self.user,
            is_draft=False,
            protein_cached=13,
            carbs_cached=68,
            fat_cached=7,
            total_kcal_cached=387,
            alloc_protein_cached=13.4,
            alloc_carbs_cached=70.3,
            alloc_fat_cached=16.3,
        )
        MealFood.objects.create(meal=meal, food=food, quantity=100)
        dailyplan = DailyPlan.objects.create(
            name="Día de entrenamiento",
            created_by=self.user,
            is_draft=False,
            summary_cache={
                "totals": {
                    "protein": 13,
                    "carbs": 68,
                    "fat": 7,
                    "total_kcal": 387,
                    "alloc": {"protein": 13.4, "carbs": 70.3, "fat": 16.3},
                }
            },
        )
        embedded_meal = Meal.objects.create(
            name="Instancia del plan",
            created_by=self.user,
            is_draft=False,
            protein_cached=13,
            carbs_cached=68,
            fat_cached=7,
            kcal_protein_cached=52,
            kcal_carbs_cached=272,
            kcal_fat_cached=63,
            total_kcal_cached=387,
            alloc_protein_cached=13.4,
            alloc_carbs_cached=70.3,
            alloc_fat_cached=16.3,
        )
        MealFood.objects.create(meal=embedded_meal, food=food, quantity=100)
        DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=embedded_meal, hour="08:00")
        program = Program.objects.create(
            name="Programa base",
            created_by=self.user,
            duration_weeks=1,
            summary_cache={
                "filled_days_count": 1,
                "program_totals": {
                    "protein": 13,
                    "carbs": 68,
                    "fat": 7,
                    "kcal_protein": 52,
                    "kcal_carbs": 272,
                    "kcal_fat": 63,
                },
            },
        )
        ProgramDay.objects.create(program=program, dailyplan=dailyplan, week_number=1, day_number=1)
        other = User.objects.create_user(username="private-library-owner")
        Food.objects.create(name="Alimento ajeno", protein=1, carbs=1, fat=1, created_by=other)

        expectations = {
            "/api/v1/library/foods": ("food", "Avena personal"),
            "/api/v1/library/meals": ("meal", "Desayuno reutilizable"),
            "/api/v1/library/daily-plans": ("dailyPlan", "Día de entrenamiento"),
            "/api/v1/library/programs": ("program", "Programa base"),
        }
        for path, (entity, name) in expectations.items():
            with self.subTest(path=path):
                response = self.client.get(path, {"search": name.split()[0]})
                self.assertEqual(response.status_code, 200)
                data = response.json()["data"]
                self.assertEqual(data["total"], 1)
                self.assertEqual(data["items"][0]["entity"], entity)
                self.assertEqual(data["items"][0]["name"], name)
                self.assertIn("nutrition", data["items"][0])
                self.assertIn("panel", data["items"][0])

        meal_item = self.client.get("/api/v1/library/meals").json()["data"]["items"][0]
        self.assertEqual(meal_item["panel"]["kind"], "foods")
        self.assertEqual(meal_item["panel"]["foods"][0]["name"], "Avena personal")
        self.assertEqual(meal_item["panel"]["foods"][0]["quantity"], 100.0)
        self.assertIn("calorie_share", meal_item["panel"]["foods"][0])
        self.assertIn("calorie_distribution", meal_item["panel"]["foods"][0])
        self.assertAlmostEqual(sum(meal_item["panel"]["foods"][0]["calorie_distribution"].values()), 100, places=1)

        dailyplan_item = self.client.get("/api/v1/library/daily-plans").json()["data"]["items"][0]
        self.assertEqual(dailyplan_item["panel"]["kind"], "meals")
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["name"], "Instancia del plan")
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["detail_id"], embedded_meal.id)
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["foods"][0]["name"], "Avena personal")
        self.assertIn("calories", dailyplan_item["panel"]["meals"][0]["foods"][0])
        self.assertIn("calorie_distribution", dailyplan_item["panel"]["meals"][0]["foods"][0])
        self.assertIn("protein_allocation", dailyplan_item["panel"]["meals"][0]["foods"][0])
        self.assertIn("calorie_share", dailyplan_item["panel"]["meals"][0])
        self.assertIn("calorie_distribution", dailyplan_item["panel"]["meals"][0])
        self.assertEqual(dailyplan_item["panel"]["meals"][0]["protein_per_kilogram"], 0.2)

        program_item = self.client.get("/api/v1/library/programs").json()["data"]["items"][0]
        self.assertEqual(program_item["panel"]["kind"], "weeks")
        self.assertTrue(program_item["can_calendarize"])
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["plan_name"], "Día de entrenamiento")
        self.assertEqual(program_item["panel"]["weeks"][0]["filled_days_count"], 1)
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["nutrition"]["calories"], 387.0)
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["meals"][0]["name"], "Instancia del plan")
        self.assertEqual(program_item["panel"]["weeks"][0]["days"][0]["meals"][0]["foods"][0]["name"], "Avena personal")
        self.assertEqual(program_item["panel"]["weeks"][0]["foods"][0]["name"], "Avena personal")
        self.assertEqual(program_item["indicators"][1]["icon"], "dailyPlan")
        self.assertEqual(program_item["indicators"][2]["icon"], "food")
        self.assertIn("calorie_share", program_item["panel"]["weeks"][0])
        self.assertIn("calorie_distribution", program_item["panel"]["weeks"][0])

        detail_expectations = {
            f"/api/v1/library/foods/{food.id}": "food",
            f"/api/v1/library/meals/{meal.id}": "meal",
            f"/api/v1/library/daily-plans/{dailyplan.id}": "dailyPlan",
            f"/api/v1/library/programs/{program.id}": "program",
        }
        for path, entity in detail_expectations.items():
            with self.subTest(detail=path):
                detail = self.client.get(path)
                self.assertEqual(detail.status_code, 200)
                detail_data = detail.json()["data"]
                self.assertEqual(detail_data["entity"], entity)
                self.assertEqual(detail_data["creator"], self.user.get_full_name().strip() or self.user.username)
                if entity == "dailyPlan":
                    meal_data = detail_data["panel"]["meals"][0]
                    self.assertEqual(meal_data["foods"][0]["name"], "Avena personal")
                    self.assertIn("calories", meal_data["foods"][0])
                    self.assertIn("calorie_distribution", meal_data["foods"][0])
                    self.assertEqual(meal_data["protein_per_kilogram"], 0.2)
                    aggregated_food = detail_data["panel"]["foods"][0]
                    self.assertEqual(aggregated_food["name"], "Avena personal")
                    self.assertEqual(aggregated_food["quantity"], 100.0)
                    self.assertIn("calorie_share", aggregated_food)

                    self.assertIn("protein_allocation", aggregated_food)
                if entity == "program":
                    week_data = detail_data["panel"]["weeks"][0]
                    self.assertEqual(week_data["filled_days_count"], 1)
                    self.assertEqual(week_data["average_calories"], 55.3)
                    self.assertEqual(week_data["days"][0]["dailyplan_id"], dailyplan.id)
                    self.assertEqual(week_data["days"][0]["nutrition"]["calories"], 387.0)
                    self.assertEqual(week_data["days"][0]["meals"][0]["name"], "Instancia del plan")
                    self.assertEqual(week_data["days"][0]["meals"][0]["protein_per_kilogram"], 0.2)
                    self.assertEqual(week_data["foods"][0]["name"], "Avena personal")

        embedded_meal_detail = self.client.get(f"/api/v1/library/meals/{embedded_meal.id}")
        self.assertEqual(embedded_meal_detail.status_code, 200)
        self.assertEqual(embedded_meal_detail.json()["data"]["name"], "Instancia del plan")

        dailyplan.source = DailyPlan.SOURCE_PROGRAM
        dailyplan.save(update_fields=["source"])
        program_dailyplan_detail = self.client.get(f"/api/v1/library/daily-plans/{dailyplan.id}")
        self.assertEqual(program_dailyplan_detail.status_code, 200)
        self.assertEqual(program_dailyplan_detail.json()["data"]["id"], dailyplan.id)
        private_program_dailyplan = DailyPlan.objects.create(
            name="Plan de programa ajeno", created_by=other, source=DailyPlan.SOURCE_PROGRAM, is_draft=False
        )
        self.assertEqual(
            self.client.get(f"/api/v1/library/daily-plans/{private_program_dailyplan.id}").status_code, 404
        )

        missing = self.client.get("/api/v1/library/meals/999999")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json()["error"]["code"], "library_item_not_found")

    def test_mobile_can_create_and_complete_each_library_entity(self):
        food_response = self.client.post(
            "/api/v1/library/foods",
            data={"name": "Yogur natural", "protein": 4.2, "carbs": 5.1, "fat": 2.3},
            content_type="application/json",
        )
        self.assertEqual(food_response.status_code, 200)
        food = food_response.json()["data"]
        self.assertEqual(food["entity"], "food")
        self.assertFalse(food["is_draft"])

        meal_response = self.client.post(
            "/api/v1/library/meals", data={"name": "Desayuno nuevo"}, content_type="application/json"
        )
        dailyplan_response = self.client.post(
            "/api/v1/library/daily-plans", data={"name": "Día nuevo"}, content_type="application/json"
        )
        program_response = self.client.post(
            "/api/v1/library/programs", data={"name": "Programa nuevo"}, content_type="application/json"
        )
        for response, entity in (
            (meal_response, "meal"),
            (dailyplan_response, "dailyPlan"),
            (program_response, "program"),
        ):
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["data"]["entity"], entity)
            self.assertTrue(response.json()["data"]["is_draft"])

        meal_id = meal_response.json()["data"]["id"]
        dailyplan_id = dailyplan_response.json()["data"]["id"]
        program_id = program_response.json()["data"]["id"]
        self.assertEqual(self.client.get("/api/v1/library/meals").json()["data"]["total"], 0)
        draft_meals = self.client.get("/api/v1/library/meals", {"include_drafts": True}).json()["data"]
        self.assertEqual(draft_meals["total"], 1)
        self.assertEqual(draft_meals["items"][0]["indicators"][-1]["value"], "Borrador")
        self.assertEqual(self.client.get(f"/api/v1/library/meals/{meal_id}").status_code, 200)
        self.assertEqual(self.client.get(f"/api/v1/library/daily-plans/{dailyplan_id}").status_code, 200)

        add_food = self.client.post(
            f"/api/v1/library/meals/{meal_id}/food-picker/commit",
            data={"food_id": food["id"], "quantity": 150},
            content_type="application/json",
        )
        self.assertEqual(add_food.status_code, 200)
        self.assertFalse(Meal.objects.get(pk=meal_id).is_draft)

        add_meal = self.client.post(
            f"/api/v1/library/daily-plans/{dailyplan_id}/meal-picker/commit",
            data={"meal_id": meal_id, "hour": "08:30", "note": ""},
            content_type="application/json",
        )
        self.assertEqual(add_meal.status_code, 200)
        self.assertFalse(DailyPlan.objects.get(pk=dailyplan_id).is_draft)

        assign_dailyplan = self.client.post(
            f"/api/v1/library/programs/{program_id}/daily-plan-picker/commit",
            data={
                "dailyplan_id": dailyplan_id,
                "week_number": 1,
                "day_numbers": [1],
                "confirm_replacements": False,
            },
            content_type="application/json",
        )
        self.assertEqual(assign_dailyplan.status_code, 200)
        self.assertFalse(Program.objects.get(pk=program_id).is_draft)

    def test_library_creation_rejects_blank_names_and_out_of_range_macros(self):
        blank = self.client.post("/api/v1/library/meals", data={"name": "   "}, content_type="application/json")
        invalid_macro = self.client.post(
            "/api/v1/library/foods",
            data={"name": "Inválido", "protein": 101, "carbs": 0, "fat": 0},
            content_type="application/json",
        )
        self.assertEqual(blank.status_code, 422)
        self.assertEqual(blank.json()["error"]["code"], "library_name_required")
        self.assertEqual(invalid_macro.status_code, 422)
        self.assertEqual(invalid_macro.json()["error"]["code"], "request_validation_failed")

    def test_mobile_composition_pickers_preview_and_commit_the_four_web_flows(self):
        food = Food.objects.create(
            name="Avena para picker",
            protein=10,
            carbs=60,
            fat=5,
            created_by=self.user,
        )
        target_meal = Meal.objects.create(
            name="Comida destino",
            created_by=self.user,
            is_draft=False,
            protein_cached=0,
            carbs_cached=0,
            fat_cached=0,
            total_kcal_cached=0,
        )

        food_preview = self.client.post(
            f"/api/v1/library/meals/{target_meal.id}/food-picker/preview",
            data={"food_id": food.id, "quantity": 50},
            content_type="application/json",
        )
        self.assertEqual(food_preview.status_code, 200)
        self.assertEqual(food_preview.json()["data"]["selection"]["quantity"], 50.0)
        self.assertEqual(food_preview.json()["data"]["impacts"][0]["after"]["protein"]["grams"], 5.0)

        food_commit = self.client.post(
            f"/api/v1/library/meals/{target_meal.id}/food-picker/commit",
            data={"food_id": food.id, "quantity": 50},
            content_type="application/json",
        )
        self.assertEqual(food_commit.status_code, 200)
        self.assertTrue(MealFood.objects.filter(meal=target_meal, food=food, quantity=50).exists())

        source_meal = Meal.objects.create(
            name="Comida reutilizable",
            created_by=self.user,
            is_draft=False,
            protein_cached=10,
            carbs_cached=60,
            fat_cached=5,
            total_kcal_cached=325,
        )
        MealFood.objects.create(meal=source_meal, food=food, quantity=100)
        target_dailyplan = DailyPlan.objects.create(
            name="Plan destino",
            created_by=self.user,
            is_draft=False,
        )
        meal_payload = {"meal_id": source_meal.id, "hour": "08:30:00", "note": "Antes de entrenar"}
        meal_preview = self.client.post(
            f"/api/v1/library/daily-plans/{target_dailyplan.id}/meal-picker/preview",
            data=meal_payload,
            content_type="application/json",
        )
        self.assertEqual(meal_preview.status_code, 200)
        self.assertEqual(meal_preview.json()["data"]["selection"]["hour"], "08:30")
        meal_commit = self.client.post(
            f"/api/v1/library/daily-plans/{target_dailyplan.id}/meal-picker/commit",
            data=meal_payload,
            content_type="application/json",
        )
        self.assertEqual(meal_commit.status_code, 200)
        slot = DailyPlanMeal.objects.get(dailyplan=target_dailyplan)
        self.assertEqual(str(slot.hour), "08:30:00")
        self.assertEqual(slot.note, "Antes de entrenar")
        self.assertNotEqual(slot.meal_id, source_meal.id)

        replacement_meal = Meal.objects.create(
            name="Comida de reemplazo",
            created_by=self.user,
            is_draft=False,
            protein_cached=20,
            carbs_cached=30,
            fat_cached=10,
            total_kcal_cached=290,
        )
        MealFood.objects.create(meal=replacement_meal, food=food, quantity=80)
        replacement_payload = {
            "meal_id": replacement_meal.id,
            "dailyplan_meal_id": slot.id,
            "hour": "09:00:00",
            "note": "Reemplazada",
        }
        replacement_preview = self.client.post(
            f"/api/v1/library/daily-plans/{target_dailyplan.id}/meal-picker/preview",
            data=replacement_payload,
            content_type="application/json",
        )
        self.assertEqual(replacement_preview.status_code, 200)
        self.assertIn("reemplazar", replacement_preview.json()["data"]["impacts"][0]["label"].lower())
        replacement_commit = self.client.post(
            f"/api/v1/library/daily-plans/{target_dailyplan.id}/meal-picker/commit",
            data=replacement_payload,
            content_type="application/json",
        )
        self.assertEqual(replacement_commit.status_code, 200)
        slot.refresh_from_db()
        self.assertEqual(slot.id, replacement_commit.json()["data"]["created_id"])
        self.assertEqual(slot.meal.name, "Comida de reemplazo")
        self.assertEqual(DailyPlanMeal.objects.filter(dailyplan=target_dailyplan).count(), 1)

        source_dailyplan = DailyPlan.objects.create(
            name="Plan reutilizable",
            created_by=self.user,
            is_draft=False,
        )
        source_dailyplan_meal = Meal.objects.create(
            name="Comida del plan reutilizable",
            created_by=self.user,
            is_draft=False,
            protein_cached=10,
            carbs_cached=60,
            fat_cached=5,
            total_kcal_cached=325,
        )
        MealFood.objects.create(meal=source_dailyplan_meal, food=food, quantity=100)
        DailyPlanMeal.objects.create(dailyplan=source_dailyplan, meal=source_dailyplan_meal, hour="13:00")
        program = Program.objects.create(name="Programa destino", created_by=self.user, duration_weeks=1)
        occupied_dailyplan = DailyPlan.objects.create(
            name="Plan ocupado",
            created_by=self.user,
            is_draft=False,
            source=DailyPlan.SOURCE_PROGRAM,
        )
        ProgramDay.objects.create(program=program, dailyplan=occupied_dailyplan, week_number=1, day_number=1)
        program_payload = {
            "dailyplan_id": source_dailyplan.id,
            "week_number": 1,
            "day_numbers": [1, 2],
        }
        program_preview = self.client.post(
            f"/api/v1/library/programs/{program.id}/daily-plan-picker/preview",
            data=program_payload,
            content_type="application/json",
        )
        self.assertEqual(program_preview.status_code, 200)
        self.assertEqual(program_preview.json()["data"]["replacements"], ["Lunes"])
        self.assertEqual(program_preview.json()["data"]["impacts"], [])

        unconfirmed = self.client.post(
            f"/api/v1/library/programs/{program.id}/daily-plan-picker/commit",
            data=program_payload,
            content_type="application/json",
        )
        self.assertEqual(unconfirmed.status_code, 409)
        self.assertEqual(unconfirmed.json()["error"]["code"], "picker_replacement_confirmation_required")
        program_payload["confirm_replacements"] = True
        program_commit = self.client.post(
            f"/api/v1/library/programs/{program.id}/daily-plan-picker/commit",
            data=program_payload,
            content_type="application/json",
        )
        self.assertEqual(program_commit.status_code, 200)
        self.assertEqual(ProgramDay.objects.filter(program=program, week_number=1).count(), 2)
        self.assertTrue(
            all(
                row.dailyplan.source == DailyPlan.SOURCE_PROGRAM
                for row in ProgramDay.objects.filter(program=program).select_related("dailyplan")
            )
        )

        week_preview = self.client.post(f"/api/v1/library/programs/{program.id}/week-picker/preview")
        self.assertEqual(week_preview.status_code, 200)
        self.assertEqual(week_preview.json()["data"]["selection"]["name"], "Semana 2")
        week_commit = self.client.post(
            f"/api/v1/library/programs/{program.id}/week-picker/commit?expected_week_number=2",
        )
        self.assertEqual(week_commit.status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.normalized_duration_weeks, 2)
        repeated_commit = self.client.post(
            f"/api/v1/library/programs/{program.id}/week-picker/commit?expected_week_number=2",
        )
        self.assertEqual(repeated_commit.status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.normalized_duration_weeks, 2)

    def test_mobile_comparison_edit_panels_mutate_owned_compositions(self):
        first_food = Food.objects.create(name="Primer alimento", protein=10, carbs=20, fat=3, created_by=self.user)
        second_food = Food.objects.create(name="Segundo alimento", protein=5, carbs=8, fat=2, created_by=self.user)
        meal = Meal.objects.create(name="Comida editable", created_by=self.user, is_draft=False)
        first_relation = MealFood.objects.create(meal=meal, food=first_food, quantity=100, order=1)
        second_relation = MealFood.objects.create(meal=meal, food=second_food, quantity=50, order=2)

        detail = self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]
        self.assertEqual(detail["panel"]["foods"][0]["relation_id"], first_relation.id)
        updated = self.client.patch(
            f"/api/v1/library/meals/{meal.id}/foods/{first_relation.id}",
            data={"quantity": 75},
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200)
        first_relation.refresh_from_db()
        self.assertEqual(float(first_relation.quantity), 75)
        reordered = self.client.put(
            f"/api/v1/library/meals/{meal.id}/foods/order",
            data={"ordered_ids": [second_relation.id, first_relation.id]},
            content_type="application/json",
        )
        self.assertEqual(reordered.status_code, 200)
        self.assertEqual(
            list(meal.meal_food_set.order_by("order").values_list("id", flat=True)),
            [second_relation.id, first_relation.id],
        )
        deleted = self.client.delete(f"/api/v1/library/meals/{meal.id}/foods/{first_relation.id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(MealFood.objects.filter(pk=first_relation.id).exists())

        source_one = Meal.objects.create(name="Fuente uno", created_by=self.user, is_draft=False)
        source_two = Meal.objects.create(name="Fuente dos", created_by=self.user, is_draft=False)
        dailyplan = DailyPlan.objects.create(name="Plan editable", created_by=self.user, is_draft=False)
        slot_one = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=source_one, order=1, hour="08:00")
        slot_two = DailyPlanMeal.objects.create(dailyplan=dailyplan, meal=source_two, order=2, hour="13:00")
        plan_detail = self.client.get(f"/api/v1/library/daily-plans/{dailyplan.id}").json()["data"]
        self.assertEqual(plan_detail["panel"]["meals"][0]["relation_id"], slot_one.id)
        scheduled = self.client.patch(
            f"/api/v1/library/daily-plans/{dailyplan.id}/meals/{slot_one.id}",
            data={"hour": "09:15:00", "note": "Después de entrenar"},
            content_type="application/json",
        )
        self.assertEqual(scheduled.status_code, 200)
        slot_one.refresh_from_db()
        self.assertEqual(str(slot_one.hour), "09:15:00")
        self.assertEqual(slot_one.note, "Después de entrenar")
        time_only = self.client.patch(
            f"/api/v1/library/daily-plans/{dailyplan.id}/meals/{slot_one.id}",
            data={"hour": "10:20:00"},
            content_type="application/json",
        )
        self.assertEqual(time_only.status_code, 200)
        slot_one.refresh_from_db()
        self.assertEqual(str(slot_one.hour), "10:20:00")
        self.assertEqual(slot_one.note, "Después de entrenar")
        plan_reordered = self.client.put(
            f"/api/v1/library/daily-plans/{dailyplan.id}/meals/order",
            data={"ordered_ids": [slot_two.id, slot_one.id]},
            content_type="application/json",
        )
        self.assertEqual(plan_reordered.status_code, 200)
        self.assertEqual(
            list(dailyplan.dailyplan_meals.order_by("order").values_list("id", flat=True)), [slot_two.id, slot_one.id]
        )
        self.assertEqual(
            self.client.delete(f"/api/v1/library/daily-plans/{dailyplan.id}/meals/{slot_two.id}").status_code, 200
        )

        program = Program.objects.create(name="Programa editable", created_by=self.user, duration_weeks=2)
        snapshot = DailyPlan.objects.create(
            name="Día editable", created_by=self.user, is_draft=False, source=DailyPlan.SOURCE_PROGRAM
        )
        ProgramDay.objects.create(program=program, dailyplan=snapshot, week_number=1, day_number=1)
        self.assertEqual(
            self.client.put(
                f"/api/v1/library/programs/{program.id}/weeks/order",
                data={"ordered_ids": [2, 1]},
                content_type="application/json",
            ).status_code,
            200,
        )
        occupied = ProgramDay.objects.filter(program=program).first()
        self.assertIsNotNone(occupied)
        self.assertEqual(
            self.client.delete(
                f"/api/v1/library/programs/{program.id}/weeks/{occupied.week_number}/days/{occupied.day_number}"
            ).status_code,
            200,
        )
        self.assertFalse(ProgramDay.objects.filter(pk=occupied.id).exists())
        self.assertEqual(self.client.post(f"/api/v1/library/programs/{program.id}/weeks/1/duplicate").status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.normalized_duration_weeks, 3)
        self.assertEqual(self.client.delete(f"/api/v1/library/programs/{program.id}/weeks/3").status_code, 200)
        program.refresh_from_db()
        self.assertEqual(program.normalized_duration_weeks, 2)

    def test_mobile_composition_pickers_enforce_ownership_and_write_scope(self):
        food = Food.objects.create(name="Alimento permitido", protein=5, carbs=10, fat=2, created_by=self.user)
        meal = Meal.objects.create(name="Comida propia", created_by=self.user, is_draft=False)
        other = User.objects.create_user(username="picker-other-owner")
        foreign_meal = Meal.objects.create(name="Comida ajena", created_by=other, is_draft=False)

        foreign_target = self.client.post(
            f"/api/v1/library/meals/{foreign_meal.id}/food-picker/preview",
            data={"food_id": food.id, "quantity": 100},
            content_type="application/json",
        )
        self.assertEqual(foreign_target.status_code, 404)
        self.assertEqual(foreign_target.json()["error"]["code"], "picker_target_not_found")

        read_only_token = create_mcp_user_token(
            user=self.user,
            name="Read-only picker token",
            scopes=[MOBILE_SCOPE_READ],
            expires_at=timezone.now() + timedelta(minutes=15),
        ).raw_token
        read_only_client = Client(HTTP_AUTHORIZATION=f"Bearer {read_only_token}")
        preview = read_only_client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/preview",
            data={"food_id": food.id, "quantity": 100},
            content_type="application/json",
        )
        commit = read_only_client.post(
            f"/api/v1/library/meals/{meal.id}/food-picker/commit",
            data={"food_id": food.id, "quantity": 100},
            content_type="application/json",
        )
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(commit.status_code, 403)
        self.assertEqual(commit.json()["error"]["code"], "mobile_scope_missing")
        self.assertFalse(MealFood.objects.filter(meal=meal).exists())

    def test_library_list_actions_reorder_and_bulk_delete_only_owned_items(self):
        first = Food.objects.create(name="Primero", protein=1, carbs=1, fat=1, created_by=self.user, list_order=0)
        second = Food.objects.create(name="Segundo", protein=1, carbs=1, fat=1, created_by=self.user, list_order=1)
        other = User.objects.create_user(username="other-library-actions")
        foreign = Food.objects.create(name="Ajeno", protein=1, carbs=1, fat=1, created_by=other)

        reordered = self.client.put(
            "/api/v1/library/foods/order",
            data={"ordered_ids": [second.id, first.id]},
            content_type="application/json",
        )
        self.assertEqual(reordered.status_code, 200)
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual((second.list_order, first.list_order), (0, 1))

        rejected = self.client.put(
            "/api/v1/library/foods/order",
            data={"ordered_ids": [first.id, foreign.id]},
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)

        deleted = self.client.post(
            "/api/v1/library/foods/bulk-delete",
            data={"item_ids": [first.id, second.id]},
            content_type="application/json",
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(set(deleted.json()["data"]["affected_ids"]), {first.id, second.id})
        self.assertFalse(Food.objects.filter(id__in=[first.id, second.id], is_active=True).exists())
        self.assertTrue(Food.objects.filter(pk=foreign.id, is_active=True).exists())

    def test_library_list_actions_require_write_scope(self):
        food = Food.objects.create(name="Solo lectura", protein=1, carbs=1, fat=1, created_by=self.user)
        read_only = create_mcp_user_token(
            user=self.user,
            name="Read-only library token",
            scopes=[MOBILE_SCOPE_READ],
            expires_at=timezone.now() + timedelta(minutes=15),
            device_session=self.device_session,
        )
        client = Client(HTTP_AUTHORIZATION=f"Bearer {read_only.raw_token}")
        response = client.put(
            "/api/v1/library/foods/order",
            data={"ordered_ids": [food.id]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "mobile_scope_missing")
        create_response = client.post(
            "/api/v1/library/foods",
            data={"name": "No autorizado", "protein": 1, "carbs": 1, "fat": 1},
            content_type="application/json",
        )
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(create_response.json()["error"]["code"], "mobile_scope_missing")
        self.assertFalse(Food.objects.filter(name="No autorizado").exists())

    def test_library_actions_match_web_placement_and_execute_through_the_mobile_api(self):
        food = Food.objects.create(name="Yogur natural", protein=10, carbs=4, fat=3, created_by=self.user)
        meal = Meal.objects.create(name="Colación", created_by=self.user, is_draft=False)

        food_list_item = self.client.get("/api/v1/library/foods").json()["data"]["items"][0]
        food_detail = self.client.get(f"/api/v1/library/foods/{food.id}").json()["data"]
        meal_list_item = self.client.get("/api/v1/library/meals").json()["data"]["items"][0]
        meal_detail = self.client.get(f"/api/v1/library/meals/{meal.id}").json()["data"]

        self.assertEqual(food_list_item["actions"], [])
        self.assertEqual([action["key"] for action in food_detail["actions"]], ["share", "delete"])
        self.assertEqual([action["key"] for action in meal_list_item["actions"]], ["duplicate", "delete"])
        self.assertEqual(
            [action["key"] for action in meal_detail["actions"]],
            ["rename", "duplicate", "share", "delete"],
        )

        renamed = self.client.post(
            f"/api/v1/library/meals/{meal.id}/actions",
            data={"action": "rename", "name": "Colación PM"},
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200)
        meal.refresh_from_db()
        self.assertEqual(meal.name, "Colación PM")

        duplicated = self.client.post(
            f"/api/v1/library/meals/{meal.id}/actions",
            data={"action": "duplicate"},
            content_type="application/json",
        )
        self.assertEqual(duplicated.status_code, 200)
        duplicate_id = duplicated.json()["data"]["item_id"]
        self.assertTrue(Meal.objects.filter(pk=duplicate_id, name="Colación PM (Copia)").exists())

        deleted = self.client.post(
            f"/api/v1/library/meals/{duplicate_id}/actions",
            data={"action": "delete"},
            content_type="application/json",
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(Meal.objects.filter(pk=duplicate_id).exists())

        with patch(
            "mobile_api.library_actions.deliver_share_invitation",
            return_value=SimpleNamespace(sent=False, reason="delivery_disabled"),
        ):
            shared = self.client.post(
                f"/api/v1/library/foods/{food.id}/actions",
                data={
                    "action": "share",
                    "recipient_email": "friend@example.com",
                    "subject": "Un alimento para ti",
                    "message": "Revísalo cuando puedas.",
                },
                content_type="application/json",
            )
        self.assertEqual(shared.status_code, 200)
        self.assertTrue(FoodShare.objects.filter(food=food, recipient_email="friend@example.com").exists())

    def test_library_actions_reject_items_owned_by_another_user(self):
        other = User.objects.create_user(username="another-library-owner")
        meal = Meal.objects.create(name="Privada", created_by=other, is_draft=False)

        response = self.client.post(
            f"/api/v1/library/meals/{meal.id}/actions",
            data={"action": "delete"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "library_item_not_found")
        self.assertTrue(Meal.objects.filter(pk=meal.id).exists())
