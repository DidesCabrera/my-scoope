from __future__ import annotations

import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from notas.application.ai_intake.nutrition_brief import NutritionBrief, serialize_brief
from notas.application.dto.proposal_payloads import CREATE_DAILYPLAN_INTENT
from notas.domain.models import Food, NutritionProposal


def json_post(client, url_name: str, payload: dict | None = None):
    return client.post(
        reverse(url_name),
        data=json.dumps(payload or {}),
        content_type="application/json",
    )


class AIToolsNutritionEngineEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="felipe", password="test")
        self.client.force_login(self.user)
        self._create_food_catalog()

    def _create_food_catalog(self):
        Food.objects.create(
            name="Pescado blanco",
            protein=22,
            carbs=0,
            fat=2,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="pescados",
            data_quality_score=90,
            default_portion_g=180,
            min_portion_g=90,
            max_portion_g=260,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="carnes",
            data_quality_score=95,
            default_portion_g=170,
            min_portion_g=90,
            max_portion_g=260,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Yogur griego natural",
            protein=10,
            carbs=4,
            fat=0.4,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="lácteos",
            data_quality_score=85,
            default_portion_g=170,
            min_portion_g=100,
            max_portion_g=250,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Arroz cocido",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="cereales",
            data_quality_score=90,
            default_portion_g=150,
            min_portion_g=45,
            max_portion_g=240,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Avena",
            protein=13,
            carbs=60,
            fat=7,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="cereales",
            data_quality_score=88,
            default_portion_g=60,
            min_portion_g=25,
            max_portion_g=120,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Palta",
            protein=2,
            carbs=9,
            fat=15,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="grasas",
            data_quality_score=80,
            default_portion_g=30,
            min_portion_g=10,
            max_portion_g=40,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Tomate",
            protein=1,
            carbs=4,
            fat=0.2,
            created_by=None,
            is_global=True,
            is_verified=True,
            food_group="verduras",
            data_quality_score=80,
            default_portion_g=100,
            min_portion_g=50,
            max_portion_g=180,
            portion_step_g=5,
        )

    def _brief_payload(self, **overrides):
        values = {
            "raw_prompt": "quiero bajar grasa, 4 comidas, simple",
            "goal": "fat_loss",
            "requested_entity": "daily_plan",
            "meals_per_day": 4,
            "weight_kg": 80,
            "height_cm": 175,
            "age_years": 30,
            "sex": "male",
            "activity_level": "moderate",
            "style_preferences": ["simple"],
            "excluded_foods": [],
        }
        values.update(overrides)
        return serialize_brief(NutritionBrief(**values))

    def test_create_nutrition_engine_dailyplan_proposal_endpoint_runs_engine(self):
        response = json_post(
            self.client,
            "ai_tools_create_nutrition_engine_dailyplan_proposal",
            {
                "nutrition_brief": self._brief_payload(),
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["ok"])
        proposal = data["data"]["proposal"]
        source_proposal = data["data"]["source_proposal"]

        self.assertEqual(proposal["source"], NutritionProposal.SOURCE_MCP)
        self.assertEqual(source_proposal["source"], NutritionProposal.SOURCE_MCP)
        self.assertEqual(proposal["proposed_payload"]["intent"], CREATE_DAILYPLAN_INTENT)
        self.assertEqual(
            data["data"]["engine_validation"]["kind"],
            "strict_dailyplan_nutrition_validation",
        )
        self.assertIn(
            data["data"]["engine_validation"]["status"],
            {"ok", "warning", "error"},
        )
        self.assertIsNone(data["data"]["iteration_trace"])
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 2)

    def test_iterate_nutrition_engine_dailyplan_proposal_endpoint_creates_traced_revision(self):
        create_response = json_post(
            self.client,
            "ai_tools_create_nutrition_engine_dailyplan_proposal",
            {
                "nutrition_brief": self._brief_payload(),
            },
        )
        previous_proposal_id = create_response.json()["data"]["proposal"]["id"]

        response = json_post(
            self.client,
            "ai_tools_iterate_nutrition_engine_dailyplan_proposal",
            {
                "previous_proposal_id": previous_proposal_id,
                "nutrition_brief": self._brief_payload(
                    raw_prompt="quiero bajar grasa, 4 comidas, simple, sin arroz",
                    excluded_foods=["arroz"],
                ),
                "user_message": "sin arroz",
            },
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data["ok"])
        proposal = data["data"]["proposal"]
        trace = data["data"]["iteration_trace"]

        self.assertEqual(proposal["source"], NutritionProposal.SOURCE_MCP)
        self.assertEqual(trace["previous_proposal_id"], previous_proposal_id)
        self.assertEqual(trace["user_message"], "sin arroz")
        self.assertIn("Evitar arroz", trace["command_labels"])
        self.assertEqual(
            proposal["iteration_trace"]["previous_proposal_id"],
            previous_proposal_id,
        )
        self.assertEqual(NutritionProposal.objects.filter(created_by=self.user).count(), 4)

    def test_create_nutrition_engine_dailyplan_proposal_requires_brief(self):
        response = json_post(
            self.client,
            "ai_tools_create_nutrition_engine_dailyplan_proposal",
            {},
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertFalse(data["ok"])
        self.assertEqual(
            data["error"]["code"],
            "missing_required_field:nutrition_brief",
        )
