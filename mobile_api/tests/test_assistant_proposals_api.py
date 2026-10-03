from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ
from notas.domain.models import AiNutritionChat, NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIAssistantProposalTests(AuthenticatedMobileAPITestCase):
    def test_chat_proposals_lists_every_persisted_proposal_and_is_owner_scoped(self):
        first = NutritionProposal.objects.create(
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Primera propuesta",
            proposed_payload={"intent": "create_meal", "meal": {"name": "Comida uno", "foods": []}},
        )
        current = NutritionProposal.objects.create(
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Propuesta actual",
            proposed_payload={"intent": "create_dailyplan", "dailyplan": {"name": "Plan actual", "meals": []}},
        )
        unrelated = NutritionProposal.objects.create(
            created_by=self.user,
            source=NutritionProposal.SOURCE_AI,
            title="Propuesta de otro chat",
            proposed_payload={"intent": "create_meal", "meal": {"name": "Otra comida", "foods": []}},
        )
        chat = AiNutritionChat.objects.create(
            user=self.user,
            title="Chat con revisiones",
            proposal=current,
            conversation_payload={
                "messages": [
                    {"role": "assistant", "proposal_review_card": {"proposal_id": first.id}},
                    {"role": "assistant", "generated_plan_card": {"url": f"/app/proposals/{current.id}/"}},
                ]
            },
        )

        response = self.client.get(f"/api/v1/ai/chats/{chat.id}/proposals")

        self.assertEqual(response.status_code, 200)
        item_ids = {item["id"] for item in response.json()["data"]["items"]}
        self.assertEqual(item_ids, {first.id, current.id})
        self.assertNotIn(unrelated.id, item_ids)

        other_user = User.objects.create_user(username="chat-proposals-outsider")
        other_token = create_mcp_user_token(
            user=other_user,
            name="Chat proposals outsider token",
            scopes=[MOBILE_SCOPE_READ],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        outsider = Client(HTTP_AUTHORIZATION=f"Bearer {other_token.raw_token}")
        self.assertEqual(outsider.get(f"/api/v1/ai/chats/{chat.id}/proposals").status_code, 404)
