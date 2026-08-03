from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProfilePlanMigrationTests(TransactionTestCase):
    migrate_from = [("notas", "0044_profile_timezone_name_programcalendarization_and_more")]
    migrate_to = [("notas", "0045_migrate_profile_plan_to_accounts")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        User = old_apps.get_model("auth", "User")
        Profile = old_apps.get_model("notas", "Profile")
        Plan = old_apps.get_model("notas", "Plan")

        self.legacy_plan = Plan.objects.create(
            name="Legacy Nutritionist Exact",
            role="nutritionist",
            can_create_meal=True,
            can_create_dailyplan=True,
            can_create_program=True,
            can_publish=True,
            can_fork=False,
            can_copy=True,
            max_active_subscriptions=9,
        )
        self.user = User.objects.create(username="legacy-migration-user")
        Profile.objects.create(
            user_id=self.user.pk,
            role="nutritionist",
            plan_id=self.legacy_plan.pk,
        )

    def tearDown(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        super().tearDown()

    def test_forward_copies_exact_capabilities_and_removes_profile_field(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        apps = self.executor.loader.project_state(self.migrate_to).apps
        Profile = apps.get_model("notas", "Profile")
        AccountSubscription = apps.get_model("accounts", "AccountSubscription")

        profile_fields = {field.name for field in Profile._meta.get_fields()}
        self.assertNotIn("plan", profile_fields)
        subscription = AccountSubscription.objects.select_related("plan").get(
            user_id=self.user.pk
        )
        workspace = subscription.plan.entitlements["nutrition_workspace"]
        self.assertTrue(workspace["can_publish"])
        self.assertTrue(workspace["can_copy"])
        self.assertFalse(workspace["can_fork"])
        self.assertEqual(workspace["max_active_subscriptions"], 9)
        self.assertEqual(
            subscription.metadata["legacy_profile_plan_id"],
            self.legacy_plan.pk,
        )

    def test_reverse_restores_original_profile_plan_assignment(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        apps = self.executor.loader.project_state(self.migrate_from).apps
        Profile = apps.get_model("notas", "Profile")

        profile = Profile.objects.get(user_id=self.user.pk)
        self.assertEqual(profile.plan_id, self.legacy_plan.pk)
