from django.test import override_settings
from django.utils import timezone

from accounts.models import AccountPlan, AccountSubscription
from mobile_api.selectors import _calendarized_snapshot_with_meal_links
from mobile_api.tests.base import AuthenticatedMobileAPITestCase
from notas.application.services.calendarization.snapshots import build_dailyplan_snapshot_from_dailyplan
from notas.application.services.commands.dailyplan_commands import copy_dailyplan
from notas.domain.models import CalendarizedDay, DailyPlan, PinnedDailyPlan, Supplement, SupplementCatalogEntry, SupplementIntake


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False, SUPPLEMENTS_FEATURE_ENABLED=True)
class SupplementAPITests(AuthenticatedMobileAPITestCase):
    def setUp(self):
        super().setUp()
        AccountSubscription.objects.update_or_create(
            user=self.user, defaults={"plan": AccountPlan.objects.get(slug="pro")},
        )
        self.plan = DailyPlan.objects.create(name="Solo suplementos", created_by=self.user)

    def test_global_catalog_is_published_and_saved_as_independent_copy(self):
        entry = SupplementCatalogEntry.objects.get(slug="vitamina-d3-generica")
        listing = self.client.get("/api/v1/explore/supplements")
        self.assertEqual(listing.status_code, 200, listing.content)
        self.assertIn(entry.id, [item["id"] for item in listing.json()["data"]["items"]])
        endpoint = f"/api/v1/explore/supplements/{entry.id}/save"
        first = self.client.post(endpoint)
        second = self.client.post(endpoint)
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.json()["data"]["already_saved"], True)
        self.assertEqual(Supplement.objects.filter(created_by=self.user, catalog_entry=entry).count(), 1)
        saved = Supplement.objects.get(created_by=self.user, catalog_entry=entry)
        saved.description = "Mi versión"
        saved.save(update_fields=["description"])
        self.assertNotEqual(saved.description, entry.description)
        entry.is_published = False
        entry.save(update_fields=["is_published"])
        self.assertEqual(self.client.get(f"/api/v1/explore/supplements/{entry.id}").status_code, 404)
        self.assertEqual(self.client.post(endpoint).status_code, 404)

    def _create_supplement(self):
        response = self.client.post(
            "/api/v1/library/supplements",
            data={
                "name": "Multivitamínico", "form": "capsule",
                "components": [{"name": "Vitamina D", "quantity": "10", "unit": "mcg"}],
                "default_quantity": "2", "default_unit": "capsule",
                "nutrition": {
                    "energy_kcal": "5", "protein_g": "0", "carbs_g": "1",
                    "fat_g": "0", "saturated_fat_g": "0", "sugar_g": "0",
                    "fiber_g": "0", "sodium_mg": "12",
                },
                "user_information": "Texto aportado por el usuario",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["data"]

    def test_supplement_nutrition_is_saved_for_detail_without_entering_intake_snapshot(self):
        supplement = self._create_supplement()
        self.assertEqual(supplement["nutrition"]["energy_kcal"], "5")
        self.assertEqual(supplement["nutrition"]["sodium_mg"], "12")
        response = self.client.post(
            f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes",
            data={"items": [{"supplement_id": supplement["id"], "quantity": "2", "unit": "capsule"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        intake_supplement = response.json()["data"]["items"][0]["items"][0]["supplement"]
        self.assertNotIn("nutrition", intake_supplement)
        self.plan.refresh_from_db()
        self.assertEqual(self.plan.total_kcal, 0)

    def test_legacy_update_without_nutrition_preserves_existing_label_values(self):
        supplement = self._create_supplement()
        response = self.client.put(
            f"/api/v1/library/supplements/{supplement['id']}",
            data={
                "name": "Multivitamínico actualizado", "form": "capsule",
                "components": supplement["components"],
                "default_quantity": "2", "default_unit": "capsule",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["data"]["nutrition"]["energy_kcal"], "5")

    def test_reusable_intake_preset_can_be_added_to_multiple_plans(self):
        supplement = self._create_supplement()
        created = self.client.post(
            "/api/v1/library/supplement-intake-presets",
            data={
                "name": "Rutina de mañana",
                "items": [{"supplement_id": supplement["id"], "quantity": "2", "unit": "capsule"}],
            },
            content_type="application/json",
        )
        self.assertEqual(created.status_code, 200, created.content)
        preset = created.json()["data"]
        self.assertEqual(preset["name"], "Rutina de mañana")
        self.assertNotIn("hour", preset)
        self.assertEqual(len(self.client.get("/api/v1/library/supplement-intake-presets").json()["data"]["items"]), 1)

        other_plan = DailyPlan.objects.create(name="Otra minuta", created_by=self.user)
        for plan in (self.plan, other_plan):
            response = self.client.post(
                f"/api/v1/library/daily-plans/{plan.id}/supplement-intakes/from-preset",
                data={"preset_id": preset["id"], "hour": "08:30" if plan == self.plan else "19:45"},
                content_type="application/json",
            )
            self.assertEqual(response.status_code, 200, response.content)
            intake = response.json()["data"]["items"][0]
            self.assertEqual(intake["hour"], "08:30" if plan == self.plan else "19:45")
            self.assertEqual(intake["items"][0]["quantity"], "2.000")

        self.assertEqual(self.plan.supplement_intakes.count(), 1)
        self.assertEqual(other_plan.supplement_intakes.count(), 1)

    def test_preset_keeps_snapshot_when_supplement_is_deleted(self):
        supplement = self._create_supplement()
        preset = self.client.post(
            "/api/v1/library/supplement-intake-presets",
            data={"name": "Noche", "items": [{"supplement_id": supplement["id"], "quantity": "1", "unit": "capsule"}]},
            content_type="application/json",
        ).json()["data"]
        self.client.delete(f"/api/v1/library/supplements/{supplement['id']}")
        response = self.client.post(
            f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes/from-preset",
            data={"preset_id": preset["id"], "hour": "21:00"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        item = response.json()["data"]["items"][0]["items"][0]
        self.assertIsNone(item["supplement_id"])
        self.assertEqual(item["supplement"]["name"], "Multivitamínico")
        self.assertEqual(response.json()["data"]["items"][0]["hour"], "21:00")

    def test_plan_with_only_supplements_is_complete_and_nutrition_is_unchanged(self):
        supplement = self._create_supplement()
        response = self.client.post(
            f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes",
            data={"hour": "08:00", "items": [{"supplement_id": supplement["id"], "quantity": "1", "unit": "capsule"}]},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.plan.refresh_from_db()
        self.assertFalse(self.plan.is_draft)
        self.assertEqual(self.plan.total_kcal, 0)
        self.assertEqual(response.json()["data"]["items"][0]["label"], "Ingesta 1")
        snapshot = build_dailyplan_snapshot_from_dailyplan(self.plan).payload
        self.assertEqual(len(snapshot["supplement_intakes"]), 1)
        self.assertEqual(snapshot["supplement_intakes"][0]["label"], "Ingesta 1")
        self.assertEqual(snapshot["supplement_intakes"][0]["items"][0]["supplement_id"], supplement["id"])
        self.assertEqual(snapshot["totals"]["total_kcal"], 0)
        list_item = self.client.get("/api/v1/library/daily-plans").json()["data"]["items"][0]
        detail_item = self.client.get(f"/api/v1/library/daily-plans/{self.plan.id}").json()["data"]
        expected_indicator = {"icon": "supplement", "label": "sups", "value": 1}
        self.assertIn(expected_indicator, list_item["indicators"])
        self.assertIn(expected_indicator, detail_item["indicators"])

    def test_downgrade_preserves_records_but_blocks_all_supplement_reads(self):
        supplement = self._create_supplement()
        SupplementIntake.objects.create(dailyplan=self.plan, order=1)
        AccountSubscription.objects.filter(user=self.user).update(plan=AccountPlan.objects.get(slug="basic"))
        self.assertEqual(self.client.get("/api/v1/library/supplements").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/library/supplements/{supplement['id']}").status_code, 403)
        self.assertEqual(self.client.get(f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes").status_code, 403)
        self.assertTrue(Supplement.objects.filter(pk=supplement["id"]).exists())
        self.assertTrue(SupplementIntake.objects.filter(dailyplan=self.plan).exists())
        hidden = _calendarized_snapshot_with_meal_links(self.user, {
            "name": "Minuta", "meals": [],
            "supplement_intakes": [{"key": "supplement_intake:1", "items": [{"supplement": {"name": "Privado"}}]}],
        })
        self.assertNotIn("supplement_intakes", hidden)

    @override_settings(SUPPLEMENTS_FEATURE_ENABLED=False)
    def test_rollout_switch_closes_access_without_deleting_data(self):
        Supplement.objects.create(created_by=self.user, name="Guardado")
        self.assertEqual(self.client.get("/api/v1/library/supplements").status_code, 403)
        self.assertFalse(self.client.get("/api/v1/entitlements").json()["data"]["workspace_features"]["can_use_supplements"])
        self.assertTrue(Supplement.objects.filter(created_by=self.user, name="Guardado").exists())

    def test_plan_copy_preserves_private_intake_snapshot(self):
        supplement = self._create_supplement()
        self.client.post(
            f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes",
            data={"items": [{"supplement_id": supplement["id"], "quantity": "2", "unit": "capsule"}]},
            content_type="application/json",
        )
        copied = copy_dailyplan(self.plan, self.user)
        self.assertEqual(copied.supplement_intakes.count(), 1)
        self.assertEqual(copied.supplement_intakes.first().items.first().supplement_snapshot["name"], "Multivitamínico")

    def test_editing_intake_preserves_snapshot_after_library_item_is_deleted(self):
        supplement = self._create_supplement()
        endpoint = f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes"
        created = self.client.post(endpoint, data={"items": [{"supplement_id": supplement["id"], "quantity": "1", "unit": "capsule"}]}, content_type="application/json").json()["data"]["items"][0]
        self.assertEqual(self.client.delete(f"/api/v1/library/supplements/{supplement['id']}").status_code, 200)
        original_item = created["items"][0]
        updated = self.client.put(
            f"{endpoint}/{created['id']}",
            data={"hour": "09:00", "items": [{"item_id": original_item["id"], "supplement_id": None, "quantity": "2", "unit": "capsule"}]},
            content_type="application/json",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        item = updated.json()["data"]["items"][0]["items"][0]
        self.assertIsNone(item["supplement_id"])
        self.assertEqual(item["supplement"]["name"], "Multivitamínico")

    def test_intake_labels_follow_order_after_reordering_and_deletion(self):
        supplement = self._create_supplement()
        endpoint = f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes"
        payload = {"items": [{"supplement_id": supplement["id"], "quantity": "1", "unit": "capsule"}]}
        first = self.client.post(endpoint, data=payload, content_type="application/json").json()["data"]["items"][0]["id"]
        second = self.client.post(endpoint, data=payload, content_type="application/json").json()["data"]["items"][1]["id"]
        ordered = self.client.put(f"{endpoint}/order", data={"ordered_ids": [second, first]}, content_type="application/json")
        self.assertEqual([row["id"] for row in ordered.json()["data"]["items"]], [second, first])
        self.assertEqual([row["label"] for row in ordered.json()["data"]["items"]], ["Ingesta 1", "Ingesta 2"])
        self.assertEqual(self.client.delete(f"{endpoint}/{second}").status_code, 200)
        remaining = self.client.get(endpoint).json()["data"]["items"]
        self.assertEqual([(row["id"], row["label"]) for row in remaining], [(first, "Ingesta 1")])

    def test_intake_completion_is_whole_group_and_separate_for_pinned_and_calendar_day(self):
        supplement = self._create_supplement()
        created = self.client.post(
            f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes",
            data={"items": [{"supplement_id": supplement["id"], "quantity": "1", "unit": "capsule"}]},
            content_type="application/json",
        ).json()["data"]["items"][0]
        PinnedDailyPlan.objects.create(user=self.user, dailyplan=self.plan)
        pinned_path = f"/api/v1/today/pinned-plan/supplement-intakes/{created['id']}/check-ins"
        pinned = self.client.post(pinned_path, data={"action": "completed", "idempotency_key": "pin-one"}, content_type="application/json")
        self.assertEqual(pinned.status_code, 200, pinned.content)
        self.assertEqual(pinned.json()["data"]["items"][0]["status"], "completed")
        self.assertEqual(len(pinned.json()["data"]["items"][0]["items"]), 1)
        self.assertEqual(self.client.post(pinned_path, data={"action": "completed", "idempotency_key": "pin-one"}, content_type="application/json").status_code, 409)

        snapshot = build_dailyplan_snapshot_from_dailyplan(self.plan).payload
        day = CalendarizedDay.objects.create(user=self.user, calendar_date=timezone.localdate(), plan_snapshot=snapshot)
        calendar_path = f"/api/v1/days/{day.id}/supplement-intakes/{created['id']}/check-ins"
        self.assertEqual(self.client.get(f"/api/v1/days/{day.id}/supplement-intakes").json()["data"]["items"][0]["status"], "planned")
        calendar = self.client.post(calendar_path, data={"action": "completed", "idempotency_key": "cal-one"}, content_type="application/json")
        self.assertEqual(calendar.status_code, 200, calendar.content)
        self.assertEqual(calendar.json()["data"]["items"][0]["status"], "completed")

    def test_calendarized_intakes_support_time_reordering_and_deletion_without_changing_library(self):
        supplement = self._create_supplement()
        endpoint = f"/api/v1/library/daily-plans/{self.plan.id}/supplement-intakes"
        payload = {"items": [{"supplement_id": supplement["id"], "quantity": "1", "unit": "capsule"}]}
        first = self.client.post(endpoint, data={**payload, "hour": "08:00"}, content_type="application/json").json()["data"]["items"][0]
        second = self.client.post(endpoint, data={**payload, "hour": "20:00"}, content_type="application/json").json()["data"]["items"][1]
        day = CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=timezone.localdate(),
            plan_snapshot=build_dailyplan_snapshot_from_dailyplan(self.plan).payload,
        )
        calendar_endpoint = f"/api/v1/days/{day.id}/supplement-intakes"

        changed = self.client.patch(f"{calendar_endpoint}/{first['id']}/hour", data={"hour": "09:30"}, content_type="application/json")
        self.assertEqual(changed.status_code, 200, changed.content)
        self.assertEqual(changed.json()["data"]["items"][0]["hour"], "09:30")

        ordered = self.client.put(f"{calendar_endpoint}/order", data={"ordered_keys": [second["key"], first["key"]]}, content_type="application/json")
        self.assertEqual(ordered.status_code, 200, ordered.content)
        self.assertEqual([row["id"] for row in ordered.json()["data"]["items"]], [second["id"], first["id"]])
        self.assertEqual([row["label"] for row in ordered.json()["data"]["items"]], ["Ingesta 1", "Ingesta 2"])

        removed = self.client.delete(f"{calendar_endpoint}/{second['id']}")
        self.assertEqual(removed.status_code, 200, removed.content)
        self.assertEqual([row["id"] for row in removed.json()["data"]["items"]], [first["id"]])
        self.assertEqual(self.client.get(endpoint).json()["data"]["items"][1]["id"], second["id"])

    def test_preset_can_be_added_to_calendarized_day_without_changing_library_plan(self):
        supplement = self._create_supplement()
        preset = self.client.post(
            "/api/v1/library/supplement-intake-presets",
            data={"name": "Rutina de tarde", "items": [{"supplement_id": supplement["id"], "quantity": "2", "unit": "capsule"}]},
            content_type="application/json",
        ).json()["data"]
        day = CalendarizedDay.objects.create(
            user=self.user,
            calendar_date=timezone.localdate(),
            plan_snapshot=build_dailyplan_snapshot_from_dailyplan(self.plan).payload,
        )

        response = self.client.post(
            f"/api/v1/days/{day.id}/supplement-intakes/from-preset",
            data={"preset_id": preset["id"], "hour": "16:30"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200, response.content)
        intake = response.json()["data"]["items"][0]
        self.assertEqual(intake["label"], "Ingesta 1")
        self.assertEqual(intake["hour"], "16:30")
        self.assertEqual(intake["status"], "planned")
        self.assertEqual(intake["items"][0]["supplement"]["name"], "Multivitamínico")
        self.assertEqual(self.plan.supplement_intakes.count(), 0)

        completed = self.client.post(
            f"/api/v1/days/{day.id}/supplement-intakes/{intake['id']}/check-ins",
            data={"action": "completed", "idempotency_key": "new-calendar-intake"},
            content_type="application/json",
        )
        self.assertEqual(completed.status_code, 200, completed.content)
        self.assertEqual(completed.json()["data"]["items"][0]["status"], "completed")
