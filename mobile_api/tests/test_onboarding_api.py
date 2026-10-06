from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import DailyPlan, Food, NutritionPreferenceProfile, NutritionProposal, Profile


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
            ("Pechuga de pollo", 31, 0, 3, "carnes", "primary_protein", 170, 90, 260),
            ("Arroz cocido", 2.7, 28, 0.3, "cereales", "starch_or_carbohydrate", 150, 45, 240),
            ("Palta", 2, 9, 15, "grasas", "fat_source", 30, 10, 40),
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
                    "values": {"functional_roles": [role], "allergens": ["none"]},
                    "confidence": {"functional_roles": 95, "allergens": 95},
                },
            )

    def test_persists_one_profile_and_builds_the_first_daily_plan(self):
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
        proposal_id = generated.json()["data"]["id"]
        self.assertEqual(generated.json()["data"]["status"], NutritionProposal.STATUS_PENDING_REVIEW)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.onboarding_plan_proposal_id, proposal_id)
        self.assertEqual(self.user.profile.onboarding_stage, Profile.ONBOARDING_STAGE_PLAN)

        accepted = self.client.post("/api/v1/onboarding/accept-plan", content_type="application/json")
        self.assertEqual(accepted.status_code, 200, accepted.content)
        self.assertEqual(accepted.json()["data"]["status"], NutritionProposal.STATUS_APPLIED)
        self.assertEqual(DailyPlan.objects.filter(created_by=self.user).count(), 1)

        completed = self.client.post("/api/v1/onboarding/complete", content_type="application/json")
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertTrue(completed.json()["data"]["onboarding_completed"])
        self.assertEqual(completed.json()["data"]["onboarding_version"], Profile.ONBOARDING_VERSION_NUTRITION_V2)
