from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase

from notas.application.queries.proposal_simulation_queries import (
    simulate_proposal_payload,
)
from notas.domain.models import Food, WeightLog


class ProposalSimulationQueryTests(TestCase):
    def program_payload(self, food_id):
        return {"intent": "create_program", "program": {"name": "Eight weeks", "duration_weeks": 8,
            "days": [{"week_number": week, "day_number": day, "dailyplan": {"name": "Day", "meals": [
                {"hour": "12:00", "note": "", "meal": {"name": "Meal", "foods": [{"food_id": food_id, "quantity": 100, "unit": "g"}]}}
            ]}} for week in range(1, 9) for day in range(1, 8)]}}

    def test_program_resolves_foods_once_for_all_56_days(self):
        with self.assertNumQueries(2):  # One visible food snapshot, one measured weight.
            result = simulate_proposal_payload(self.user, self.program_payload(self.chicken.pk)).as_dict()
        self.assertEqual(len(result["program"]["days"]), 56)
        self.assertAlmostEqual(result["program"]["days"][-1]["dailyplan"]["kpis"]["protein"], 31)

    def test_program_batch_preserves_visibility_and_does_not_cache_between_users(self):
        from django.http import Http404
        simulate_proposal_payload(self.user, self.program_payload(self.chicken.pk))
        with self.assertRaises(Http404):
            simulate_proposal_payload(self.other_user, self.program_payload(self.chicken.pk))
        with self.assertRaises(Http404):
            simulate_proposal_payload(self.user, self.program_payload(self.private_other_food.pk))

    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            password="pass123",
        )

        WeightLog.objects.create(
            user=self.user,
            date=date.today(),
            weight_kg=100,
        )

        self.chicken = Food.objects.create(
            name="Pechuga pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
        )

        self.rice = Food.objects.create(
            name="Arroz blanco",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=self.user,
        )

        self.system_banana = Food.objects.create(
            name="Plátano",
            protein=1.1,
            carbs=23,
            fat=0.3,
            created_by=None,
        )

        self.private_other_food = Food.objects.create(
            name="Private Other Food",
            protein=100,
            carbs=100,
            fat=100,
            created_by=self.other_user,
        )

    def test_simulate_create_meal_payload_returns_nutrition_projection(self):
        payload = {
            "intent": "create_meal",
            "meal": {
                "name": "Almuerzo IA",
                "foods": [
                    {
                        "food_id": self.chicken.id,
                        "quantity": 200,
                        "unit": "g",
                    },
                    {
                        "food_id": self.rice.id,
                        "quantity": 100,
                        "unit": "g",
                    },
                ],
            },
        }

        simulation = simulate_proposal_payload(
            user=self.user,
            payload=payload,
        )

        data = simulation.as_dict()

        self.assertEqual(data["intent"], "create_meal")
        self.assertIsNone(data["dailyplan"])
        self.assertEqual(data["meal"]["name"], "Almuerzo IA")
        self.assertEqual(len(data["meal"]["foods"]), 2)

        self.assertEqual(data["meal"]["foods"][0]["food_id"], self.chicken.id)
        self.assertEqual(data["meal"]["foods"][0]["food_name"], "Pechuga pollo")
        self.assertEqual(data["meal"]["foods"][0]["quantity"], 200.0)

        self.assertAlmostEqual(data["meal"]["kpis"]["protein"], 64.7)
        self.assertAlmostEqual(data["meal"]["kpis"]["carbs"], 28.0)
        self.assertAlmostEqual(data["meal"]["kpis"]["fat"], 7.5)
        self.assertAlmostEqual(data["meal"]["kpis"]["total_kcal"], 438.3)
        self.assertAlmostEqual(data["meal"]["kpis"]["ppk"], 0.647)

    def test_simulate_create_meal_payload_allows_system_food(self):
        payload = {
            "intent": "create_meal",
            "meal": {
                "name": "Snack IA",
                "foods": [
                    {
                        "food_id": self.system_banana.id,
                        "quantity": 100,
                    },
                ],
            },
        }

        simulation = simulate_proposal_payload(
            user=self.user,
            payload=payload,
        )

        data = simulation.as_dict()

        self.assertEqual(data["meal"]["foods"][0]["food_name"], "Plátano")
        self.assertAlmostEqual(data["meal"]["kpis"]["protein"], 1.1)
        self.assertAlmostEqual(data["meal"]["kpis"]["carbs"], 23.0)
        self.assertAlmostEqual(data["meal"]["kpis"]["fat"], 0.3)

    def test_simulate_create_meal_payload_rejects_unreadable_food(self):
        payload = {
            "intent": "create_meal",
            "meal": {
                "name": "Invalid Meal",
                "foods": [
                    {
                        "food_id": self.private_other_food.id,
                        "quantity": 100,
                    },
                ],
            },
        }

        with self.assertRaisesMessage(Exception, "No Food matches the given query."):
            simulate_proposal_payload(
                user=self.user,
                payload=payload,
            )

    def test_simulate_create_dailyplan_payload_returns_total_projection(self):
        payload = {
            "intent": "create_dailyplan",
            "dailyplan": {
                "name": "Día entrenamiento IA",
                "meals": [
                    {
                        "hour": "09:00",
                        "note": "Desayuno",
                        "meal": {
                            "name": "Desayuno IA",
                            "foods": [
                                {
                                    "food_id": self.system_banana.id,
                                    "quantity": 100,
                                },
                            ],
                        },
                    },
                    {
                        "hour": "14:30",
                        "note": "Almuerzo",
                        "meal": {
                            "name": "Almuerzo IA",
                            "foods": [
                                {
                                    "food_id": self.chicken.id,
                                    "quantity": 200,
                                },
                                {
                                    "food_id": self.rice.id,
                                    "quantity": 100,
                                },
                            ],
                        },
                    },
                ],
            },
        }

        simulation = simulate_proposal_payload(
            user=self.user,
            payload=payload,
        )

        data = simulation.as_dict()

        self.assertEqual(data["intent"], "create_dailyplan")
        self.assertIsNone(data["meal"])

        dailyplan = data["dailyplan"]

        self.assertEqual(dailyplan["name"], "Día entrenamiento IA")
        self.assertEqual(len(dailyplan["meals"]), 2)

        self.assertEqual(dailyplan["meals"][0]["hour"], "09:00")
        self.assertEqual(dailyplan["meals"][0]["note"], "Desayuno")
        self.assertEqual(dailyplan["meals"][0]["meal"]["name"], "Desayuno IA")

        self.assertEqual(dailyplan["meals"][1]["hour"], "14:30")
        self.assertEqual(dailyplan["meals"][1]["note"], "Almuerzo")
        self.assertEqual(dailyplan["meals"][1]["meal"]["name"], "Almuerzo IA")

        self.assertAlmostEqual(dailyplan["kpis"]["protein"], 65.8)
        self.assertAlmostEqual(dailyplan["kpis"]["carbs"], 51.0)
        self.assertAlmostEqual(dailyplan["kpis"]["fat"], 7.8)
        self.assertAlmostEqual(dailyplan["kpis"]["total_kcal"], 537.4)
        self.assertAlmostEqual(dailyplan["kpis"]["ppk"], 0.658)

    def test_simulate_payload_uses_contract_validation(self):
        payload = {
            "intent": "create_meal",
            "meal": {
                "name": "Invalid Meal",
                "foods": [
                    {
                        "food_id": self.chicken.id,
                        "quantity": 0,
                    },
                ],
            },
        }

        with self.assertRaisesMessage(
            ValueError,
            "proposed_food_item_quantity_must_be_positive",
        ):
            simulate_proposal_payload(
                user=self.user,
                payload=payload,
            )
