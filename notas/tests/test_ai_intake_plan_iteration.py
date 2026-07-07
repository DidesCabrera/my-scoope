from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.application.ai_intake.nutrition_brief import (
    NutritionBrief,
    apply_conversation_adjustments,
)
from notas.application.ai_intake.iteration_commands import (
    parse_dailyplan_iteration_commands,
)
from notas.application.ai_intake.plan_iteration import should_iterate_generated_plan
from notas.domain.models import AiNutritionChat, Food, NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class AiIntakePlanIterationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ai-iteration-user",
            email="ai-iteration@example.com",
            password="pass12345",
        )
        self.client.force_login(self.user)
        self._create_food_catalog()

    def _create_food_catalog(self):
        Food.objects.create(
            name="Pechuga de pollo",
            protein=31,
            carbs=0,
            fat=3.6,
            created_by=self.user,
            is_global=True,
            is_verified=True,
            data_quality_score=95,
            food_group="poultry proteins",
            default_portion_g=140,
            min_portion_g=80,
            max_portion_g=240,
            portion_step_g=10,
        )
        Food.objects.create(
            name="Arroz cocido",
            protein=2.7,
            carbs=28,
            fat=0.3,
            created_by=self.user,
            is_global=True,
            is_verified=True,
            data_quality_score=95,
            food_group="grains cereals",
            default_portion_g=160,
            min_portion_g=80,
            max_portion_g=320,
            portion_step_g=10,
        )
        Food.objects.create(
            name="Quinoa cocida",
            protein=4.4,
            carbs=21.3,
            fat=1.9,
            created_by=self.user,
            is_global=True,
            is_verified=True,
            data_quality_score=90,
            food_group="grains cereals",
            default_portion_g=160,
            min_portion_g=80,
            max_portion_g=320,
            portion_step_g=10,
        )
        Food.objects.create(
            name="Palta",
            protein=2,
            carbs=8.5,
            fat=15,
            created_by=self.user,
            is_global=True,
            is_verified=True,
            data_quality_score=90,
            food_group="fats oils",
            default_portion_g=50,
            min_portion_g=30,
            max_portion_g=100,
            portion_step_g=5,
        )
        Food.objects.create(
            name="Tomate",
            protein=0.9,
            carbs=3.9,
            fat=0.2,
            created_by=self.user,
            is_global=True,
            is_verified=True,
            data_quality_score=90,
            food_group="vegetables",
            default_portion_g=100,
            min_portion_g=50,
            max_portion_g=200,
            portion_step_g=10,
        )

    def _create_generated_plan_chat(self):
        prompt = (
            "Quiero bajar grasa para mí, 4 comidas, simple, peso 80 kg, "
            "mido 180 cm, tengo 30 años, hombre, actividad moderada"
        )
        self.client.post(reverse("ai_nutrition_intake"), {"action": "analyze_prompt", "prompt": prompt})
        self.client.post(reverse("ai_nutrition_intake"), {"action": "create_proposal"})
        return AiNutritionChat.objects.get(user=self.user)

    def test_adjustment_rules_change_meals_and_protein_target(self):
        brief = NutritionBrief(raw_prompt="", goal="fat_loss", meals_per_day=4, protein_target=140)

        fewer_meals = apply_conversation_adjustments(brief, "quiero menos comidas")
        higher_protein = apply_conversation_adjustments(brief, "sube proteína")

        self.assertEqual(fewer_meals.meals_per_day, 3)
        self.assertEqual(higher_protein.protein_target, 160)

    def test_iteration_command_parser_extracts_structured_feedback(self):
        command_set = parse_dailyplan_iteration_commands(
            "menos arroz, cambiar pescado por pollo y hacerlo más simple"
        )

        self.assertTrue(command_set.has_commands)
        self.assertIn("Evitar arroz", command_set.labels)
        self.assertIn("Cambiar pescado por pollo", command_set.labels)
        self.assertIn("Hacer la propuesta más simple", command_set.labels)
        self.assertEqual(
            {command["kind"] for command in command_set.as_dict()["commands"]},
            {"avoid_food", "replace_food_preference", "set_simple_style"},
        )

    def test_adjustment_rules_apply_food_replacements_and_preferences(self):
        brief = NutritionBrief(
            raw_prompt="",
            goal="fat_loss",
            meals_per_day=4,
            excluded_foods=["atún"],
            preferred_foods=[],
        )

        adjusted = apply_conversation_adjustments(brief, "cambiar arroz por quinoa y prefiero pollo")

        self.assertIn("atún", adjusted.excluded_foods)
        self.assertIn("arroz", adjusted.excluded_foods)
        self.assertIn("quinoa", adjusted.preferred_foods)
        self.assertIn("pollo", adjusted.preferred_foods)

    def test_should_iterate_only_when_chat_has_generated_proposal_and_feedback(self):
        proposal = NutritionProposal.objects.create(
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="DailyPlan generado",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {"meals": []},
            },
        )
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Chat con propuesta generada",
            status=AiNutritionChat.STATUS_PROPOSAL_CREATED,
            proposal=proposal,
        )

        self.assertTrue(should_iterate_generated_plan(chat=chat, message="sin arroz"))
        self.assertFalse(should_iterate_generated_plan(chat=chat, message="quiero ver el brief"))
        self.assertFalse(should_iterate_generated_plan(chat=None, message="sin arroz"))

    def test_async_feedback_creates_new_generated_proposal_revision(self):
        chat = self._create_generated_plan_chat()
        previous_proposal_id = chat.proposal_id

        response = self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "sin arroz",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        chat.refresh_from_db()
        self.assertNotEqual(chat.proposal_id, previous_proposal_id)
        self.assertEqual(chat.status, AiNutritionChat.STATUS_PROPOSAL_CREATED)
        self.assertEqual(
            chat.proposal.current_snapshot["iteration"]["previous_proposal_id"],
            previous_proposal_id,
        )
        self.assertIn("sin arroz", chat.proposal.summary)
        self.assertIn("Evitar arroz", chat.proposal.current_snapshot["iteration"]["command_labels"])
        self.assertEqual(
            chat.proposal.validation_summary["chat_iteration"]["command_set"]["commands"][0]["kind"],
            "avoid_food",
        )
        generated_food_ids = [
            food["food_id"]
            for meal in chat.proposal.proposed_payload["dailyplan"]["meals"]
            for food in meal["meal"]["foods"]
        ]
        serialized_food_names = " ".join(
            name.lower()
            for name in Food.objects.filter(id__in=generated_food_ids).values_list("name", flat=True)
        )
        self.assertNotIn("arroz", serialized_food_names)
        self.assertIn("quinoa", serialized_food_names)
        self.assertIn("Actualicé la propuesta", response.json()["thread_html"])

    def test_feedback_records_meal_count_iteration_command(self):
        chat = self._create_generated_plan_chat()
        previous_proposal_id = chat.proposal_id

        response = self.client.post(
            reverse("ai_nutrition_intake"),
            {
                "action": "continue_conversation",
                "is_async": "1",
                "message": "quiero menos comidas",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            HTTP_ACCEPT="application/json",
        )

        self.assertEqual(response.status_code, 200)
        chat = AiNutritionChat.objects.get(user=self.user)
        self.assertNotEqual(chat.proposal_id, previous_proposal_id)
        iteration = chat.proposal.current_snapshot["iteration"]
        self.assertEqual(iteration["previous_proposal_id"], previous_proposal_id)
        self.assertIn("Reducir cantidad de comidas", iteration["command_labels"])
        self.assertEqual(
            chat.proposal.validation_summary["chat_iteration"]["command_set"]["commands"][0]["kind"],
            "decrease_meals_per_day",
        )
