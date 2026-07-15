import json

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.domain.models import DailyPlan, Food, Meal


def json_post(client, url_name, payload):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload),
        content_type="application/json",
    )


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AIToolsAPIMealProposalEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Día entrenamiento",
            created_by=self.user,
        )

        self.food = Food.objects.create(
            name="Pechuga pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
        )

    def test_create_validated_meal_proposal_endpoint_requires_login(self):
        response = json_post(
            self.client,
            "ai_tools_create_validated_meal_proposal",
            {},
        )

        self.assertEqual(response.status_code, 302)

    def test_create_validated_meal_proposal_endpoint_creates_proposal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_meal_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Propuesta MCP - Almuerzo IA",
                "summary": "Comida propuesta desde API Adapter.",
                "targets": {
                    "protein": 60,
                },
                "proposed_payload": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [
                            {
                                "food_id": self.food.id,
                                "quantity": 200,
                            },
                        ],
                    },
                },
            },
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()

        self.assertTrue(data["ok"])
        self.assertIsNone(data["error"])

        proposal = data["data"]["proposal"]

        self.assertEqual(proposal["dailyplan_id"], self.dailyplan.id)
        self.assertEqual(proposal["status"], "pending_review")
        self.assertEqual(proposal["proposed_payload"]["intent"], "create_meal")
        simulation = proposal["validation_summary"]["simulation"]

        self.assertEqual(simulation["intent"], "create_meal")
        self.assertIsNone(simulation["dailyplan"])
        self.assertEqual(simulation["meal"]["name"], "Almuerzo IA")
        self.assertAlmostEqual(
            simulation["meal"]["kpis"]["protein"],
            62.0,
        )
        self.assertAlmostEqual(
            simulation["meal"]["kpis"]["total_kcal"],
            312.8,
        )
        self.assertEqual(Meal.objects.count(), 0)


    def test_create_validated_meal_proposal_endpoint_requires_payload(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_meal_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Invalid",
            },
        )

        self.assertEqual(response.status_code, 400)

        data = response.json()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "missing_required_field:proposed_payload",
        )