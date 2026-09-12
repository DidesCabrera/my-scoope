from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from notas.application.sharing.entities import (
    EntityShareError,
    build_dailyplanmeal_share_snapshot,
    build_food_share_snapshot,
    build_meal_share_snapshot,
    build_program_share_snapshot,
    get_or_create_entity_share_resource,
)
from notas.application.sharing.inbox import save_inbox_item
from notas.application.sharing.services import claim_share_resource
from notas.domain.models import (
    DailyPlan,
    DailyPlanMeal,
    DailyPlanMealShare,
    DailyPlanShare,
    Food,
    FoodShare,
    Meal,
    MealFood,
    MealShare,
    Program,
    ProgramDay,
    ProgramShare,
    ShareClaim,
    ShareInvitation,
    ShareResource,
)


class EntitySharingTests(TestCase):
    def setUp(self):
        self.sender = User.objects.create_user("entity-sender", email="sender@example.com")
        self.recipient = User.objects.create_user("entity-recipient", email="recipient@example.com")
        self.food = Food.objects.create(
            name="Yogur", protein=8, carbs=12, fat=4, created_by=self.sender
        )
        self.meal = Meal.objects.create(name="Desayuno", created_by=self.sender, is_draft=False)
        MealFood.objects.create(meal=self.meal, food=self.food, quantity=150)
        self.plan = DailyPlan.objects.create(
            name="Plan lunes", created_by=self.sender, is_draft=False
        )
        self.dpm = DailyPlanMeal.objects.create(
            dailyplan=self.plan, meal=self.meal, hour="08:30"
        )
        self.program = Program.objects.create(
            name="Semana base", created_by=self.sender, duration_weeks=2, is_draft=False
        )
        ProgramDay.objects.create(
            program=self.program, dailyplan=self.plan, week_number=1, day_number=2
        )

    def test_adapters_are_portable_and_keep_entity_shape(self):
        food = build_food_share_snapshot(self.food)
        meal = build_meal_share_snapshot(self.meal)
        dpm = build_dailyplanmeal_share_snapshot(self.dpm)
        program = build_program_share_snapshot(self.program)

        self.assertEqual(food["subject"]["type"], "food")
        self.assertEqual(food["summary"], {"basis_grams": 100})
        self.assertEqual(meal["summary"]["food_count"], 1)
        self.assertEqual(meal["foods"][0]["quantity_grams"], 150)
        self.assertEqual(dpm["subject"]["variant"], "daily_plan_meal")
        self.assertEqual(dpm["time"], "08:30")
        self.assertEqual(program["summary"]["duration_weeks"], 2)
        self.assertEqual(program["days"][0]["plan"]["subject"]["title"], "Plan lunes")
        serialized = str((food, meal, dpm, program))
        self.assertNotIn("entity-sender", serialized)
        self.assertNotIn("sender@example.com", serialized)

    def test_resource_factory_is_owner_only_and_reuses_current_snapshot(self):
        first = get_or_create_entity_share_resource(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.MEAL,
            subject_id=self.meal.id,
        ).resource
        same = get_or_create_entity_share_resource(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.MEAL,
            subject_id=self.meal.id,
        ).resource
        self.assertEqual(first.pk, same.pk)
        dpm_resource = get_or_create_entity_share_resource(
            sender=self.sender,
            subject_type=ShareResource.SubjectType.MEAL,
            subject_id=self.dpm.id,
            variant="daily_plan_meal",
        ).resource
        self.assertNotEqual(first.pk, dpm_resource.pk)
        self.assertEqual(dpm_resource.snapshot["subject"]["variant"], "daily_plan_meal")

        outsider = User.objects.create_user("entity-outsider")
        with self.assertRaisesMessage(EntityShareError, "share_subject_not_available"):
            get_or_create_entity_share_resource(
                sender=outsider,
                subject_type=ShareResource.SubjectType.MEAL,
                subject_id=self.meal.id,
            )

    def _claim_and_save(self, resource):
        _, item = claim_share_resource(
            resource=resource,
            user=self.recipient,
            source=ShareClaim.Source.LINK,
        )
        return item, save_inbox_item(inbox_item=item, actor=self.recipient)

    def test_food_and_meal_snapshots_save_idempotent_detached_copies(self):
        food_resource = get_or_create_entity_share_resource(
            sender=self.sender, subject_type="food", subject_id=self.food.id
        ).resource
        food_item, saved_food = self._claim_and_save(food_resource)
        again = save_inbox_item(inbox_item=food_item, actor=self.recipient)

        self.assertEqual(saved_food.entity, "food")
        self.assertEqual(saved_food.instance.created_by, self.recipient)
        self.assertEqual(saved_food.instance.protein, 8)
        self.assertEqual(again.instance.pk, saved_food.instance.pk)

        meal_resource = get_or_create_entity_share_resource(
            sender=self.sender, subject_type="meal", subject_id=self.meal.id
        ).resource
        _, saved_meal = self._claim_and_save(meal_resource)
        saved_meal_food = saved_meal.instance.meal_food_set.get()
        self.assertEqual(saved_meal.entity, "meal")
        self.assertEqual(saved_meal_food.quantity, 150)
        self.assertAlmostEqual(saved_meal_food.food.protein, 8)

    def test_program_snapshot_saves_nested_user_owned_copy(self):
        resource = get_or_create_entity_share_resource(
            sender=self.sender, subject_type="program", subject_id=self.program.id
        ).resource
        _, saved = self._claim_and_save(resource)

        slot = saved.instance.program_dailyplan.select_related("dailyplan").get()
        self.assertEqual(saved.entity, "program")
        self.assertEqual(saved.instance.created_by, self.recipient)
        self.assertEqual(saved.instance.duration_weeks, 2)
        self.assertEqual((slot.week_number, slot.day_number), (1, 2))
        self.assertEqual(slot.dailyplan.source, DailyPlan.SOURCE_PROGRAM)
        self.assertEqual(slot.dailyplan.created_by, self.recipient)

    def test_dailyplan_meal_variant_saves_as_detached_meal(self):
        resource = get_or_create_entity_share_resource(
            sender=self.sender,
            subject_type="meal",
            subject_id=self.dpm.id,
            variant="daily_plan_meal",
        ).resource
        _, saved = self._claim_and_save(resource)

        self.assertEqual(saved.entity, "meal")
        self.assertEqual(saved.instance.name, self.meal.name)
        self.assertEqual(saved.instance.created_by, self.recipient)
        self.assertEqual(saved.instance.meal_food_set.get().quantity, 150)

    def test_legacy_backfill_covers_every_entity_and_preserves_tokens(self):
        legacy_rows = [
            (DailyPlanShare.objects.create(
                sender=self.sender, recipient_email=self.recipient.email,
                accepted_by=self.recipient, dailyplan=self.plan, is_favorite=True,
            ), "dailyplan"),
            (FoodShare.objects.create(
                sender=self.sender, recipient_email="food@example.com", food=self.food,
            ), "food"),
            (MealShare.objects.create(
                sender=self.sender, recipient_email=self.recipient.email,
                accepted_by=self.recipient, meal=self.meal,
            ), "meal"),
            (DailyPlanMealShare.objects.create(
                sender=self.sender, recipient_email="dpm@example.com", dailyplan_meal=self.dpm,
            ), "dpm"),
            (ProgramShare.objects.create(
                sender=self.sender, recipient_email=self.recipient.email,
                accepted_by=self.recipient, program=self.program,
            ), "program"),
        ]
        migration = import_module("notas.migrations.0060_backfill_all_legacy_shares")

        migration.backfill_all_legacy_shares(django_apps, None)
        migration.backfill_all_legacy_shares(django_apps, None)

        for legacy, prefix in legacy_rows:
            resource = ShareResource.objects.get(legacy_reference=f"{prefix}:{legacy.id}")
            invitation = ShareInvitation.objects.get(resource=resource)
            self.assertEqual(invitation.public_id, legacy.token)
            self.assertEqual(resource.claim_policy, ShareResource.ClaimPolicy.SINGLE)
            self.assertIsNone(resource.expires_at)
        migrated_program = ShareResource.objects.get(
            legacy_reference=f"program:{legacy_rows[-1][0].id}"
        )
        self.assertEqual(migrated_program.snapshot["days"][0]["plan"]["subject"]["title"], "Plan lunes")


@override_settings(NUTRITION_ONBOARDING_GATE_ENABLED=False, EMAIL_SHARE_DELIVERY_ENABLED=False)
class EntitySharingWebChannelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user("web-entity-owner", email="owner@example.com")
        self.food = Food.objects.create(name="Leche", protein=3, carbs=5, fat=2, created_by=self.owner)
        self.meal = Meal.objects.create(name="Once", created_by=self.owner, is_draft=False)
        MealFood.objects.create(meal=self.meal, food=self.food, quantity=200)
        self.plan = DailyPlan.objects.create(name="Plan web", created_by=self.owner, is_draft=False)
        self.dpm = DailyPlanMeal.objects.create(dailyplan=self.plan, meal=self.meal)
        self.program = Program.objects.create(name="Programa web", created_by=self.owner, is_draft=False)
        self.client.force_login(self.owner)

    def test_all_web_email_forms_write_only_normalized_sharing(self):
        payload = {
            "recipient_email": "friend@example.com",
            "subject": "Para ti",
            "message": "Revísalo.",
        }
        responses = (
            self.client.post(reverse("food_share", args=[self.food.id]), payload),
            self.client.post(reverse("meal_share", args=[self.meal.id]), payload),
            self.client.post(
                reverse("dailyplanmeal_share", args=[self.plan.id, self.dpm.id]), payload
            ),
            self.client.post(reverse("program_share", args=[self.program.id]), payload),
        )

        self.assertTrue(all(response.status_code == 302 for response in responses))
        self.assertEqual(ShareResource.objects.count(), 4)
        self.assertEqual(ShareInvitation.objects.count(), 4)
        self.assertFalse(DailyPlanShare.objects.exists())
        self.assertFalse(FoodShare.objects.exists())
        self.assertFalse(MealShare.objects.exists())
        self.assertFalse(DailyPlanMealShare.objects.exists())
        self.assertFalse(ProgramShare.objects.exists())
        for resource in ShareResource.objects.all():
            preview = self.client.get(reverse("share_preview", args=[resource.public_id]))
            self.assertEqual(preview.status_code, 200)
            self.assertContains(preview, resource.snapshot["subject"]["title"])
from importlib import import_module

from django.apps import apps as django_apps
