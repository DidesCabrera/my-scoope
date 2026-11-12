from django.contrib.auth.models import User
from django.test import override_settings

from accounts.models import AccountPlan, AccountSubscription
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.calendarization.snapshots import build_meal_snapshot
from notas.application.services.commands.personal_preparation_commands import (
    create_personal_preparation_draft,
    save_personal_preparation,
)
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

    def test_name_only_draft_is_unselectable_and_becomes_usable_after_ingredients(self):
        response = self.client.post(
            "/api/v1/library/preparations/drafts", data={"name": "  Salsa casera  "}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200, response.content)
        draft = response.json()["data"]
        self.assertEqual(draft["name"], "Salsa casera")
        self.assertTrue(draft["is_draft"])
        self.assertEqual(self.client.get("/api/v1/library/preparations").json()["data"]["items"][0]["id"], draft["id"])
        self.assertEqual(self.client.get("/api/v1/preparations").json()["data"]["total"], 0)
        self.assertTrue(self.client.get(f"/api/v1/preparations/{draft['id']}").json()["data"]["is_draft"])
        meal = Meal.objects.create(name="Almuerzo", created_by=self.user)
        unusable = self.client.post(
            f"/api/v1/library/meals/{meal.id}/preparations",
            data={"preparation_id": draft["id"], "units": 1}, content_type="application/json",
        )
        self.assertEqual(unusable.status_code, 404)
        self.assertEqual(
            self.client.get(f"/api/v1/preparations/{draft['id']}").json()["data"]["name"], "Salsa casera"
        )
        renamed = self.client.patch(
            f"/api/v1/library/preparations/{draft['id']}/draft",
            data={"name": "Salsa renovada"}, content_type="application/json",
        )
        self.assertEqual(renamed.status_code, 200, renamed.content)
        self.assertEqual(renamed.json()["data"]["name"], "Salsa renovada")
        saved = self.client.put(
            f"/api/v1/library/preparations/{draft['id']}",
            data={"name": "Salsa casera", "ingredients": [{"food_id": self.food.id, "quantity_g": 80}]},
            content_type="application/json",
        )
        self.assertEqual(saved.status_code, 200, saved.content)
        detail = saved.json()["data"]
        self.assertFalse(detail["is_draft"])
        self.assertEqual(detail["version"], 1)
        self.assertEqual(detail["yield_g"], 80)
        self.assertEqual(detail["default_portion_g"], 100)
        self.assertEqual(detail["household_label"], "porción")
        self.assertEqual(detail["nutrition"]["protein_g"], 10)
        self.assertFalse(detail["yield_is_manual"])
        self.assertEqual(self.client.get("/api/v1/preparations").json()["data"]["total"], 1)

    def test_food_picker_completes_draft_and_adds_to_existing_recipe(self):
        draft = self.client.post(
            "/api/v1/library/preparations/drafts", data={"name": "Avena casera"}, content_type="application/json"
        ).json()["data"]
        picker = f"/api/v1/library/preparations/{draft['id']}/food-picker"
        first = {"food_id": self.food.id, "quantity_g": 80}
        preview = self.client.post(f"{picker}/preview", data=first, content_type="application/json")
        self.assertEqual(preview.status_code, 200, preview.content)
        self.assertEqual(preview.json()["data"]["selection"]["id"], self.food.id)
        projected = preview.json()["data"]["result"]
        self.assertEqual(projected["entity"], "preparation")
        self.assertEqual(projected["name"], "Avena casera")
        self.assertEqual(projected["yield_g"], 80)
        self.assertEqual(projected["default_portion_g"], 100)
        self.assertEqual(projected["nutrition"]["protein"]["grams"], 8)
        self.assertEqual(projected["panel"]["foods"][0]["quantity"], 80)
        self.assertEqual(projected["panel"]["foods"][0]["projected_label"], "Por agregar")
        self.assertTrue(self.client.get(f"/api/v1/preparations/{draft['id']}").json()["data"]["is_draft"])
        committed = self.client.post(f"{picker}/commit", data=first, content_type="application/json")
        self.assertEqual(committed.status_code, 200, committed.content)
        detail = self.client.get(f"/api/v1/preparations/{draft['id']}").json()["data"]
        self.assertFalse(detail["is_draft"])
        self.assertEqual(detail["yield_g"], 80)
        self.assertEqual(detail["default_portion_g"], 100)

        other_food = Food.objects.create(name="Leche", protein=3, carbs=5, fat=3, is_global=True)
        second = {"food_id": other_food.id, "quantity_g": 120}
        second_preview = self.client.post(f"{picker}/preview", data=second, content_type="application/json").json()["data"]["result"]
        self.assertEqual(second_preview["yield_g"], 200)
        self.assertEqual([row["quantity"] for row in second_preview["panel"]["foods"]], [80, 120])
        self.assertEqual(self.client.post(f"{picker}/commit", data=second, content_type="application/json").status_code, 200)
        detail = self.client.get(f"/api/v1/preparations/{draft['id']}").json()["data"]
        self.assertEqual(detail["version"], 2)
        self.assertEqual(detail["yield_g"], 200)
        self.assertEqual(len(detail["recipe_ingredients"]), 2)
        duplicate = self.client.post(f"{picker}/commit", data=second, content_type="application/json")
        self.assertEqual(duplicate.status_code, 422)
        replacement_food = Food.objects.create(name="Tomate", protein=1, carbs=4, fat=0, is_global=True)
        replacement = {"food_id": replacement_food.id, "quantity_g": 95, "replace_food_id": other_food.id}
        replacement_preview = self.client.post(f"{picker}/preview", data=replacement, content_type="application/json")
        self.assertEqual(replacement_preview.status_code, 200)
        self.assertEqual(replacement_preview.json()["data"]["result"]["panel"]["foods"][1]["projected_label"], "Reemplazo")
        self.assertEqual(replacement_preview.json()["data"]["result"]["yield_g"], 175)
        self.assertEqual(self.client.post(f"{picker}/commit", data=replacement, content_type="application/json").status_code, 200)
        detail = self.client.get(f"/api/v1/preparations/{draft['id']}").json()["data"]
        self.assertEqual([(row["food_id"], row["quantity_g"]) for row in detail["recipe_ingredients"]], [(self.food.id, 80), (replacement_food.id, 95)])

    def test_food_picker_cannot_access_another_users_draft(self):
        other = User.objects.create_user(username="other-picker-owner")
        AccountSubscription.objects.update_or_create(
            user=other, defaults={"plan": AccountPlan.objects.get(slug="pro")}
        )
        draft = create_personal_preparation_draft(user=other, name="Privada")
        path = f"/api/v1/library/preparations/{draft.id}/food-picker"
        body = {"food_id": self.food.id, "quantity_g": 50}
        self.assertEqual(self.client.post(f"{path}/preview", data=body, content_type="application/json").status_code, 404)
        self.assertEqual(self.client.post(f"{path}/commit", data=body, content_type="application/json").status_code, 404)

    def test_removing_last_food_returns_preparation_to_draft(self):
        preparation = self.create_preparation()
        response = self.client.delete(f"/api/v1/library/preparations/{preparation['id']}/foods")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["data"]["is_draft"])
        self.assertTrue(self.client.get(f"/api/v1/preparations/{preparation['id']}").json()["data"]["is_draft"])

    def test_yield_tracks_ingredients_until_manually_corrected(self):
        created = self.client.post(
            "/api/v1/library/preparations",
            data={"name": "Avena", "ingredients": [{"food_id": self.food.id, "quantity_g": 100}]},
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200, created.content)
        preparation_id = created.json()["data"]["id"]
        revised = self.client.put(
            f"/api/v1/library/preparations/{preparation_id}",
            data={"name": "Avena", "ingredients": [{"food_id": self.food.id, "quantity_g": 150}]},
            content_type="application/json",
        )
        self.assertEqual(revised.json()["data"]["yield_g"], 150)
        corrected = self.client.put(
            f"/api/v1/library/preparations/{preparation_id}",
            data={"name": "Avena", "yield_g": 120, "default_portion_g": 75,
                  "ingredients": [{"food_id": self.food.id, "quantity_g": 150}]},
            content_type="application/json",
        )
        self.assertEqual(corrected.status_code, 200, corrected.content)
        self.assertEqual(corrected.json()["data"]["yield_g"], 120)
        self.assertEqual(corrected.json()["data"]["default_portion_g"], 75)
        self.assertTrue(corrected.json()["data"]["yield_is_manual"])

    def test_full_recipe_detail_keeps_recipe_quantities_and_nutrition(self):
        second_food = Food.objects.create(name="Acelga", protein=2, carbs=3, fat=0, is_global=True)
        created = self.client.post(
            "/api/v1/library/preparations",
            data={
                "name": "Humita con acelga",
                "ingredients": [
                    {"food_id": self.food.id, "quantity_g": 100},
                    {"food_id": second_food.id, "quantity_g": 170},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200, created.content)
        preparation_id = created.json()["data"]["id"]
        portion = self.client.get(f"/api/v1/preparations/{preparation_id}").json()["data"]
        recipe = self.client.get(f"/api/v1/preparations/{preparation_id}?full_recipe=true").json()["data"]
        self.assertEqual(recipe["yield_g"], 270)
        self.assertEqual(recipe["default_portion_g"], 100)
        self.assertEqual(recipe["grams"], 270)
        self.assertEqual([row["quantity_g"] for row in recipe["ingredients"]], [100, 170])
        self.assertEqual([row["quantity_g"] for row in recipe["recipe_ingredients"]], [100, 170])
        self.assertAlmostEqual(sum(row["quantity_g"] for row in portion["ingredients"]), 100)
        self.assertAlmostEqual(recipe["nutrition"]["protein_g"], 13.4)
        self.assertAlmostEqual(portion["nutrition"]["protein_g"], 13.4 * 100 / 270, places=3)
        self.assertEqual(recipe["nutrition"]["protein_per_kilogram"], 0.2)
        self.assertEqual(portion["nutrition"]["protein_per_kilogram"], 0.1)
        library_item = self.client.get("/api/v1/library/preparations").json()["data"]["items"][0]
        self.assertEqual(library_item["nutrition"], portion["nutrition"])

        revised = self.client.put(
            f"/api/v1/library/preparations/{preparation_id}",
            data={
                "name": "Humita con acelga", "yield_g": 300, "default_portion_g": 75,
                "ingredients": [
                    {"food_id": self.food.id, "quantity_g": 100},
                    {"food_id": second_food.id, "quantity_g": 170},
                ],
            },
            content_type="application/json",
        )
        self.assertEqual(revised.status_code, 200, revised.content)
        recipe = self.client.get(f"/api/v1/preparations/{preparation_id}?full_recipe=true").json()["data"]
        self.assertEqual(recipe["grams"], 300)
        self.assertEqual([row["quantity_g"] for row in recipe["ingredients"]], [100, 170])
        self.assertAlmostEqual(recipe["nutrition"]["protein_g"], 13.4)

    def test_another_users_draft_is_not_visible_or_editable(self):
        other = User.objects.create_user(username="other-draft-owner")
        AccountSubscription.objects.update_or_create(
            user=other, defaults={"plan": AccountPlan.objects.get(slug="pro")}
        )
        draft = create_personal_preparation_draft(user=other, name="Receta privada")
        self.assertEqual(self.client.get(f"/api/v1/preparations/{draft.id}").status_code, 404)
        self.assertEqual(self.client.get("/api/v1/library/preparations").json()["data"]["total"], 0)
        self.assertEqual(self.client.delete(f"/api/v1/library/preparations/{draft.id}").status_code, 404)
        update = self.client.put(
            f"/api/v1/library/preparations/{draft.id}",
            data={"name": "Ajena", "ingredients": [{"food_id": self.food.id, "quantity_g": 100}]},
            content_type="application/json",
        )
        self.assertEqual(update.status_code, 404)

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
        draft_blocked = self.client.post(
            "/api/v1/library/preparations/drafts", data={"name": "Sin Pro"}, content_type="application/json"
        )
        self.assertEqual(draft_blocked.status_code, 403)
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
