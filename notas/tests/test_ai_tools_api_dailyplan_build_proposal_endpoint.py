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
class AIToolsAPIDailyPlanBuildProposalEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            password="pass123",
        )

        self.dailyplan = DailyPlan.objects.create(
            name="Día contexto",
            created_by=self.user,
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

    def test_create_validated_dailyplan_build_proposal_endpoint_requires_login(self):
        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_build_proposal",
            {},
        )

        self.assertEqual(response.status_code, 302)

    def test_create_validated_dailyplan_build_proposal_endpoint_creates_proposal(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_build_proposal",
            {
                "dailyplan_id": self.dailyplan.id,
                "title": "Propuesta MCP - Día entrenamiento IA",
                "summary": "DailyPlan propuesto desde API Adapter.",
                "targets": {
                    "protein": 190,
                    "total_kcal": 2800,
                },
                "proposed_payload": {
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
                                            "food_id": self.rice.id,
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
                                    ],
                                },
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
        self.assertEqual(proposal["proposed_payload"]["intent"], "create_dailyplan")

        simulation = proposal["validation_summary"]["simulation"]

        self.assertEqual(simulation["intent"], "create_dailyplan")
        self.assertIsNone(simulation["meal"])
        self.assertEqual(
            simulation["dailyplan"]["name"],
            "Día entrenamiento IA",
        )
        self.assertAlmostEqual(
            simulation["dailyplan"]["kpis"]["protein"],
            64.7,
        )
        self.assertAlmostEqual(
            simulation["dailyplan"]["kpis"]["total_kcal"],
            438.3,
        )

        self.assertEqual(Meal.objects.count(), 0)
        self.assertEqual(DailyPlan.objects.count(), 1)

    def test_create_validated_dailyplan_build_proposal_endpoint_requires_payload(self):
        self.client.force_login(self.user)

        response = json_post(
            self.client,
            "ai_tools_create_validated_dailyplan_build_proposal",
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