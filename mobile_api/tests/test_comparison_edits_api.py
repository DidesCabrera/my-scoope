from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.utils import timezone

from mobile_api.tests.base import PaidMobileAPITestCase
from notas.application.services.mcp_user_tokens import create_mcp_user_token
from notas.application.services.oauth_device_sessions import MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE
from notas.domain.models import Food


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class MobileAPIComparisonEditTests(PaidMobileAPITestCase):
    def test_saved_comparison_rename_is_owner_scoped(self):
        foods = [
            Food.objects.create(name=name, protein=10, carbs=20, fat=5, created_by=self.user)
            for name in ("Avena", "Arroz")
        ]
        saved = self.client.post(
            "/api/v1/comparisons/saved",
            data={"kind": "foods", "selections": [{"id": food.id, "quantity": 100} for food in foods]},
            content_type="application/json",
        )
        comparison_id = saved.json()["data"]["saved_comparison_id"]
        renamed = self.client.patch(
            f"/api/v1/comparisons/saved/{comparison_id}/name",
            data={"name": "  Desayuno comparado  "},
            content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200)
        self.assertEqual(renamed.json()["data"]["saved_comparison_name"], "Desayuno comparado")

        outsider = User.objects.create_user(username="comparison-rename-outsider")
        token = create_mcp_user_token(
            user=outsider,
            name="Comparison rename outsider token",
            scopes=[MOBILE_SCOPE_READ, MOBILE_SCOPE_WRITE],
            expires_at=timezone.now() + timedelta(minutes=15),
        )
        hidden = Client(HTTP_AUTHORIZATION=f"Bearer {token.raw_token}").patch(
            f"/api/v1/comparisons/saved/{comparison_id}/name",
            data={"name": "Nombre ajeno"},
            content_type="application/json",
        )
        self.assertEqual(hidden.status_code, 404)
