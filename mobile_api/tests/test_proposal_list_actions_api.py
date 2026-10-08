from django.contrib.auth.models import User
from django.test import override_settings

from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import NutritionProposal


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIProposalListActionTests(AuthenticatedMobileAPITestCase):
    def test_proposal_list_can_be_bulk_deleted(self):
        first = NutritionProposal.objects.create(created_by=self.user, title="Primera")
        second = NutritionProposal.objects.create(created_by=self.user, title="Segunda")

        listed = self.client.get("/api/v1/proposals")
        deleted = self.client.post(
            "/api/v1/proposals/bulk-delete",
            data={"item_ids": [first.id]},
            content_type="application/json",
        )

        self.assertEqual([item["id"] for item in listed.json()["data"]["items"]], [second.id, first.id])
        self.assertEqual(deleted.status_code, 200)
        self.assertFalse(NutritionProposal.objects.filter(id=first.id).exists())

        outsider = User.objects.create_user(username="proposal-list-outsider")
        foreign = NutritionProposal.objects.create(created_by=outsider, title="Privada")
        denied = self.client.post(
            "/api/v1/proposals/bulk-delete",
            data={"item_ids": [foreign.id]},
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 403)
        self.assertTrue(NutritionProposal.objects.filter(id=foreign.id).exists())
