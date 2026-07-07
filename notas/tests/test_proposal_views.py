from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    Food,
    Meal,
    MealFood,
    NutritionProposal,
)


class ProposalViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="felipe",
            email="felipe@example.com",
            password="pass123",
        )
        self.other_user = User.objects.create_user(
            username="other",
            email="other@example.com",
            password="pass123",
        )
        for user in (self.user, self.other_user):
            user.profile.onboarding_completed_at = timezone.now()
            user.profile.onboarding_version = user.profile.ONBOARDING_VERSION_NUTRITION_V1
            user.profile.save(update_fields=["onboarding_completed_at", "onboarding_version"])

        self.dailyplan = DailyPlan.objects.create(
            name="Training Day",
            created_by=self.user,
            is_public=False,
            is_draft=False,
        )
        self.other_dailyplan = DailyPlan.objects.create(
            name="Other Training Day",
            created_by=self.other_user,
            is_public=False,
            is_draft=False,
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

        self.proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Increase protein",
            summary="Increase protein while keeping calories stable.",
            targets={
                "protein": 190,
            },
            current_snapshot={
                "dailyplan_id": self.dailyplan.id,
                "dailyplan_name": self.dailyplan.name,
                "actual": {
                    "protein": 170,
                },
            },
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
            validation_summary={
                "within_tolerance": False,
                "delta": {
                    "protein": -20,
                },
                "metrics": [
                    {
                        "metric": "protein",
                        "target": 190,
                        "actual": 170,
                        "delta": -20,
                        "tolerance": 10,
                        "within_tolerance": False,
                        "status": "under_target",
                    }
                ],
            },
        )

        self.other_proposal = NutritionProposal.objects.create(
            dailyplan=self.other_dailyplan,
            created_by=self.other_user,
            title="Private other proposal",
        )

    def test_proposal_list_requires_login(self):
        response = self.client.get(
            reverse("proposal_list"),
        )

        self.assertEqual(response.status_code, 302)

    def test_proposal_list_shows_visible_proposals_only(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("proposal_list"),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Increase protein")
        self.assertNotContains(response, "Private other proposal")

    def test_proposal_detail_renders_review_page_for_validation_proposal(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[self.proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)

        # Regla de producto: la propuesta existe y pertenece al usuario.
        self.assertContains(response, self.proposal.title)
        self.assertContains(response, self.dailyplan.name)

        # Regla de producto: una proposal pending_review mantiene acciones humanas.
        self.assertContains(response, "Aprobar propuesta")
        self.assertContains(response, "Rechazar propuesta")

        # Regla de producto: no debe mostrar acción de apply todavía.
        self.assertNotContains(response, "Aplicar propuesta")

    def test_proposal_detail_shows_proposal_review_summary(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[self.proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Increase protein")
        self.assertContains(response, "Training Day")
        self.assertContains(response, "adjust_dailyplan_to_targets")
        self.assertContains(response, "protein")
        self.assertContains(response, "190")
        self.assertContains(response, "Revisión humana")
        self.assertContains(response, "Aprobar propuesta")
        self.assertContains(response, "Rechazar propuesta")


    def test_proposal_detail_blocks_private_other_proposal(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[self.other_proposal.id],
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_approve_proposal_marks_it_as_approved(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "proposal_approve",
                args=[self.proposal.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.proposal.refresh_from_db()

        self.assertEqual(
            self.proposal.status,
            NutritionProposal.STATUS_APPROVED,
        )
        self.assertEqual(
            self.proposal.reviewed_by,
            self.user,
        )
        self.assertIsNotNone(self.proposal.reviewed_at)

        # Importante: aprobar todavía no modifica el DailyPlan.
        self.dailyplan.refresh_from_db()
        self.assertEqual(self.dailyplan.name, "Training Day")

    def test_reject_proposal_marks_it_as_rejected(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "proposal_reject",
                args=[self.proposal.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.proposal.refresh_from_db()

        self.assertEqual(
            self.proposal.status,
            NutritionProposal.STATUS_REJECTED,
        )
        self.assertEqual(
            self.proposal.reviewed_by,
            self.user,
        )
        self.assertIsNotNone(self.proposal.reviewed_at)

    def test_cancel_proposal_marks_it_as_cancelled(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse(
                "proposal_cancel",
                args=[self.proposal.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        self.proposal.refresh_from_db()

        self.assertEqual(
            self.proposal.status,
            NutritionProposal.STATUS_CANCELLED,
        )
        self.assertEqual(
            self.proposal.reviewed_by,
            self.user,
        )
        self.assertIsNotNone(self.proposal.reviewed_at)

    def test_unrelated_user_cannot_approve_private_proposal(self):
        self.client.force_login(self.other_user)

        response = self.client.post(
            reverse(
                "proposal_approve",
                args=[self.proposal.id],
            )
        )

        self.assertEqual(response.status_code, 404)

        self.proposal.refresh_from_db()

        self.assertEqual(
            self.proposal.status,
            NutritionProposal.STATUS_PENDING_REVIEW,
        )

    def test_proposal_detail_shows_review_vm_for_create_dailyplan(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Plan AI",
            summary="DailyPlan completo propuesto desde MCP.",
            targets={
                "protein": 190,
                "total_kcal": 2800,
            },
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [],
                },
            },
            validation_summary={
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_dailyplan",
                },
                "simulation": {
                    "intent": "create_dailyplan",
                    "meal": None,
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
                                            "food_id": 128,
                                            "food_name": "a nuevo egg TEST",
                                            "quantity": 200,
                                            "unit": "g",
                                            "protein": 2,
                                            "carbs": 2,
                                            "fat": 2,
                                            "total_kcal": 34,
                                        },
                                    ],
                                    "kpis": {
                                        "total_kcal": 34,
                                        "protein": 2,
                                        "carbs": 2,
                                        "fat": 2,
                                        "ppk": 0.02,
                                        "alloc_protein": 23.52,
                                        "alloc_carbs": 23.52,
                                        "alloc_fat": 52.94,
                                    },
                                },
                            },
                        ],
                        "kpis": {
                            "total_kcal": 34,
                            "protein": 2,
                            "carbs": 2,
                            "fat": 2,
                            "ppk": 0.02,
                            "alloc_protein": 23.52,
                            "alloc_carbs": 23.52,
                            "alloc_fat": 52.94,
                        },
                    },
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Plan AI")
        self.assertContains(response, "DailyPlan propuesto")
        self.assertContains(response, "Día entrenamiento IA")
        self.assertContains(response, "Desayuno IA")
        self.assertContains(response, "09:00")
        self.assertContains(response, "Desayuno")
        self.assertContains(response, "a nuevo egg TEST")

    def test_proposal_detail_shows_review_vm_for_create_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Comida AI",
            summary="Comida propuesta desde MCP.",
            targets={
                "protein": 60,
            },
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [],
                },
            },
            validation_summary={
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_meal",
                },
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [
                            {
                                "food_id": 1,
                                "food_name": "Pechuga pollo",
                                "quantity": 200,
                                "unit": "g",
                                "protein": 62,
                                "carbs": 0,
                                "fat": 7.2,
                                "total_kcal": 312.8,
                            },
                        ],
                        "kpis": {
                            "total_kcal": 312.8,
                            "protein": 62,
                            "carbs": 0,
                            "fat": 7.2,
                            "ppk": 0.62,
                            "alloc_protein": 79.28,
                            "alloc_carbs": 0,
                            "alloc_fat": 20.72,
                        },
                    },
                    "dailyplan": None,
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comida AI")

    def test_proposal_detail_renders_create_meal_review_card(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Comida AI",
            summary="Comida propuesta desde MCP.",
            targets={
                "protein": 60,
                "total_kcal": 500,
            },
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": 1,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
            validation_summary={
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_meal",
                },
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [
                            {
                                "food_id": 1,
                                "food_name": "Pechuga pollo",
                                "quantity": 200,
                                "unit": "g",
                                "protein": 62,
                                "carbs": 0,
                                "fat": 7.2,
                                "total_kcal": 312.8,
                            },
                        ],
                        "kpis": {
                            "total_kcal": 312.8,
                            "protein": 62,
                            "carbs": 0,
                            "fat": 7.2,
                            "ppk": 0.62,
                            "alloc_protein": 79.28,
                            "alloc_carbs": 0,
                            "alloc_fat": 20.72,
                        },
                    },
                    "dailyplan": None,
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comida propuesta")
        self.assertContains(response, "Almuerzo IA")
        self.assertContains(response, "Pechuga pollo")

    def test_proposal_detail_renders_create_dailyplan_review_card(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Plan AI",
            summary="DailyPlan completo propuesto desde MCP.",
            targets={
                "protein": 190,
                "total_kcal": 2800,
            },
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [],
                },
            },
            validation_summary={
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_dailyplan",
                },
                "simulation": {
                    "intent": "create_dailyplan",
                    "meal": None,
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
                                            "food_id": 128,
                                            "food_name": "a nuevo egg TEST",
                                            "quantity": 200,
                                            "unit": "g",
                                            "protein": 2,
                                            "carbs": 2,
                                            "fat": 2,
                                            "total_kcal": 34,
                                        },
                                    ],
                                    "kpis": {
                                        "total_kcal": 34,
                                        "protein": 2,
                                        "carbs": 2,
                                        "fat": 2,
                                        "ppk": 0.02,
                                        "alloc_protein": 23.52,
                                        "alloc_carbs": 23.52,
                                        "alloc_fat": 52.94,
                                    },
                                },
                            },
                        ],
                        "kpis": {
                            "total_kcal": 34,
                            "protein": 2,
                            "carbs": 2,
                            "fat": 2,
                            "ppk": 0.02,
                            "alloc_protein": 23.52,
                            "alloc_carbs": 23.52,
                            "alloc_fat": 52.94,
                        },
                    },
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DailyPlan propuesto")
        self.assertContains(response, "Día entrenamiento IA")
        self.assertContains(response, "Desayuno IA")
        self.assertContains(response, "09:00")
        self.assertContains(response, "Desayuno")
        self.assertContains(response, "a nuevo egg TEST")

    def test_proposal_detail_shows_safe_review_actions_for_reviewable_proposal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Comida AI",
            summary="Comida propuesta desde MCP.",
            targets={
                "protein": 60,
            },
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [],
                },
            },
            validation_summary={
                "payload_validation": {
                    "is_valid": True,
                    "intent": "create_meal",
                },
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [],
                        "kpis": {
                            "protein": 62,
                            "total_kcal": 312.8,
                        },
                    },
                    "dailyplan": None,
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revisión humana")
        self.assertContains(response, "Aprobar propuesta")
        self.assertContains(response, "Rechazar propuesta")
        self.assertContains(response, "Cancelar propuesta")
        self.assertContains(response, "Aprobar todavía no aplica cambios reales")


    def test_proposal_detail_shows_closed_review_message_for_rejected_proposal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Comida AI rechazada",
            status=NutritionProposal.STATUS_REJECTED,
            reviewed_by=self.user,
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [],
                },
            },
            validation_summary={
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [],
                        "kpis": {
                            "protein": 62,
                            "total_kcal": 312.8,
                        },
                    },
                    "dailyplan": None,
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revisión cerrada")
        self.assertContains(response, "Esta propuesta ya no está pendiente de revisión")
        self.assertNotContains(response, "Aprobar propuesta")
        self.assertNotContains(response, "Rechazar propuesta")
        self.assertNotContains(response, "Aplicar propuesta")



    def test_approve_create_meal_proposal_does_not_create_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
            validation_summary={
                "simulation": {
                    "intent": "create_meal",
                    "meal": {
                        "name": "Almuerzo IA",
                        "foods": [],
                        "kpis": {},
                    },
                    "dailyplan": None,
                },
            },
        )

        before_meal_count = Meal.objects.count()
        before_dailyplan_count = DailyPlan.objects.count()

        response = self.client.post(
            reverse(
                "proposal_approve",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertEqual(Meal.objects.count(), before_meal_count)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count)

    def test_approve_create_dailyplan_proposal_does_not_create_dailyplan_or_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Plan AI",
            proposed_payload={
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
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
            validation_summary={
                "simulation": {
                    "intent": "create_dailyplan",
                    "meal": None,
                    "dailyplan": {
                        "name": "Día entrenamiento IA",
                        "meals": [],
                        "kpis": {},
                    },
                },
            },
        )

        before_meal_count = Meal.objects.count()
        before_dailyplan_count = DailyPlan.objects.count()

        response = self.client.post(
            reverse(
                "proposal_approve",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertEqual(Meal.objects.count(), before_meal_count)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count)

    def test_reject_create_dailyplan_proposal_does_not_create_dailyplan_or_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Plan AI",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [],
                },
            },
            validation_summary={
                "simulation": {
                    "intent": "create_dailyplan",
                    "meal": None,
                    "dailyplan": {
                        "name": "Día entrenamiento IA",
                        "meals": [],
                        "kpis": {},
                    },
                },
            },
        )

        before_meal_count = Meal.objects.count()
        before_dailyplan_count = DailyPlan.objects.count()

        response = self.client.post(
            reverse(
                "proposal_reject",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 302)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_REJECTED)
        self.assertEqual(Meal.objects.count(), before_meal_count)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count)

    def test_proposal_apply_create_meal_creates_real_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        before_meal_count = Meal.objects.count()

        response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Meal.objects.count(), before_meal_count + 1)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertContains(response, "Propuesta aplicada")
        self.assertContains(response, "Almuerzo IA")

    def test_proposal_apply_create_dailyplan_creates_real_dailyplan(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
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
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        before_dailyplan_count = DailyPlan.objects.count()
        before_meal_count = Meal.objects.count()
        before_dpm_count = DailyPlanMeal.objects.count()
        before_mealfood_count = MealFood.objects.count()

        response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count + 1)
        self.assertEqual(Meal.objects.count(), before_meal_count + 1)
        self.assertEqual(DailyPlanMeal.objects.count(), before_dpm_count + 1)
        self.assertEqual(MealFood.objects.count(), before_mealfood_count + 1)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertContains(response, "Propuesta aplicada")
        self.assertContains(response, "Día entrenamiento IA")


    def test_proposal_apply_external_subject_requires_ppk_warning_ack(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan externo",
            targets={
                "subject_context": {
                    "source": "external_chat_data",
                    "ppk_weight_source": "external_subject_weight",
                    "requires_library_ppk_warning": True,
                    "calculation_weight_kg": 70,
                },
            },
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día externo IA",
                    "meals": [
                        {
                            "hour": "09:00",
                            "note": "Desayuno",
                            "meal": {
                                "name": "Desayuno externo",
                                "foods": [
                                    {
                                        "food_id": self.rice.id,
                                        "quantity": 100,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        before_dailyplan_count = DailyPlan.objects.count()

        response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPROVED)
        self.assertContains(response, "debes confirmar")

    def test_proposal_apply_external_subject_with_ack_creates_real_dailyplan(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan externo",
            targets={
                "subject_context": {
                    "source": "external_chat_data",
                    "ppk_weight_source": "external_subject_weight",
                    "requires_library_ppk_warning": True,
                    "calculation_weight_kg": 70,
                },
            },
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día externo IA",
                    "meals": [
                        {
                            "hour": "09:00",
                            "note": "Desayuno",
                            "meal": {
                                "name": "Desayuno externo",
                                "foods": [
                                    {
                                        "food_id": self.rice.id,
                                        "quantity": 100,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        before_dailyplan_count = DailyPlan.objects.count()

        response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            {
                "ack_external_subject_ppk_warning": "1",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(DailyPlan.objects.count(), before_dailyplan_count + 1)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertContains(response, "Propuesta aplicada")

    def test_proposal_apply_requires_applicable_status(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        before_meal_count = Meal.objects.count()

        response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Meal.objects.count(), before_meal_count)

        proposal.refresh_from_db()

        self.assertEqual(proposal.status, NutritionProposal.STATUS_PENDING_REVIEW)
        self.assertContains(response, "No se pudo aplicar la propuesta")

    def test_unrelated_user_cannot_apply_private_proposal(self):
        self.client.force_login(self.other_user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Meal.objects.count(), 0)

    def test_proposal_detail_shows_apply_button_for_approved_create_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aplicación segura")
        self.assertContains(response, "Aplicar propuesta")
        self.assertNotContains(response, "Aprobar propuesta")
        self.assertNotContains(response, "Rechazar propuesta")

    def test_proposal_detail_shows_apply_button_for_approved_create_dailyplan(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
                "intent": "create_dailyplan",
                "dailyplan": {
                    "name": "Día entrenamiento IA",
                    "meals": [
                        {
                            "meal": {
                                "name": "Desayuno IA",
                                "foods": [
                                    {
                                        "food_id": self.rice.id,
                                        "quantity": 100,
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aplicación segura")
        self.assertContains(response, "Aplicar propuesta")
        self.assertNotContains(response, "Aprobar propuesta")
        self.assertNotContains(response, "Rechazar propuesta")


    def test_proposal_detail_does_not_show_apply_button_for_pending_review(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_PENDING_REVIEW,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Aplicar propuesta")
        self.assertContains(response, "Aprobar propuesta")
        self.assertContains(response, "Rechazar propuesta")


    def test_proposal_detail_does_not_show_apply_button_for_unsupported_intent(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Legacy approved",
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Propuesta aprobada")
        self.assertNotContains(response, "Aplicar propuesta")
        self.assertNotContains(response, "Aprobar propuesta")
        self.assertNotContains(response, "Rechazar propuesta")

    def test_proposal_detail_does_not_show_apply_button_for_applied_create_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            )
        )

        proposal.refresh_from_db()

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertNotContains(response, "Aplicar propuesta")
        self.assertContains(response, "Propuesta aplicada")


    def test_proposal_detail_does_not_show_apply_button_for_applied_create_dailyplan(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
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
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            )
        )

        proposal.refresh_from_db()

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertNotContains(response, "Aplicar propuesta")
        self.assertContains(response, "Propuesta aplicada")


    def test_proposal_detail_shows_non_applicable_message_for_approved_unsupported_intent(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Legacy approved",
            proposed_payload={
                "intent": "adjust_dailyplan_to_targets",
                "suggested_changes": [],
            },
        )

        response = self.client.get(
            reverse(
                "proposal_detail",
                args=[proposal.id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Aplicar propuesta")
        self.assertNotContains(response, "Aprobar propuesta")
        self.assertNotContains(response, "Rechazar propuesta")
        self.assertContains(
            response,
            "Sin aplicación automática",
        )


    def test_double_apply_create_meal_does_not_create_duplicate_meal(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Comida AI",
            proposed_payload={
                "intent": "create_meal",
                "meal": {
                    "name": "Almuerzo IA",
                    "foods": [
                        {
                            "food_id": self.chicken.id,
                            "quantity": 200,
                            "unit": "g",
                        },
                    ],
                },
            },
        )

        first_response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        second_response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        proposal.refresh_from_db()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertEqual(
            Meal.objects.filter(
                name="Almuerzo IA",
                created_by=self.user,
            ).count(),
            1,
        )
        self.assertContains(second_response, "No se pudo aplicar la propuesta")


    def test_double_apply_create_dailyplan_does_not_create_duplicate_dailyplan(self):
        self.client.force_login(self.user)

        proposal = NutritionProposal.objects.create(
            dailyplan=self.dailyplan,
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            status=NutritionProposal.STATUS_APPROVED,
            title="Plan AI",
            proposed_payload={
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
                                        "unit": "g",
                                    },
                                ],
                            },
                        },
                    ],
                },
            },
        )

        first_response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        second_response = self.client.post(
            reverse(
                "proposal_apply",
                args=[proposal.id],
            ),
            follow=True,
        )

        proposal.refresh_from_db()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(proposal.status, NutritionProposal.STATUS_APPLIED)
        self.assertEqual(
            DailyPlan.objects.filter(
                name="Día entrenamiento IA",
                created_by=self.user,
            ).count(),
            1,
        )
        self.assertContains(second_response, "No se pudo aplicar la propuesta")



