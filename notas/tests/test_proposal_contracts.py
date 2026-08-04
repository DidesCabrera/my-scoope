from django.test import SimpleTestCase

from notas.application.proposals.contracts import (
    AI_NUTRITION_BRIEF_INTENT,
    CREATE_DAILYPLAN_INTENT,
    CREATE_MEAL_INTENT,
    can_apply_proposal,
    get_proposal_intent_contract,
    proposal_status_label,
    resolve_proposal_intent,
)


class ProposalContractsTests(SimpleTestCase):
    def test_resolve_proposal_intent_normalizes_payload_intent(self):
        self.assertEqual(
            resolve_proposal_intent({"intent": " create_meal "}),
            CREATE_MEAL_INTENT,
        )
        self.assertIsNone(resolve_proposal_intent({"intent": ""}))
        self.assertIsNone(resolve_proposal_intent(None))

    def test_intent_contracts_define_supported_entities(self):
        meal_contract = get_proposal_intent_contract(CREATE_MEAL_INTENT)
        dailyplan_contract = get_proposal_intent_contract(CREATE_DAILYPLAN_INTENT)
        brief_contract = get_proposal_intent_contract(AI_NUTRITION_BRIEF_INTENT)

        self.assertEqual(meal_contract.entity_title, "Comida en la propuesta")
        self.assertEqual(meal_contract.attachment_kind, "meal")
        self.assertTrue(meal_contract.is_create_meal)
        self.assertTrue(meal_contract.is_apply_supported)

        self.assertEqual(dailyplan_contract.entity_title, "DailyPlan en la propuesta")
        self.assertEqual(dailyplan_contract.attachment_kind, "dailyplan")
        self.assertTrue(dailyplan_contract.is_create_dailyplan)
        self.assertTrue(dailyplan_contract.is_apply_supported)

        self.assertEqual(brief_contract.attachment_kind, "brief")
        self.assertFalse(brief_contract.is_apply_supported)

    def test_unknown_intent_is_safe_and_not_applicable(self):
        contract = get_proposal_intent_contract("unknown")

        self.assertEqual(contract.entity_title, "Entidad en la propuesta")
        self.assertEqual(contract.attachment_kind, "dailyplan")
        self.assertFalse(contract.is_apply_supported)

    def test_can_apply_proposal_requires_approved_supported_and_not_applied(self):
        self.assertTrue(
            can_apply_proposal(
                status="approved",
                intent=CREATE_MEAL_INTENT,
                applied_at=None,
            )
        )
        self.assertFalse(
            can_apply_proposal(
                status="pending_review",
                intent=CREATE_MEAL_INTENT,
                applied_at=None,
            )
        )
        self.assertFalse(
            can_apply_proposal(
                status="approved",
                intent=AI_NUTRITION_BRIEF_INTENT,
                applied_at=None,
            )
        )
        self.assertFalse(
            can_apply_proposal(
                status="approved",
                intent=CREATE_MEAL_INTENT,
                applied_at="2026-06-30T00:00:00Z",
            )
        )

    def test_proposal_status_label_is_centralized(self):
        self.assertEqual(proposal_status_label("pending_review"), "Pendiente")
        self.assertEqual(proposal_status_label("approved"), "Aprobada")
        self.assertEqual(proposal_status_label("applied"), "Aplicada")
        self.assertEqual(proposal_status_label("custom"), "custom")
        self.assertEqual(proposal_status_label(None), "")
