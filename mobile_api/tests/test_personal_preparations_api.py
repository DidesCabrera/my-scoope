from django.contrib.auth.models import User
from django.test import override_settings

from accounts.models import AccountPlan, AccountSubscription
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.calendarization.snapshots import build_meal_snapshot
from notas.application.services.commands.personal_preparation_commands import save_personal_preparation
from notas.application.sharing.entities import build_meal_share_snapshot
from notas.application.sharing.services import ShareUnavailable
from notas.domain.models import Food, Meal, MealPreparation, Preparation


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False, PERSONAL_PREPARATIONS_FEATURE_ENABLED=True)
class PersonalPreparationAPITests(AuthenticatedMobileAPITestCase):
    def setUp(self):
        super().setUp()
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="pro")}
        )
        self.food = Food.objects.create(
            name="Avena", protein=10, carbs=60, fat=5, is_global=True, preparation_state="dry", sodium_mg_per_100g=2
        )
        self.payload = {
            "name": "Avena cocida",
            "yield_g": 200,
            "default_portion_g": 100,
            "household_label": "porción",
            "ingredients": [{"food_id": self.food.id, "quantity_g": 100}],
        }

    def create_preparation(self):
        response = self.client.post("/api/v1/library/preparations", data=self.payload, content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["data"]

    def test_create_list_and_use_personal_preparation_in_meal(self):
        created = self.create_preparation()
        self.assertTrue(created["is_personal"])
        self.assertEqual(created["recipe_ingredients"][0]["quantity_g"], 100)
        self.assertEqual(created["nutrition"]["protein_g"], 5)
        self.assertEqual(self.client.get("/api/v1/library/preparations").json()["data"]["total"], 1)
        self.assertEqual(self.client.get("/api/v1/home/summary").json()["data"]["library_counts"]["preparation"], 1)
        self.assertTrue(
            self.client.get("/api/v1/entitlements").json()["data"]["workspace_features"][
                "can_use_personal_preparations"
            ]
        )
        self.assertEqual(self.client.get("/api/v1/preparations?search=Avena").json()["data"]["total"], 1)
        meal = Meal.objects.create(name="Desayuno", created_by=self.user)
        added = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data={"preparation_id": created["id"], "units": 1},
            content_type="application/json",
        )
        self.assertEqual(added.status_code, 200, added.content)
        self.assertEqual(MealPreparation.objects.get(meal=meal).version.version, 1)
        with self.assertRaises(ShareUnavailable):
            build_meal_share_snapshot(meal)

    def test_revision_updates_live_meal_but_not_frozen_snapshot(self):
        created = self.create_preparation()
        meal = Meal.objects.create(name="Desayuno", created_by=self.user)
        response = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data={"preparation_id": created["id"], "units": 1},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        frozen = build_meal_snapshot(meal=meal, key="meal:1", order=0, hour=None)
        changed = {**self.payload, "ingredients": [{"food_id": self.food.id, "quantity_g": 200}]}
        updated = self.client.put(
            f"/api/v1/library/preparations/{created['id']}", data=changed, content_type="application/json"
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(updated.json()["data"]["version"], 2)
        self.assertEqual(MealPreparation.objects.get(meal=meal).version.version, 2)
        self.assertEqual(frozen["foods"][0]["protein_g"], 5)
        meal.refresh_from_db()
        self.assertEqual(meal.protein, 10)

    def test_private_ingredients_and_other_users_preparations_are_rejected(self):
        other = User.objects.create_user(username="other-preparation-user")
        private_food = Food.objects.create(name="Privado", protein=1, carbs=1, fat=1, created_by=other)
        payload = {**self.payload, "ingredients": [{"food_id": private_food.id, "quantity_g": 100}]}
        response = self.client.post("/api/v1/library/preparations", data=payload, content_type="application/json")
        self.assertEqual(response.status_code, 422, response.content)
        self.assertEqual(Preparation.objects.filter(created_by=self.user).count(), 0)
        other_preparation = Preparation.objects.create(name="Ajena", is_global=False, created_by=other)
        self.assertEqual(self.client.get(f"/api/v1/preparations/{other_preparation.id}").status_code, 404)
        AccountSubscription.objects.update_or_create(user=other, defaults={"plan": AccountPlan.objects.get(slug="pro")})
        saved_other = save_personal_preparation(
            user=other,
            name="Receta ajena",
            yield_g=100,
            default_portion_g=50,
            household_label="porción",
            ingredients=[{"food_id": self.food.id, "quantity_g": 100}],
        )
        self.assertEqual(self.client.get(f"/api/v1/preparations/{saved_other.id}").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/preparations").json()["data"]["total"], 0)

    def test_downgrade_and_switch_preserve_records_but_close_personal_access(self):
        created = self.create_preparation()
        meal = Meal.objects.create(name="Comida", created_by=self.user)
        added = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data={"preparation_id": created["id"], "units": 1},
            content_type="application/json",
        )
        self.assertEqual(added.status_code, 200, added.content)
        relation_id = added.json()["data"]["created_id"]
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="basic"))
        self.assertEqual(self.client.get("/api/v1/library/preparations").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/preparations/{created['id']}").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/preparations").json()["data"]["total"], 0)
        blocked = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data={"preparation_id": created["id"], "units": 1},
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 404)
        bypass = self.client.patch(
            f"/api/v1/library/meals/{meal.id}/preparations/{relation_id}",
            data={"units": 2},
            content_type="application/json",
        )
        self.assertEqual(bypass.status_code, 404)
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="pro"))
        with override_settings(PERSONAL_PREPARATIONS_FEATURE_ENABLED=False):
            self.assertEqual(self.client.get("/api/v1/library/preparations").status_code, 403)
            self.assertFalse(
                self.client.get("/api/v1/entitlements").json()["data"]["workspace_features"][
                    "can_use_personal_preparations"
                ]
            )
        self.assertTrue(Preparation.objects.filter(pk=created["id"], is_active=True).exists())

    def test_delete_removes_from_library_and_picker_without_destroying_versions(self):
        created = self.create_preparation()
        response = self.client.delete(f"/api/v1/library/preparations/{created['id']}")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.client.get("/api/v1/library/preparations").json()["data"]["total"], 0)
        self.assertEqual(self.client.get(f"/api/v1/preparations/{created['id']}").status_code, 200)
        self.assertEqual(Preparation.objects.get(pk=created["id"]).versions.count(), 1)
