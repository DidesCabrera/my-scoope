from decimal import Decimal

from django.contrib.auth.models import User
from django.test import Client, override_settings

from accounts.models import AccountPlan, AccountSubscription
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.domain.models import Preparation, PreparationVersion


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class ExplorePreparationsAPITests(AuthenticatedMobileAPITestCase):
    def create_preparation(self, name, *, is_global=True, is_active=True, created_by=None, with_version=True):
        preparation = Preparation.objects.create(
            name=name, is_global=is_global, is_active=is_active, created_by=created_by,
        )
        if with_version:
            version = PreparationVersion.objects.create(
                preparation=preparation, version=1, release_version="test", yield_g=Decimal("100"),
                default_portion_g=Decimal("50"), household_label="porción", protein_g=Decimal("10"),
                carbs_g=Decimal("20"), fat_g=Decimal("5"), sodium_mg=Decimal("0"),
                allergens=[], ingredients_snapshot=[], content_sha256="test",
            )
            preparation.current_version = version
            preparation.save(update_fields=["current_version"])
        return preparation

    def test_exploration_only_lists_active_versioned_global_preparations(self):
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="pro")}
        )
        curator = User.objects.create_user(username="preparation-curator")
        first = self.create_preparation("Completo italiano")
        second = self.create_preparation("Sopa global")
        self.create_preparation("Completo personal", is_global=False, created_by=self.user)
        self.create_preparation("Completo ajeno", is_global=False, created_by=curator)
        self.create_preparation("Completo inactivo", is_active=False)
        self.create_preparation("Completo sin versión", with_version=False)

        response = self.client.get("/api/v1/explore/preparations")
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["total"], 2)
        self.assertEqual([item["id"] for item in data["items"]], [first.id, second.id])
        self.assertTrue(all(not item["is_personal"] for item in data["items"]))
        self.assertEqual(self.client.get("/api/v1/explore/preparations", {"search": "italiano"}).json()["data"]["total"], 1)
        self.assertEqual(self.client.get("/api/v1/explore/preparations", {"limit": 1, "offset": 1}).json()["data"]["items"][0]["id"], second.id)
        self.assertEqual(self.client.get(f"/api/v1/preparations/{first.id}").status_code, 200)

    def test_exploration_requires_authentication(self):
        self.assertEqual(Client().get("/api/v1/explore/preparations").status_code, 401)
