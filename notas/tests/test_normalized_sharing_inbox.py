from importlib import import_module

from django.apps import apps as django_apps
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.application.sharing.dailyplans import create_dailyplan_share_resource
from notas.application.sharing.services import claim_share_resource
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    DailyPlanShare,
    Food,
    InboxItem,
    Meal,
    MealFood,
    ShareClaim,
    ShareResource,
)
from notas.presentation.pages.inbox_pages import build_inbox_items


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False)
class NormalizedSharingInboxTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user("inbox-sender", email="sender@example.com")
        self.recipient = User.objects.create_user("inbox-recipient", email="recipient@example.com")
        self.plan = DailyPlan.objects.create(name="Plan de snapshot", created_by=self.sender, is_draft=False)
        meal = Meal.objects.create(name="Almuerzo", created_by=self.sender, is_draft=False)
        food = Food.objects.create(name="Arroz", protein=3, carbs=28, fat=1, created_by=self.sender)
        MealFood.objects.create(meal=meal, food=food, quantity=150)
        DailyPlanMeal.objects.create(dailyplan=self.plan, meal=meal, hour="13:00")
        self.resource = create_dailyplan_share_resource(sender=self.sender, dailyplan_id=self.plan.id).resource
        _, self.inbox_item = claim_share_resource(
            resource=self.resource,
            user=self.recipient,
            source=ShareClaim.Source.LINK,
        )
        self.client.force_login(self.recipient)

    def test_normalized_claim_is_listed_and_detail_marks_it_read(self):
        listing = self.client.get(reverse("inbox_list"))
        detail = self.client.get(reverse("inbox_detail", args=["share", self.inbox_item.id]))

        self.assertContains(listing, "Plan de snapshot")
        self.assertEqual(detail.status_code, 200)
        self.inbox_item.refresh_from_db()
        self.assertIsNotNone(self.inbox_item.read_at)

    def test_claimed_snapshot_remains_available_after_public_link_revocation(self):
        self.resource.status = ShareResource.Status.REVOKED
        self.resource.save(update_fields=["status"])

        public_response = self.client.get(reverse("share_preview", args=[self.resource.public_id]))
        inbox_response = self.client.get(reverse("inbox_attachment_detail", args=["share", self.inbox_item.id]))

        self.assertEqual(public_response.status_code, 404)
        self.assertEqual(inbox_response.status_code, 200)
        self.assertContains(inbox_response, "Plan de snapshot")

    def test_favorite_and_dismiss_use_recipient_owned_inbox_state(self):
        favorite_url = reverse("inbox_toggle_favorite", args=["share", self.inbox_item.id])
        delete_url = reverse("inbox_delete", args=["share", self.inbox_item.id])

        self.client.post(favorite_url)
        self.inbox_item.refresh_from_db()
        self.assertTrue(self.inbox_item.is_favorite)

        self.client.post(delete_url)
        self.inbox_item.refresh_from_db()
        self.assertIsNotNone(self.inbox_item.dismissed_at)
        self.assertNotContains(self.client.get(reverse("inbox_list")), "Plan de snapshot")

    def test_save_hydrates_one_recipient_owned_copy_from_snapshot(self):
        save_url = reverse("inbox_save_attachment", args=["share", self.inbox_item.id])

        first = self.client.post(save_url)
        second = self.client.post(save_url)

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second["Location"], first["Location"])
        copies = DailyPlan.objects.filter(created_by=self.recipient, name="Plan de snapshot")
        self.assertEqual(copies.count(), 1)
        saved = copies.get()
        saved_food = saved.dailyplan_meals.get().meal.meal_food_set.get()
        self.assertEqual(saved_food.food.name, "Arroz")
        self.assertEqual(saved_food.quantity, 150)
        self.assertAlmostEqual(saved_food.food.carbs, 28)
        self.inbox_item.refresh_from_db()
        self.assertEqual(self.inbox_item.saved_object_id, saved.id)

    def test_migrated_legacy_dailyplan_is_not_duplicated_in_dual_read(self):
        legacy = DailyPlanShare.objects.create(
            sender=self.sender,
            recipient_email=self.recipient.email,
            accepted_by=self.recipient,
            dailyplan=self.plan,
        )
        self.resource.legacy_reference = f"dailyplan:{legacy.id}"
        self.resource.save(update_fields=["legacy_reference"])

        items = build_inbox_items(self.recipient)

        self.assertEqual([item.title for item in items].count("Plan de snapshot"), 1)

    def test_dailyplan_backfill_is_idempotent_and_preserves_legacy_state(self):
        second_plan = DailyPlan.objects.create(name="Plan legacy", created_by=self.sender, is_draft=False)
        legacy = DailyPlanShare.objects.create(
            sender=self.sender,
            recipient_email=self.recipient.email,
            accepted_by=self.recipient,
            dailyplan=second_plan,
            is_read=True,
            is_favorite=True,
        )
        migration = import_module("notas.migrations.0057_sharing_inbox_migration_metadata")

        migration.backfill_accepted_dailyplan_shares(django_apps, None)
        migration.backfill_accepted_dailyplan_shares(django_apps, None)

        migrated = ShareResource.objects.get(legacy_reference=f"dailyplan:{legacy.id}")
        migrated_item = InboxItem.objects.get(resource=migrated)
        self.assertEqual(migrated.snapshot["subject"]["title"], "Plan legacy")
        self.assertIsNotNone(migrated_item.read_at)
        self.assertTrue(migrated_item.is_favorite)
        self.assertEqual(ShareResource.objects.filter(legacy_reference=f"dailyplan:{legacy.id}").count(), 1)
