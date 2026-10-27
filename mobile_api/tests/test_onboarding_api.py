from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.ai_intake.onboarding_catalog_minutas import _candidate_payload
from notas.domain.models import (
    DailyPlan,
    DailyPlanCatalogEntry,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionPreferenceProfile,
    NutritionProposal,
    Profile,
)
from nutrition_solver.domain.models import MacroTarget


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIOnboardingV2Tests(AuthenticatedMobileAPITestCase):
    def test_personal_record_endpoints_update_without_restarting_onboarding(self):
        self.user.profile.onboarding_stage = Profile.ONBOARDING_STAGE_COMPLETED
        self.user.profile.save(update_fields=["onboarding_stage"])

        planning = self.client.patch("/api/v1/personal-records/planning", data={
            "goal": "maintenance", "activity_level": "moderate", "training_frequency": 2,
        }, content_type="application/json")
        self.assertEqual(planning.status_code, 200, planning.content)
        self.assertEqual(planning.json()["data"]["stage"], Profile.ONBOARDING_STAGE_COMPLETED)

        preferences = self.client.patch("/api/v1/personal-records/preferences", data={
            "dietary_pattern": "vegetarian", "allergies_or_intolerances": ["maní"], "avoided_foods": ["apio"],
        }, content_type="application/json")
        self.assertEqual(preferences.status_code, 200, preferences.content)
        stored = NutritionPreferenceProfile.objects.get(user=self.user).preferences
        self.assertEqual(stored["dietary_pattern"], "vegetarian")

        metrics = self.client.patch("/api/v1/personal-records/metrics", data={"weight_kg": 81.2}, content_type="application/json")
        self.assertEqual(metrics.status_code, 200, metrics.content)
        self.assertEqual(metrics.json()["data"]["weight_kg"], 81.2)
    def _create_minimal_food_catalog(self):
        foods = (
            ("Pechuga de pollo", 31, 0, 3, "carnes", "primary_protein", 160, 80, 300),
            ("Arroz cocido", 2.7, 28, 0.3, "cereales", "starch_or_carbohydrate", 220, 60, 350),
            ("Palta", 2, 9, 15, "grasas", "fat_source", 70, 10, 120),
            ("Tomate", 1, 4, 0.2, "verduras", "vegetable_or_fruit", 100, 50, 180),
        )
        for name, protein, carbs, fat, group, role, default, minimum, maximum in foods:
            Food.objects.create(
                name=name,
                protein=protein,
                carbs=carbs,
                fat=fat,
                created_by=None,
                is_global=True,
                is_verified=True,
                solver_enabled=True,
                visibility=Food.VISIBILITY_CORE,
                food_group=group,
                data_quality_score=90,
                default_portion_g=default,
                min_portion_g=minimum,
                max_portion_g=maximum,
                portion_step_g=5,
                solver_capabilities={
                    "schema_version": "solver_food_capabilities.v1",
                    "source": "test",
                    "values": {"functional_roles": [role], "allergens": ["none"],
                               "dietary_tags": ["omnivore"] if name == "Pechuga de pollo" else ["vegan"]},
                    "confidence": {"functional_roles": 95, "allergens": 95},
                },
            )

        owner = User.objects.create_user(username="myscoope_catalog", is_active=False)
        catalog_foods = list(Food.objects.order_by("id"))
        for index, meal_count in enumerate((3, 4), start=1):
            plan = DailyPlan.objects.create(
                created_by=owner, name=f"Minuta de prueba {index}",
                source=DailyPlan.SOURCE_SYSTEM, is_draft=False,
            )
            DailyPlanCatalogEntry.objects.create(
                dailyplan=plan, summary="Minuta curada", dietary_style="omnivore",
                is_published=True, sort_order=index,
            )
            for slot in range(meal_count):
                meal = Meal.objects.create(created_by=owner, name=f"Comida {index}-{slot}", is_draft=False)
                for order, food in enumerate(catalog_foods, start=1):
                    MealFood.objects.create(
                        meal=meal, food=food,
                        quantity={"Pechuga de pollo": 160, "Arroz cocido": 220, "Palta": 70, "Tomate": 100}[food.name],
                        order=order,
                    )
                DailyPlanMeal.objects.create(
                    dailyplan=plan, meal=meal, hour=time(8 + slot * 4), order=slot + 1,
                )

    def test_persists_profile_and_builds_two_catalog_minutas(self):
        self._create_minimal_food_catalog()
        analyzed = self.client.post(
            "/api/v1/onboarding/analyze",
            data={
                "birth_date": "1990-05-10",
                "sex": "male",
                "height_cm": 178,
                "weight_kg": 82.5,
                "goal": "fat_loss",
                "activity_level": "light",
                "training_frequency": 3,
                "dietary_pattern": "omnivore",
                "allergies_or_intolerances": ["mariscos"],
                "avoided_foods": ["cilantro", "aceitunas"],
            },
            content_type="application/json",
        )

        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        analyzed_data = analyzed.json()["data"]
        self.assertEqual(analyzed_data["stage"], Profile.ONBOARDING_STAGE_SUMMARY)
        self.assertGreater(analyzed_data["estimate"]["estimated_maintenance_kcal"], 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.nutrition_goal, "fat_loss")
        self.assertEqual(self.user.profile.activity_level, "light")
        self.assertEqual(self.user.profile.training_frequency, 3)
        self.assertEqual(self.user.weight_logs.count(), 1)
        preferences = NutritionPreferenceProfile.objects.get(user=self.user).preferences
        self.assertEqual(preferences["dietary_pattern"], "omnivore")
        self.assertEqual(preferences["allergies_or_intolerances"], ["mariscos"])
        self.assertEqual(preferences["avoided_foods"], ["cilantro", "aceitunas"])

        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 200, generated.content)
        items = generated.json()["data"]["items"]
        self.assertEqual(len(items), 2)
        self.assertTrue(all(item["status"] == NutritionProposal.STATUS_PENDING_REVIEW for item in items))
        self.assertEqual({item["dailyplan"]["name"] for item in items}, {"Minuta de prueba 1", "Minuta de prueba 2"})
        for item in items:
            proposal = NutritionProposal.objects.get(pk=item["id"])
            self.assertTrue(proposal.validation_summary["engine_validation"]["is_valid"])
            self.assertEqual(proposal.current_snapshot["source"], "onboarding_catalog_minuta.v1")
            self.assertTrue(proposal.current_snapshot["adjustments_g"])
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.onboarding_plan_proposal_ids, [item["id"] for item in items])
        self.assertEqual(self.user.profile.onboarding_plan_proposal_id, items[0]["id"])
        self.assertEqual(self.user.profile.onboarding_stage, Profile.ONBOARDING_STAGE_PLAN)

        resumed = self.client.get("/api/v1/onboarding/state")
        self.assertEqual(resumed.json()["data"]["proposal_ids"], [item["id"] for item in items])
        replay = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual([item["id"] for item in replay.json()["data"]["items"]], [item["id"] for item in items])

        accepted = self.client.post("/api/v1/onboarding/accept-plan", content_type="application/json")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual([item["status"] for item in accepted.json()["data"]["items"]], [NutritionProposal.STATUS_APPLIED] * 2)
        self.assertEqual(DailyPlan.objects.filter(created_by=self.user).count(), 2)
        self.assertEqual(
            set(DailyPlan.objects.filter(created_by=self.user).values_list("forked_from_id", flat=True)),
            set(DailyPlanCatalogEntry.objects.values_list("dailyplan_id", flat=True)),
        )
        self.assertEqual(self.client.post("/api/v1/onboarding/accept-plan", content_type="application/json").status_code, 200)
        self.assertEqual(DailyPlan.objects.filter(created_by=self.user).count(), 2)

        self.assertEqual(self.client.post("/api/v1/onboarding/complete", content_type="application/json").status_code, 409)
        local_today = date.fromisoformat(self.client.get("/api/v1/calendar?days=1").json()["data"]["local_date"])
        for offset, item in enumerate(accepted.json()["data"]["items"]):
            assigned = self.client.put(
                f"/api/v1/calendar/days/{local_today + timedelta(days=offset)}/plan",
                data={"dailyplan_id": item["applied_result"]["object_id"], "assignment_key": f"onboarding-first-{offset}"},
                content_type="application/json",
            )
            self.assertEqual(assigned.status_code, 200, assigned.content)

        completed = self.client.post("/api/v1/onboarding/complete", content_type="application/json")
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertTrue(completed.json()["data"]["onboarding_completed"])
        self.assertEqual(completed.json()["data"]["onboarding_version"], Profile.ONBOARDING_VERSION_NUTRITION_V2)

    def test_catalog_minutas_can_include_food_portions_measured_in_ml(self):
        self._create_minimal_food_catalog()
        oil = Food.objects.create(
            name="Aceite de oliva", protein=0, carbs=0, fat=100,
            portion_unit=Food.PORTION_UNIT_MILLILITERS,
            created_by=None, is_global=True, is_verified=True,
            solver_enabled=True, visibility=Food.VISIBILITY_CORE,
            food_group="grasas", data_quality_score=90,
            default_portion_g=8, min_portion_g=2, max_portion_g=20,
            portion_step_g=1,
            solver_capabilities={
                "schema_version": "solver_food_capabilities.v1", "source": "test",
                "values": {"functional_roles": ["fat_source"], "allergens": ["none"],
                           "dietary_tags": ["vegan"]},
                "confidence": {"functional_roles": 95, "allergens": 95},
            },
        )
        for plan in DailyPlan.objects.all():
            first_meal = plan.dailyplan_meals.order_by("order").first().meal
            MealFood.objects.create(meal=first_meal, food=oil, quantity=8, order=5)

        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "omnivore",
            "allergies_or_intolerances": [], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 200, generated.content)
        proposals = NutritionProposal.objects.filter(created_by=self.user)
        self.assertEqual(proposals.count(), 2)
        for proposal in proposals:
            portions = [food for meal in proposal.proposed_payload["dailyplan"]["meals"]
                        for food in meal["meal"]["foods"] if food["food_id"] == oil.id]
            self.assertEqual(len(portions), 1)
            self.assertEqual(portions[0]["unit"], "ml")
        accepted = self.client.post("/api/v1/onboarding/accept-plan", content_type="application/json")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual(len(accepted.json()["data"]["items"]), 2)

    def test_catalog_minutas_adjust_source_portions_above_food_maximum(self):
        self._create_minimal_food_catalog()
        rice = Food.objects.get(name="Arroz cocido")
        rice.max_portion_g = 200  # Published catalog meals use 220 g.
        rice.save(update_fields=["max_portion_g"])

        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "omnivore",
            "allergies_or_intolerances": [], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)

        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 200, generated.content)
        self.assertEqual(len(generated.json()["data"]["items"]), 2)
        for proposal in NutritionProposal.objects.filter(created_by=self.user):
            rice_portions = [food["quantity"] for meal in proposal.proposed_payload["dailyplan"]["meals"]
                             for food in meal["meal"]["foods"] if food["food_id"] == rice.id]
            self.assertTrue(rice_portions)
            self.assertTrue(all(quantity <= 200 for quantity in rice_portions))

    def test_catalog_minuta_respects_fractional_upper_bound_when_solving(self):
        self._create_minimal_food_catalog()
        oil = Food.objects.create(
            name="Aceite de oliva", protein=0, carbs=0, fat=100,
            created_by=None, is_global=True, portion_unit=Food.PORTION_UNIT_MILLILITERS,
            min_portion_g=2, max_portion_g=20,
        )
        entry = DailyPlanCatalogEntry.objects.order_by("sort_order").first()
        first_meal = entry.dailyplan.dailyplan_meals.order_by("order").first().meal
        MealFood.objects.create(meal=first_meal, food=oil, quantity=8, order=5)

        candidate = _candidate_payload(
            entry, pattern="omnivore", target=MacroTarget(kcal=2500, protein=145, carbs=245, fat=100),
            exclusions=set(), allergens=set(),
        )
        self.assertIsNotNone(candidate)
        payload = candidate[0]
        oil_portions = [food["quantity"] for meal in payload["dailyplan"]["meals"]
                        for food in meal["meal"]["foods"] if food["food_id"] == oil.id]
        self.assertEqual(len(oil_portions), 1)
        self.assertLessEqual(oil_portions[0], 17.6)  # 8 ml source × 2.2, rounded inward for the solver.

    def test_unknown_allergen_data_fails_without_partial_proposals(self):
        self._create_minimal_food_catalog()
        chicken = Food.objects.get(name="Pechuga de pollo")
        chicken.solver_capabilities = {"values": {}}
        chicken.save(update_fields=["solver_capabilities"])
        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "omnivore",
            "allergies_or_intolerances": ["mariscos"], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 422)
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 0)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.onboarding_stage, Profile.ONBOARDING_STAGE_SUMMARY)
        self.assertEqual(self.user.profile.onboarding_plan_proposal_ids, [])

    def test_dietary_style_is_checked_against_each_food(self):
        self._create_minimal_food_catalog()
        DailyPlanCatalogEntry.objects.update(dietary_style="vegetarian")
        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "vegetarian",
            "allergies_or_intolerances": [], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 422)
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 0)

    def test_one_compatible_catalog_plan_does_not_leave_a_partial_proposal(self):
        self._create_minimal_food_catalog()
        DailyPlanCatalogEntry.objects.filter(sort_order=2).update(is_published=False)
        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "omnivore",
            "allergies_or_intolerances": [], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 422)
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 0)

    def test_acceptance_is_atomic_if_the_second_proposal_is_no_longer_applicable(self):
        self._create_minimal_food_catalog()
        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "omnivore",
            "allergies_or_intolerances": [], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 200, generated.content)
        first_id, second_id = [item["id"] for item in generated.json()["data"]["items"]]
        NutritionProposal.objects.filter(pk=second_id).update(status=NutritionProposal.STATUS_CANCELLED)

        accepted = self.client.post("/api/v1/onboarding/accept-plan", content_type="application/json")
        self.assertEqual(accepted.status_code, 409)
        self.assertEqual(NutritionProposal.objects.get(pk=first_id).status, NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertEqual(DailyPlan.objects.filter(created_by=self.user).count(), 0)

    def test_calendarized_foods_sum_all_selected_days_and_follow_replacements(self):
        self._create_minimal_food_catalog()
        analyzed = self.client.post("/api/v1/onboarding/analyze", data={
            "birth_date": "1990-05-10", "sex": "male", "height_cm": 178,
            "weight_kg": 82.5, "goal": "fat_loss", "activity_level": "light",
            "training_frequency": 3, "dietary_pattern": "omnivore",
            "allergies_or_intolerances": [], "avoided_foods": [],
        }, content_type="application/json")
        self.assertEqual(analyzed.status_code, 200, analyzed.content)
        generated = self.client.post("/api/v1/onboarding/generate-plan", content_type="application/json")
        self.assertEqual(generated.status_code, 200, generated.content)
        accepted = self.client.post("/api/v1/onboarding/accept-plan", content_type="application/json")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        proposals = accepted.json()["data"]["items"]
        plan_ids = [item["applied_result"]["object_id"] for item in proposals]
        start = date.fromisoformat(self.client.get("/api/v1/calendar?days=1").json()["data"]["local_date"])

        for offset in range(4):
            assigned = self.client.put(
                f"/api/v1/calendar/days/{start + timedelta(days=offset)}/plan",
                data={"dailyplan_id": plan_ids[offset // 2], "assignment_key": f"onboarding-{offset}"},
                content_type="application/json",
            )
            self.assertEqual(assigned.status_code, 200, assigned.content)

        summary = self.client.get("/api/v1/onboarding/calendarized-foods")
        self.assertEqual(summary.status_code, 200, summary.content)
        data = summary.json()["data"]
        self.assertEqual(data["days_count"], 4)
        self.assertEqual([len(plan["dates"]) for plan in data["plans"]], [2, 2])
        rice = next(food for food in data["foods"] if food["name"] == "Arroz cocido")
        plan_rice = [next(food for food in plan["foods"] if food["name"] == "Arroz cocido") for plan in data["plans"]]
        self.assertAlmostEqual(rice["quantity"], sum(food["quantity"] for food in plan_rice))

        replaced = self.client.put(
            f"/api/v1/calendar/days/{start}/plan",
            data={"dailyplan_id": plan_ids[1], "assignment_key": "onboarding-replacement", "replace_existing": True},
            content_type="application/json",
        )
        self.assertEqual(replaced.status_code, 200, replaced.content)
        updated = self.client.get("/api/v1/onboarding/calendarized-foods").json()["data"]
        self.assertEqual(updated["days_count"], 4)
        self.assertEqual([len(plan["dates"]) for plan in updated["plans"]], [1, 3])
        updated_rice = next(food for food in updated["foods"] if food["name"] == "Arroz cocido")
        self.assertAlmostEqual(updated_rice["quantity"], sum(
            food["quantity"] for plan in updated["plans"] for food in plan["foods"] if food["name"] == "Arroz cocido"
        ))
